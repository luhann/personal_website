#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fonttools[woff]"]
# ///
"""Downloads EB Garamond/IBM Plex woff2 per script subset from Google's CSS2
endpoint, names each by its SHA256 hash for content-addressed caching.

Mirrors ~/dev/homelab/hln-site/refresh-fonts.py. Each subset keeps Google's
unicode-range, so a browser fetches only the files whose characters appear on
the page: Latin readers pay for Latin, and Cyrillic, Greek and Vietnamese text
still renders in the site's faces.

Google's subsets are not a partition of the font: they drop arrows (the
footnote back-link ↩), box drawing (file trees in code blocks), fractions and
super/subscripts. So each face also gets "symbols" and "extra" files, cut from
the full upstream font in google/fonts, holding what no Google range declares,
under their own unicode-range; the cost is paid only by a page that uses those
characters. Coverage equals the full font except codepoints a Google range
declares but its file lacks (typographic spaces, joiners): those fall back as
they would on Google Fonts, because claiming them would overlap the range.

Writes static/fonts/*.woff2, static/fonts/OFL-*.txt, static/fonts.css and
templates/font-preload.html (preloads for the Latin files the first paint
needs). Not part of `just build`: run it deliberately with `just fonts`.
"""

import hashlib
import io
import re
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# Garamond and Plex Sans are variable on Google, so a weight range is one file
# per subset. Plex Mono is static: 700 and italic are what the sass asks for.
# Every face used in italic has a real italic: the body sets
# font-synthesis-style: none so CJK (which has no italic) is never slanted, and
# that also stops the browser faking one for a Latin face that lacks it.
CSS2 = (
    "https://fonts.googleapis.com/css2"
    "?family=EB+Garamond:ital,wght@0,400..700;1,400..700"
    "&family=IBM+Plex+Mono:ital,wght@0,400;0,700;1,400"
    "&family=IBM+Plex+Sans:ital,wght@0,400..600;1,400..600"
    "&display=swap"
)
# The full font behind each face, for the symbols remainder. Keyed like the
# CSS: (family, style, font-weight).
UPSTREAM = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FULL = {
    ("EB Garamond", "normal", "400 700"): "ebgaramond/EBGaramond[wght].ttf",
    ("EB Garamond", "italic", "400 700"): "ebgaramond/EBGaramond-Italic[wght].ttf",
    ("IBM Plex Sans", "normal", "400 600"): "ibmplexsans/IBMPlexSans[wdth,wght].ttf",
    ("IBM Plex Sans", "italic", "400 600"): "ibmplexsans/IBMPlexSans-Italic[wdth,wght].ttf",
    ("IBM Plex Mono", "normal", "400"): "ibmplexmono/IBMPlexMono-Regular.ttf",
    ("IBM Plex Mono", "normal", "700"): "ibmplexmono/IBMPlexMono-Bold.ttf",
    ("IBM Plex Mono", "italic", "400"): "ibmplexmono/IBMPlexMono-Italic.ttf",
}
# The remainder splits in two so a page using one arrow does not pay for 400
# rare glyphs: "symbols" holds the blocks prose and code actually reach for
# (super/subscripts, number forms, arrows, math, technical, box drawing,
# geometric shapes); "extra" holds the rest (combining marks, enclosed
# alphanumerics, regional indicators, ...).
SYMBOL_BLOCKS = [(0x2070, 0x209F), (0x2150, 0x23FF), (0x2500, 0x25FF)]
# Latin files requested on first paint; everything else loads on demand.
PRELOAD = {("eb-garamond", "normal", "latin"), ("ibm-plex-sans", "normal", "latin")}
# woff2 is served only to a browser UA; a bare urllib request gets ttf.
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)

get = lambda url: urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": UA})
).read()

css = get(CSS2).decode()
blocks = re.findall(r"/\* (\S+) \*/\s*(@font-face \{.*?\})", css, re.S)
field = lambda block, key: re.search(rf"{key}: ([^;]+);", block).group(1)
src = lambda block: re.search(r"url\((\S+?)\)", block).group(1)

names = {}
for script, block in blocks:
    key = (
        field(block, "font-family").strip("'").lower().replace(" ", "-"),
        field(block, "font-style"),
        script,
    )
    assert names.setdefault(src(block), key) == key, f"{src(block)} spans more than one face"

out = Path("static/fonts")
out.mkdir(exist_ok=True)
for stale in [*out.glob("*.woff2"), *out.glob("OFL-*.txt")]:
    stale.unlink()
# The OFL asks that redistributed copies carry the licence, and the repo is
# public: fetch it from the same google/fonts directory each face comes from.
for directory in sorted({path.split("/")[0] for path in FULL.values()}):
    (out / f"OFL-{directory}.txt").write_bytes(get(f"{UPSTREAM}{directory}/OFL.txt"))
hashed = {}
for url, key in names.items():
    data = get(url)
    hashed[url] = f"{'-'.join(key)}.{hashlib.sha256(data).hexdigest()[:8]}.woff2"
    (out / hashed[url]).write_bytes(data)

body = "".join(
    block.replace(src(block), f"fonts/{hashed[src(block)]}") + "\n" for _, block in blocks
)


def ranges(codepoints):
    """Codepoints -> a unicode-range value of contiguous runs."""
    runs = []
    for cp in sorted(codepoints):
        if runs and cp == runs[-1][1] + 1:
            runs[-1][1] = cp
        else:
            runs.append([cp, cp])
    return ", ".join(f"U+{a:04X}" + (f"-{b:04X}" if b != a else "") for a, b in runs)


def declared(value):
    """A unicode-range value -> the set of codepoints it names."""
    cps = set()
    for part in value.split(","):
        lo, _, hi = part.strip().removeprefix("U+").partition("-")
        cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return cps


# Covered means DECLARED by one of Google's blocks, not present in its file.
# Google declares spans its files do not fill (U+2000-206F has no en space, for
# one); a remainder claiming those would overlap, win the match as the later
# rule, and make every page fetch it for a space character.
faces = {}
for _, block in blocks:
    face = (field(block, "font-family").strip("'"), field(block, "font-style"), field(block, "font-weight"))
    faces.setdefault(face, set()).update(declared(field(block, "unicode-range")))
assert set(faces) == set(FULL), f"FULL does not match the CSS faces: {set(faces) ^ set(FULL)}"

for (family, style, weight), covered in faces.items():
    full_bytes = get(UPSTREAM + urllib.parse.quote(FULL[family, style, weight]))
    full = TTFont(io.BytesIO(full_bytes))
    missing = set(full.getBestCmap()) - covered
    if not missing:
        continue
    # Pin to the weights the face declares; any other axis (Plex Sans' wdth) to
    # its default, since the site never sets it.
    lo, _, hi = weight.partition(" ")
    limits = {a.axisTag: a.defaultValue for a in full["fvar"].axes} if "fvar" in full else None
    if limits:
        limits["wght"] = (float(lo), float(hi or lo))
    symbols = {cp for cp in missing if any(a <= cp <= b for a, b in SYMBOL_BLOCKS)}
    for part, cps in (("symbols", symbols), ("extra", missing - symbols)):
        if not cps:
            continue
        font = TTFont(io.BytesIO(full_bytes), lazy=False)
        # `meta` (design/supported-language hints) has no subsetter; browsers
        # ignore it and Google's own subsets ship without it.
        options = subset.Options()
        options.drop_tables += ["meta"]
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=cps)
        subsetter.subset(font)
        if limits:
            font = instancer.instantiateVariableFont(font, limits)
        # Keep head.modified as upstream set it: a save-time stamp would change
        # the bytes, so the content hash and filename, on every run.
        font.recalcTimestamp = False
        font.flavor = "woff2"
        buffer = io.BytesIO()
        font.save(buffer)
        data = buffer.getvalue()
        name = (
            f"{family.lower().replace(' ', '-')}-{style}-{weight.replace(' ', '-')}-{part}"
            f".{hashlib.sha256(data).hexdigest()[:8]}.woff2"
        )
        (out / name).write_bytes(data)
        body += (
            f"@font-face {{\n  font-family: '{family}';\n  font-style: {style};\n"
            f"  font-weight: {weight};\n  font-display: swap;\n"
            f"  src: url(fonts/{name}) format('woff2');\n"
            f"  unicode-range: {ranges(cps)};\n}}\n"
        )
Path("static/fonts.css").write_text(
    f"/* GENERATED by refresh-fonts.py from Google's CSS2 endpoint — do not edit.\n"
    f"   {CSS2} */\n{body}"
)

preloads = sorted(hashed[url] for url, key in names.items() if key in PRELOAD)
assert len(preloads) == len(PRELOAD), f"expected {len(PRELOAD)} preloads, got {preloads}"
Path("templates/font-preload.html").write_text(
    "{# GENERATED by refresh-fonts.py — do not edit. #}\n"
    + "".join(
        f'<link rel="preload" href="/fonts/{name}" as="font" type="font/woff2" crossorigin="anonymous">\n'
        for name in preloads
    )
)
files = list(out.iterdir())
print(f"{len(files)} files, {sum(p.stat().st_size for p in files)} bytes")

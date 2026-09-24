
default:
  @just --list

clean:
  @rm -rvf public/

build:
  zola build

serve:
  zola serve

# Re-download the self-hosted faces from Google's CSS2 endpoint into
# static/fonts/ + static/fonts.css + templates/font-preload.html. Not part of
# build: run it deliberately, then rebuild.
fonts:
  uv run --script refresh-fonts.py

# Verify the patroclus token symlinks still resolve. The site is built here and
# public/ is uploaded to the VPS, so sass/patroclus/ links straight into
# ~/dev/patroclus/scss -- no vendored copy, nothing to drift.
check-theme:
  @test -e sass/patroclus/_patroclus-tokens.scss \
    && test -e sass/patroclus/_patroclus-css-vars.scss \
    && echo "patroclus tokens linked" \
    || (echo "patroclus token symlinks are broken -- is ~/dev/patroclus present?"; exit 1)

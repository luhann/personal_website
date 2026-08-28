+++
title = "On Blogging"
date = 2026-05-29
description = "How I found a website and blog setup that works for me."
[taxonomies]
tags = ["meta", "writing"]
+++

Like many academics before me, I have spent years upholding a storied tradition: attempting to maintain a public-facing
website, failing, and trying again. My initial foray into the world of personal academic websites was
with the [Hugo](https://gohugo.io/) static site generator using the Academic theme. {% <margin> %} I went
looking for the original Academic theme I used, and I can't find it anywhere. There are still some screenshots of the
old theme on Google Images. {% </margin> %}

My problem with Hugo was two-fold. Firstly, I didn't understand **how** to really use Hugo, and I didn't put in any
effort to rectify that shortcoming. Secondly, I did not keep up-to-date with any of the developments of Hugo or the
Academic theme that I was using. This meant that updates to Hugo — or the academic theme — frequently broke
my website. I would apply the updated theme, and then Hugo would fail to build as I hadn't set one of the new configuration
options or additional settings.

Could I have remedied the situation by spending some time learning Hugo and how the themes worked? Absolutely. However,
at the time I wanted something that just worked ™, without having to spend any time or effort. {% <margin class="left"> %} History
has shown that this is not a winning strategy in any endeavour. {% </margin> %} I would routinely have to spend hours getting
my site up-to-date with all of the new changes before I could even think of writing a blog post. Given how infrequently
I actually worked on my website, the ratio of fixing to writing was sub-optimal to say the least.

Eventually, I got sick of that vicious cycle and gave up on writing my own blog posts. Instead, I switched to a purely
static personal website that was made up of just a single `index.html` with a *very* brief biography and some social
media links.

{% <aside> %}
Without the CSS, my entire website could fit into a single [jumbo frame](https://en.wikipedia.org/wiki/Jumbo_frame).
{% </aside> %}

Although the above site did not look particularly aesthetically pleasing, it had the distinct advantage of minimalism.
No updates would cause it to not work, and editing or adding content was extremely easy. There was no framework updating
or tinkering with settings. Perhaps a version of myself born in the 80s would be appreciative of such a website. The
downside was that adding additional **non-homepage** content — like say for example a blog — was extremely challenging,
unless your idea of a good-looking blog was a loose collection of roughly related html files in the same directory.
{% <margin> %} Like three [honey badgers](https://en.wikipedia.org/wiki/Honey_badger) in a trench coat. {% </margin> %}

I have recently been spending most of my free time writing [Rust](https://rust-lang.org/) and connecting it to R, through
the excellent [extendr](https://extendr.rs/) project. Both the extendr website, and the [blog](https://extendr.rs/blog/)
are excellent examples of relatively lightweight but good looking websites. Both are built using the [Zola](https://www.getzola.org/)
static site generator. Zola promises that it is <q>A fast static site generator in a single binary with everything built-in. Forget dependencies.
Everything you need in one binary.</q> After dealing with Hugo dependency hell, no dependencies sounded like music to my ears.
Particularly, Zola felt like a perfect middle ground between the extreme minimalism of hand-writing your own `html` and
using a fully defined Byzantine theme.

A Zola site is just a collection of files and folders, with a specific structure.
<div class="terminal-window">
  <div class="terminal-header">
    <span class="dot red"></span>
    <span class="dot yellow"></span>
    <span class="dot green"></span>
    <span class="terminal-title">~/posts/blog-setup</span>
  </div>
  <div class="terminal-body">
<pre><code>.
├── <span class="file-config">config.toml</span>
├── <span class="folder">content</span>
│   ├── <span class="folder">about</span>
│   │   └── _index.md
│   ├── <span class="folder">posts</span>
│   │   ├── <span class="folder">hello_world</span>
│   │   │   └── index.md
│   │   └── _index.md
│   └── _index.md
├── <span class="folder-highlight">sass</span>
│   └── main.scss
├── <span class="folder">static</span>
│   └─ <span class="folder">font</span>
│      └── custom_font.woff2
└── <span class="folder-highlight">templates</span>
    ├── base.html
    ├── index.html
    └── post.html</code></pre>
  </div>
</div>

{% <aside> %} See [getting started](https://www.getzola.org/documentation/getting-started/overview/)
for a more official introduction to Zola.
{% </aside> %}

What attracted me to this layout is how fiercely it aligns with my preference for ownership and predictability. Zola doesn’t
abstract the machinery of a website away behind magic black boxes or deeply nested theme configurations. It offers a transparent, 
flat structure that says exactly what it does on the tin. If a page renders incorrectly, I don't have to hunt through
upstream GitHub theme repositories to find a breaking change; the issue can only be directly inside my own `templates/` directory.
It forces a certain level of intentionality that my previous Hugo setup lacked.

When you run `zola build`, Zola parses your Markdown files and automatically injects the text into the corresponding HTML
templates. What this means is that you only have to write your core template logic once. From then on, creating a new post
is straightforward, just add a new Markdown file into a folder and `zola build`. {% <margin> %} The source for my website can be found
here [https://github.com/luhann/luhann.github.io](https://github.com/luhann/luhann.github.io) as a more detailed demonstration. {% </margin> %}
What this gives me is a website that requires no external themes or dependencies — so cannot break like my previous Hugo site — 
but the flexibility of editing raw `html` for each page of my site if I so desire.

Of course, I am being entirely hypocritical here. My main problems from Hugo stemmed from using external
themes, yet I tout the advantages of Zola by creating my own theme from scratch. Of course it will never break.
If I had used an external Zola theme I might eventually run into the same problems as using the Hugo Academic theme.
Conversely, if I had created my own Hugo theme from scratch it is unlikely I would have had any of the issues I did.
What then does this mean for blogging and static site generation? Regardless of the tool you pick, spending some
time upfront to learn the ins-and-outs of the tool is likely going to lead to a much less frustrating workflow in the long
run. {% <margin class="left"> %} Or perhaps the true message is that one should do all they can to limit 
[external dependencies](https://recology.info/2018/10/limiting-dependencies/) wherever possible. {% </margin> %}

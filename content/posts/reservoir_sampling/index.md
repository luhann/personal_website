+++
title = "On Reservoir Sampling"
date = 2026-06-14
description = "How sometimes the most optimal algorithm is not indeed optimal."
[taxonomies]
tags = ["rust", "algorithms"]
+++

I personally find that one of the most fun ways to learn a new programming language (particularly a [systems programming
language](https://en.wikipedia.org/wiki/System_programming_language)) is to take a relatively simple program and 
see how much you can optimise it. Just for the hell of it. I like to call this:

{% <margin> %}
Perhaps in a later blog post I'll expand on this further.
{% </margin> %}

> In pursuit of meaningless minimalism.

{% <margin class="quote-note"> %}
We should forget about small efficiencies, say about 97% of the time: **premature optimization is the root of all evil**. Yet we should not pass up our opportunities in that critical 3% - Donald Knuth
{% </margin> %}

Recently, with the goal of learning [Rust](https://rust-lang.org/) I converted all of my old Fish shell scripts to
Rust binaries. This will come as no surprise to anyone but Rust is far more capable than Fish, and so while translating
my shell scripts to Rust I decided to see if I could make them **faster**. One utility that I thought would be ripe for
premature optimisation is my wallpaper picker. The task is simple, select a single random wallpaper from a given directory
containing all of my wallpapers.

My naïve Fish implementation looked something like this (I omit the full script for brevity):

```fish
# Wallpaper directory
set -l WALLPAPER_DIR "$HOME/onedrive/wallpapers/"

# Randomly select a wallpaper from the specified directory
set -l WALL (find "."  $WALLPAPER_DIR \
    --type file -e jpg -e jpeg -e png -e webp \
    | sort -R \
    | head -n 1)
```
As you can see, the Fish implementation loads the full list of files into memory, sorts them randomly and picks the first one.
Between shell invocation overhead, firing up **three separate utilities**, and piping text streams between them, we incur
significant overhead. All of that, just to discard the entire list of files bar one.

{% <margin> %}
To guard against the hypothetical edge case where I have more images than there are atoms in the universe.
{% </margin> %}

For my Rust utility, I wanted to make sure that I never have to read the entire list of files into memory.

Enter [Reservoir Sampling](https://en.wikipedia.org/wiki/Reservoir_sampling). Reservoir sampling is a family of algorithms
for choosing a simple random sample of *k* elements, without replacement, from a population of size *n* — without needing
to know the population size (*n*). {% <margin class="left"> %}I know, I know, em-dashes are signs of AI use. You can take
my em-dashes from my cold, dead hands.{% </margin> %}The naïve implementation is known as Algorithm R, created by Alan Waterman[^1],
and is conceptually relatively straightforward.

First select the first *k* elements of *n*, where *k* is the sample size you would like. Next initialise a new index to
track the remainder of our elements: *i*. Then for each element in the list of remainders (after the first *k* elements
have been selected), we generate a random number between 1 and *i*. If that random number is between 1 and *k* we replace
the element in *k* at that position with our new number, otherwise we discard the number. Iterate over every element of
the remainder, and at the end you will have your random sample of *k* elements. When *k* = 1, it is even simpler as you
can just check if the random number generated is equal to 1 (or 0 in zero-indexed arrays). In Rust it would look something
like this:

```rust, name=algorithm_r_naive.rs
fn algorithm_r<I>(inputs: I) -> Option<PathBuf>
where
    I: Iterator<Item = PathBuf>,
{
    let mut chosen = None;
    for (i, item) in inputs.enumerate() {
        if fastrand::usize(..=i) == 0 {
            chosen = Some(item);
        }
    }
    chosen
}
```
Items at the front of the remainder have a higher chance of initially entering the sample than items towards the end,
but they must survive a brutal gauntlet to make it to the end. While conceptually simple, Algorithm R has two major
drawbacks with respect to the pursuit of meaningless minimalism:
- You must evaluate every element of the remainder, one at a time. 
- You must generate a random number for every element of the remainder.

Generating random numbers (particularly true RNG) is computationally expensive, doing so when you are going to discard
99% of the results is even more so. Thankfully, there exists a more efficient algorithm for reservoir sampling.

Enter Algorithm L. First select the first *k* elements of *n*, where *k* is the sample size you would like, and initialize a
floating-point variable *W* to track the reservoir's threshold property. Instead of generating a random number for
every single remaining element, we use a geometric distribution formula based on *W* to calculate a random number of
elements to skip entirely. After we calculate the skip, we generate a random number between 1 and *k* and replace the
element in *k* at that position with our new random number. Finally we update our reservoir threshold with another random
number. Algorithm L generates 3 random numbers for each evaluated element, but 0 random numbers for each skipped element.
Given that the majority of elements are skipped, this works out to far fewer random number generations than Algorithm R.

A standard implementation of Algorithm L in Rust looks something like this:

{% <aside class="left"> %}
For *k* = 1.
{% </aside> %}

{% <aside> %}
A bit of Rust pedantry here: looking at `inputs.nth(skip)`, it might seem like we are cleanly skipping over unneeded elements.
However, because our iterator is an unknown-length filesystem stream, `nth()` is forced to call `next()` under the hood
until it reaches the target. We are saving ourselves from generating random numbers, but we are still evaluating every
single directory entry in between.

If we were sampling from a data structure that supported *O(1)* random access, Algorithm L would be significantly faster.
But converting the directory stream into an array would require loading all the file paths into memory first, which obviates
the entire raison d'être of reservoir sampling.
{% </aside> %}

```rust, name=algorithm_l.rs
fn algorithm_l<I>(inputs: I) -> Option<PathBuf>
where
    I: Iterator<Item = PathBuf>,
{
    let mut inputs = inputs;
    let mut chosen = None;

    if let Some(item) = inputs.next() {
        chosen = Some(item);
    } else {
        return None;
    }

    let mut w: f64 = fastrand::f64();

    loop {
        let skip = (fastrand::f64().ln() / (1.0 - w).ln()) as usize;

        if let Some(item) = inputs.nth(skip) {
            chosen = Some(item);

            w *= fastrand::f64();
        } else {
            break;
        }
    }

    chosen
}
```

We have achieved peak meaningless minimalism. End of story, or so I thought. However, every good meaningless minimalist knows
that peak minimalism is only achieved once the benchmarks say it has been achieved.

{% <margin> %}
Andrew Gallant, aka [BurntSushi](https://github.com/burntsushi), has perhaps the best [post on benchmarking](https://burntsushi.net/ripgrep/) I have ever
read, and it should be required reading for anyone comparing anything with benchmarks. 
{% </margin> %}

Using the Rust implementations described above, we can benchmark just the random wallpaper selection section of code using
the [criterion crate](https://crates.io/crates/criterion).

<div class="tufte-plot-container">
  <div class="tufte-plot-item">
    {{ <inline_svg path="posts/reservoir_sampling/images/violin.svg" /> }}
  </div>
</div>

{% <aside> %}
The benchmarks shown here were calculated on my Ryzen 5950x in a TTY.

Notably, I used the list of my wallpapers stored in RAM as the test case. I currently have 51 wallpapers in my directory.
{% </aside> %}

<div style="display: flex; gap: 20px; overflow-x: auto; font-size: 0.75rem; font-family: sans-serif;">
<div style="flex: 1; min-width: 300px;">

<div style="text-align: center; font-weight: bold; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 5px; font-size: 0.95rem;">Algorithm L</div>

| Metric | Lower Bound | Estimate | Upper Bound |
| :--- | :---: | :---: | :---: |
| **Slope** | <span style="color: #888;">63.625 ns</span> | 63.685 ns | <span style="color: #888;">63.753 ns</span> |
| **R²** | <span style="color: #888;">0.9538650</span> | 0.9544209 | <span style="color: #888;">0.9537203</span> |
| **Mean** | <span style="color: #888;">63.666 ns</span> | 63.713 ns | <span style="color: #888;">63.762 ns</span> |
| **Std. Dev.** | <span style="color: #888;">465.83 ps</span> | 547.00 ps | <span style="color: #888;">621.83 ps</span> |
| **Median** | <span style="color: #888;">63.512 ns</span> | 63.534 ns | <span style="color: #888;">63.553 ns</span> |
| **MAD** | <span style="color: #888;">187.12 ps</span> | 210.03 ps | <span style="color: #888;">240.41 ps</span> |

</div>
<div style="flex: 1; min-width: 300px;">

<div style="text-align: center; font-weight: bold; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 5px; font-size: 0.95rem;">Algorithm R</div>

| Lower Bound | Estimate | Upper Bound |
| :---: | :---: | :---: |
| <span style="color: #888;">48.057 ns</span> | 48.085 ns | <span style="color: #888;">48.116 ns</span> |
| <span style="color: #888;">0.9829652</span> | 0.9831714 | <span style="color: #888;">0.9829132</span> |
| <span style="color: #888;">48.072 ns</span> | 48.094 ns | <span style="color: #888;">48.117 ns</span> |
| <span style="color: #888;">217.27 ps</span> | 259.18 ps | <span style="color: #888;">300.39 ps</span> |
| <span style="color: #888;">47.980 ns</span> | 47.985 ns | <span style="color: #888;">47.992 ns</span> |
| <span style="color: #888;">41.994 ps</span> | 51.568 ps | <span style="color: #888;">64.680 ps</span> |

</div>
</div>

As we can see, Algorithm R is faster than Algorithm L ... Wait, What? The keen-eyed might already suspect why this is the
case. There are two related issues leading to the surprising performance difference, operation cost and mechanical sympathy.
Namely, Big O says that the time complexity for algorithm R is *O(n)* and for algorithm L it is *O(k(1 + log(n/k)))*.
However, this is only true if all primitive operations take the same length of time or number of CPU cycles — which
does not happen on modern CPUs.

On modern CPUs algorithm R is (roughly) an integer increment, a pseudo-random integer generation, and a simple integer comparison. All
in all on most modern CPUs this will be between 3 to 7 CPU cycles per iteration. Algorithm L is (roughly) a pseudo-random
floating-point generation, two natural logarithms, a floating-point division and then a cast to `usize`. Logarithms are transcendental functions.
They cannot be executed in a single CPU cycle. Instead, they require complex microcode approximations or iterative hardware loops.
All in all algorithm L will take roughly  60 to 120 CPU cycles per iteration — before we even get to things like
pipelining and branch prediction. Of course there are fewer iterations in algorithm L, but not enough to outweigh the raw
speed of simple instructions **for this use-case.** If *k* and *n* were both much, much larger algorithm L would snatch the crown,
as the cost of floating-point operations is dwarfed by the number of elements algorithm L would allow us to skip relative to
algorithm R. We pursued meaningless minimalism, and discovered that the real meaningless minimalism was the friends we made along
the way, and that mechanical sympathy beats theoretical complexity every single time.

To tie a bow in the wallpaper selector saga, there are a couple of things we can do outside of the reservoir sampling
algorithm to make the final utility faster. Use the [fastrand](https://docs.rs/fastrand/latest/fastrand/)
crate to generate random numbers, they are not true random numbers but are very fast to generate. Avoid allocations
by making use of Rust's iterators which are lazily evaluated. Filter unsupported image types to reduce the number of
elements evaluated for reservoir sampling. Use only `DirEntry` not `PathBuf`, so no allocations are needed. Putting
that all together, the final version of my random wallpaper utility looks something like this:

{% <aside> %}
The core implementation of algorithm R is in the commented reservoir sampling block. A plus side of using Algorithm R
is that it is much easier to understand, even if you know nothing about reservoir sampling.
{% </aside> %}

```rust,name=algorithm_r.rs
fn pick_random_wallpaper(dir: &Path) -> Result<Option<walkdir::DirEntry>, Box<dyn Error>> {
    let candidates = WalkDir::new(dir)
        .into_iter()
        .filter_map(Result::ok)
        // Filter using borrowed DirEntry to avoid early allocations
        .filter(|entry| entry.file_type().is_file() && is_supported_image(entry.path()));

    let mut chosen: Option<walkdir::DirEntry> = None;
    let mut rng = fastrand::Rng::new();

    // Reservoir sampling for a single item
    for (i, entry) in candidates.enumerate() {
        if rng.usize(..=i) == 0 {
            chosen = Some(entry);
        }
    }

    Ok(chosen)
}
```

## Appendix

Now that you know for a wallpaper directory of 51 images, algorithm R is faster. The natural next question is:
at what directory size does algorithm L dethrone algorithm R? It turns out that my current directory size was
right at the inflection point, if I had slightly more images this post might never have happened. The figure
below shows implementations for algorithm R and algorithm L optimised in the same way as the snippet above:

<div class="tufte-plot-container">
  <div class="tufte-plot-item">
    {{ <inline_svg path="posts/reservoir_sampling/images/inflection.svg" /> }}
  </div>
</div>

If you have more than approximately 70 wallpapers in your folder, you have my explicit permission to use Algorithm L,
it will be faster.

[^1]: [Who discovered Algorithm R?](https://markkm.com/blog/reservoir-sampling/)

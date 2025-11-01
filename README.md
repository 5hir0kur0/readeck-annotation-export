# Readeck Annotation Export

Basic tool to export [Readeck](https://readeck.org/) annotations as Markdown-formatted text.

The Readeck API supports exporting a whole article as Markdown (with the
annotations highlighted using `==` syntax). However, there is no built-in way to
export only the annotations themselves. This tool fills that gap by fetching the
article content and extracting only the annotated parts from the HTML and then
converting them to Markdown format.

Right now it just handles my specific use-case, but it could be extended to be more
flexible in the future.

## Features

- Export annotations for one or more articles by their IDs
- Converts HTML annotations to Logseq Markdown format (list of blockquotes)
- Can also export the annotations as plain text (Logseq markdown, with formatting *within* each quote stripped)
- Output format inspired by the Omnivore Logseq Plugin (currently not customizable)

## Usage

Clone the repository, install `uv`, and run the CLI tool with the article IDs:

```shell
# Set your Readeck API token and URL as environment variables
export READECK_AUTH_TOKEN=...
export READECK_URL='https://example.org'

uv run cli ARTICLE_ID [ARTICLE_ID ...]
```

## Example Output

<img width="2310" height="1696" alt="image" src="https://github.com/user-attachments/assets/f2e5fc0e-dea5-47d5-b566-c0500da519fd" />

The text is from highlights I made using Readeck for this blog post:

> Source: "Demystifying monads in Rust through property-based testing" — Rain.  
> © Rain 2020–present. Licensed under CC BY-NC-SA 4.0 unless marked otherwise.  
> URL: https://sunshowers.io/posts/monads-through-pbt/  
> Accessed: 2025-11-01


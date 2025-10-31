# Readeck Annotation Export

Basic tool to export Readeck annotations as Markdown-formatted text.

The Readeck API supports exporting a whole article as Markdown (with the
annotations highlighted using `==` syntax). However, there is no built-in way to
export only the annotations themselves. This tool fills that gap by fetching the
article content and extracting only the annotated parts from the HTML and then
converting them to Markdown format.

Right now it just handles my specific use-case, but it could be extended to be more
flexible in the future.

## Features

- Export annotations for one or more articles by their IDs
- Converts HTML annotations to Markdown format
- Can also export the annotations as plain text (with all formatting stripped)

## Usage

Clone the repository, install `uv`, and run the CLI tool with the article IDs:

```shell
# Set your Readeck API token and URL as environment variables
export READECK_AUTH_TOKEN=...
export READECK_URL='https://example.org'

uv run cli ARTICLE_ID [ARTICLE_ID ...]
```

## Example Output

TODO

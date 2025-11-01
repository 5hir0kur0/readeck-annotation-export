"""Command-line interface for readeck_annotation_export."""

import logging
import sys
import os
from .core import generate_articles


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {os.path.basename(sys.argv[0])} <article_id> [<article_id> ...]", file=sys.stderr)
        sys.exit(1)
    args = sys.argv[1:]
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(levelname)s: %(message)s")
    if not args:
        raise ValueError("No article IDs provided")
    articles = generate_articles(args)
    print(articles)

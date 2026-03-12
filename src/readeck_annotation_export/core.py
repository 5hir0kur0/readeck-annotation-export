import logging
import os
import urllib.request
import json
from datetime import datetime
from markdownify import markdownify
import http.client

from readeck_annotation_export.annotation_extractor import extract_readeck_annotations
from readeck_annotation_export.constants import (
    READECK_URL_FALLBACK,
    USE_HTML_EXTRACTION,
)

try:
    # The default limit of 100 headers may be too low for some requests
    http.client._MAXHEADERS = 1000
except:
    pass


def format_date(iso_date: str) -> str:
    iso_date = iso_date.split("T")[0]
    date = datetime.strptime(iso_date, "%Y-%m-%d")
    day = date.day
    suffix = (
        "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    )
    return "[[" + date.strftime(f"%b {day}{suffix}, %Y") + "]]"


def slash_join(s1: str, s2: str) -> str:
    return s1.rstrip("/") + "/" + s2.lstrip("/")


def readeck_url(*parts) -> str:
    result = os.environ.get("READECK_URL")
    result = result or READECK_URL_FALLBACK
    for part in parts:
        result = slash_join(result, part)
    return result


def generate_article(**article):
    properties = [
        "collapsed:: true",
        "type:: [[Article]]",
        f'url:: {article["url"]}',
        f'{article["authors"] and
           "author:: " + ", ".join(
            [f"[[{author}]]" for author in article["authors"]]
        ) or ""}',
        f'{f"links:: [[Readeck]]" +
           "".join([f", [[{label}]]" for label in article["labels"]]) +
           (article["site_name"] and f", [[{article["site_name"]}]]")}',
        f'{article.get("published", "") and "date-published:: " + format_date(article["published"])}',
    ]
    annotations_rendered = ""
    print(article)
    for annotation in article.get("annotations", []):
        lines = annotation["text"].split("\n")
        color = ""
        if annotation["color"] and annotation["color"] != "none":
            color = f'background-color:: {annotation["color"]}\n\t\t  '
        if "```" not in annotation["text"]:
            annotations_rendered += (
                    f"\t\t- {color}> " + "\n\t\t  > ".join(lines) + "\n"
            )
        else:
            # Fix code block rendering. Logseq doesn't support indented code blocks in blockquotes.
            # Use the following syntax instead:
            # #+BEGIN_QUOTE
            # ```
            # code...
            # ```
            # #+END_QUOTE
            annotations_rendered += (
                    f"\t\t- {color}#+BEGIN_QUOTE\n"
                    + "\n".join("\t\t  " + line for line in lines)
                    + "\n\t\t  #+END_QUOTE\n"
            )
        note = annotation.get("note") or ""
        if note:
            annotations_rendered += f"\t\t\t- {'\n\t\t\t  '.join(note.split('\n'))}\n"
    return (
            f'\t- [{article["title"]}]({
            readeck_url('bookmarks', article["id"])
            })\n'
            + "".join("\t  " + prop + "\n" for prop in properties if prop)
            + annotations_rendered
    )


def readeck_headers() -> dict[str, str]:
    auth_token = os.environ.get("READECK_AUTH_TOKEN")
    if not auth_token:
        raise ValueError("READECK_AUTH_TOKEN environment variable not set")
    headers = {
        "Authorization": f"Bearer {auth_token}",
    }
    return headers


def readeck_get(url):
    headers = readeck_headers()
    logging.debug("requesting: %s", readeck_url(url))
    req = urllib.request.Request(readeck_url(url), headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        return data


def readeck_get_raw(url: str) -> str:
    headers = readeck_headers()
    logging.debug("requesting: %s", readeck_url(url))
    req = urllib.request.Request(readeck_url(url), headers=headers)
    with urllib.request.urlopen(req) as response:
        data = response.read().decode("utf-8")
        return data


def get_bookmark(id):
    return readeck_get(f"/api/bookmarks/{id}")


def to_markdown(html: str) -> str:
    return markdownify(html, heading_style="ATX", bullets="*").strip()


def get_annotations(id: str):
    annotations = readeck_get(f"/api/bookmarks/{id}/annotations")
    if not USE_HTML_EXTRACTION:
        return annotations
    annotations_dict = {ann["id"]: ann for ann in annotations}
    data = readeck_get_raw(f"/api/bookmarks/{id}/article")
    html_annotations = extract_readeck_annotations(data)
    return [
        {"text": to_markdown(ann.text), "color": ann.color, "note": annotations_dict[ann.id].get("note")} for ann in
        html_annotations
    ]


def generate_articles(article_ids):
    articles = [get_bookmark(article_id) for article_id in article_ids]
    annotations = [get_annotations(article_id) for article_id in article_ids]
    articles_extended = [
        article | {"annotations": annotation}
        for article, annotation in zip(articles, annotations)
    ]
    heading = "- ## 🔖 Articles"
    return (
            heading
            + "\n"
            + "".join(generate_article(**article) for article in articles_extended)
    )

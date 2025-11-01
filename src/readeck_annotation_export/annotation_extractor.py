#!/usr/bin/env python3

from html.parser import HTMLParser
from collections import OrderedDict
import logging
import html
from dataclasses import dataclass, field
from typing import TypeVar, Optional, List

HtmlAttribute = tuple[str, str | None]  # (key, value) where value can be None
TagTuple = tuple[str, List[HtmlAttribute]]


def attributes_to_str(attrs: list[HtmlAttribute]) -> str:
    """Reconstruct attributes list (list of (k,v) tuples) into a string for a start tag."""
    if not attrs:
        return ""
    parts = []
    for k, v in attrs:
        if v is None:
            parts.append(k)
        else:
            # escape quotes in attribute values
            parts.append(f'{k}="{html.escape(v, quote=True)}"')
    return " " + " ".join(parts)


def open_tag_str(tag_tuple: tuple[str, list[HtmlAttribute]]) -> str:
    tag, attrs = tag_tuple
    return f"<{tag}{attributes_to_str(attrs)}>"

def close_tag_str(tag: str) -> str:
    return f"</{tag}>"


T = TypeVar("T")
def find_common_prefix(list_of_lists: list[list[T]]) -> list[T]:
    if not list_of_lists:
        return []
    prefix = list_of_lists[0]
    for lst in list_of_lists[1:]:
        # shrink prefix to match lst
        new_pref = []
        for a, b in zip(prefix, lst):
            if a == b:
                new_pref.append(a)
            else:
                break
        prefix = new_pref
        if not prefix:
            break
    return prefix

@dataclass
class Annotation:
    color: Optional[str]
    context: List[TagTuple]
    text: str
    pending_open_context: List[TagTuple] = field(default_factory=list)
    first_index: int = 0

def last_or_none(d: OrderedDict[str, T]) -> Optional[tuple[str, T]]:
    """Return the last value in the OrderedDict or None if empty."""
    return next(reversed(d.items())) if d else None

def ctx_up_to_section(stack: list[TagTuple]) -> list[TagTuple]:
    """Return the context up to the last <section> tag in the stack."""
    sec_index = -1
    for i in range(len(stack)-1, -1, -1):
        if stack[i][0] == "section":
            sec_index = i
            break
    return stack[sec_index+1 :] if sec_index != -1 else stack[:]

class ReadeckExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)  # we will handle charrefs/entities ourselves
        self.stack: list[tuple[str, list[HtmlAttribute]]] = []  # stack of (tag, attrs_list)
        self.annotations: OrderedDict[str, Annotation] = OrderedDict()  # id -> Annotation
        self.order_counter = 0

        # annotation parsing state
        self._inside_rd = False
        self._current_ann_id = None
        self._current_ann_color = None
        self._current_ann_text_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = list(attrs)  # list of (k, v)
        # push to stack
        self.stack.append((tag, attrs))

        if tag != "rd-annotation":
            # If we are inside an rd-annotation and a new start tag appears -> error
            if self._inside_rd:
                logging.error(
                    "Detected HTML start tag <%s> inside an <rd-annotation> (annotation id=%s). "
                    "Per spec, tags inside <rd-annotation> are an error.",
                    tag,
                    self._current_ann_id,
                )
            else:
                last_ann = last_or_none(self.annotations)
                if last_ann is not None:
                    ann = last_ann[1]
                    ann.pending_open_context.append((tag, attrs))
            return

        # entering an annotation
        # find id (data-annotation-id-value preferred) and color
        # attrs may contain ('data-annotation-id-value', '...') or ('id','annotation-...').
        ann_id = None
        color = None
        for k, v in attrs:
            if k == "data-annotation-id-value" and v:
                ann_id = v
            elif k == "data-annotation-color":
                color = v
        if ann_id is None:
            logging.error("rd-annotation tag missing data-annotation-id-value attribute; ignoring annotation.")
            return

        self._inside_rd = True
        self._current_ann_id = ann_id
        self._current_ann_color = color
        self._current_ann_text_parts = []

        # record in annotations dict (OrderedDict keeps insertion order)
        if ann_id not in self.annotations:
            self.annotations[ann_id] = Annotation( # type: ignore
                color=color,
                context=[],
                text="",
                first_index=self.order_counter,
            )
            self.order_counter += 1
            self.annotations[ann_id].context = self.stack[:-1]  # snapshot of stack without rd-annotation
            for ctx_tag in ctx_up_to_section(self.annotations[ann_id].context):
                self.annotations[ann_id].text += open_tag_str(ctx_tag)
        # update color if we didn't have it before
        if self.annotations[ann_id].color is None and color is not None:
            self.annotations[ann_id].color = color
        self.annotations[ann_id].text += ''.join(open_tag_str(s) for s in self.annotations[ann_id].pending_open_context)
        self.annotations[ann_id].context += self.annotations[ann_id].pending_open_context
        self.annotations[ann_id].pending_open_context = []
        return

    def handle_startendtag(self, tag, attrs):
        # treat as start followed by end
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        # pop from stack
        if self.stack[-1][0] != tag:
            logging.warning(
                "Mismatched end tag </%s>; expected </%s>. Ignoring.",
                tag,
                self.stack[-1][0],
            )
            return
        self.stack.pop()
        last_ann = last_or_none(self.annotations)
        if last_ann is not None and not self._inside_rd:
            ann = last_ann[1]
            if ann.pending_open_context and ann.pending_open_context[-1][0] == tag:
                # remove from pending and do not add to text
                ann.pending_open_context.pop()
            if not ann.pending_open_context and ann.context and ann.context[-1][0] == tag and tag != "section":
                # remove from context and add to text
                ann.context.pop()
                ann.text += close_tag_str(tag)
                return
        # If we are ending an rd-annotation, finalize the occurrence
        if tag == "rd-annotation":
            if not self._inside_rd:
                logging.warning(
                    "Encountered </rd-annotation> end tag while not inside an rd-annotation; "
                    "possible malformed HTML with <rd-annotation> tags."
                )
                # stray end tag; ignore
                return
            # capture context: tags after the last <section> in the stack
            # We want the context "up to the <section> level" -> find last index of tag == 'section' in stack
            stack_snapshot = self.stack[:]
            # find last 'section'
            sec_index = -1
            for i in range(len(stack_snapshot)-1, -1, -1):
                if stack_snapshot[i][0] == "section":
                    sec_index = i
                    break
            context = stack_snapshot[sec_index+1 :] if sec_index != -1 else stack_snapshot[:]

            # store occurrence
            text = "".join(self._current_ann_text_parts)
            self.annotations[self._current_ann_id].text += text # type: ignore

            # reset annotation state
            self._inside_rd = False
            self._current_ann_id = None
            self._current_ann_color = None
            self._current_ann_text_parts = []

    def handle_data(self, data):
        if self._inside_rd:
            # append raw data (keep entities as in original - we handle them in entity handlers)
            self._current_ann_text_parts.append(data)

    def handle_entityref(self, name):
        # &name;
        s = f"&{name};"
        if self._inside_rd:
            self._current_ann_text_parts.append(s)

    def handle_charref(self, name):
        # &#123; or &#x7b;
        s = f"&#{name};"
        if self._inside_rd:
            self._current_ann_text_parts.append(s)

    def handle_comment(self, data):
        # ignore comments
        pass

    def error(self, message):
        logging.error("HTMLParser error: %s", message)

@dataclass
class ExtractedAnnotation:
    id: str
    color: Optional[str]
    text: str

def extract_readeck_annotations(html_string: str) -> list[ExtractedAnnotation]:
    """
    Parse the html_string and return a list of annotation HTML strings (one per annotation id),
    ordered by first-seen order.
    """
    p = ReadeckExtractor()
    p.feed(html_string)
    p.close()

    results = []
    for ann_id, meta in p.annotations.items():
        ann = p.annotations[ann_id]
        # close any remaining open tags in context
        for tag, _ in reversed(ann.context):
            if tag == "section":
                break
            ann.text += close_tag_str(tag)
        results.append(ExtractedAnnotation(
            id=ann_id,
            color=meta.color,
            text=ann.text,
        ))

    return results

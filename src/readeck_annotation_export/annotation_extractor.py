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

# New small POD dataclasses for annotations
@dataclass
class AnnotationOccurrence:
    context: List[TagTuple]
    text: str

@dataclass
class Annotation:
    color: Optional[str]
    occurrences: List[AnnotationOccurrence] = field(default_factory=list)
    first_index: int = 0


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
            # If we are inside an rd-annotation and a new start tag appears -> error per spec
            if self._inside_rd:
                logging.warning(
                    "Detected HTML start tag <%s> inside an <rd-annotation> (annotation id=%s). "
                    "Per spec, tags inside <rd-annotation> are an error.",
                    tag,
                    self._current_ann_id,
                )
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
                occurrences=[],
                first_index=self.order_counter,
            )
            self.order_counter += 1
        else:
            # update color if we didn't have it before
            if self.annotations[ann_id].color is None and color is not None:
                self.annotations[ann_id].color = color

        return

    def handle_startendtag(self, tag, attrs):
        # treat as start followed by end
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        # If we are ending an rd-annotation, finalize the occurrence
        if tag == "rd-annotation":
            if not self._inside_rd:
                # stray end tag; ignore
                return
            # capture context: tags after the last <section> in the stack
            # The stack currently contains the rd-annotation itself as the top element; we pop it later below.
            # We want the context "up to the <section> level" -> find last index of tag == 'section' in stack (excluding the rd-annotation)
            # Note: stack currently includes rd-annotation at the top; but content's parent tags are those below it.
            # Use snapshot of stack excluding the last rd-annotation tuple.
            stack_snapshot = self.stack[:-1]
            # find last 'section'
            sec_index = -1
            for i in range(len(stack_snapshot)-1, -1, -1):
                if stack_snapshot[i][0] == "section":
                    sec_index = i
                    break
            context = stack_snapshot[sec_index+1 :] if sec_index != -1 else stack_snapshot[:]

            # store occurrence
            text = "".join(self._current_ann_text_parts)
            occ = AnnotationOccurrence(context=context, text=text)
            self.annotations[self._current_ann_id].occurrences.append(occ) # type: ignore

            # reset annotation state
            self._inside_rd = False
            self._current_ann_id = None
            self._current_ann_color = None
            self._current_ann_text_parts = []
            # pop the rd-annotation tag itself from stack below
            # (we will pop it again further down after this function)
        # Pop matching tag from stack (naive robust pop: pop last matching open tag)
        # Find the last occurrence of this tag on stack and pop up to it.
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                # remove from i..end
                del self.stack[i:]
                return
        # if not found, ignore

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


def extract_readeck_annotations(html_string: str) -> list[str]:
    """
    Parse the html_string and return a list of annotation HTML strings (one per annotation id),
    ordered by first-seen order.
    """
    p = ReadeckExtractor()
    p.feed(html_string)
    p.close()

    results = []
    for ann_id, meta in p.annotations.items():
        occurrences = meta.occurrences
        # compute final base: common prefix of all contexts
        contexts = [occ.context for occ in occurrences]
        base = find_common_prefix(contexts)

        # I think this approach works (based on the html output I've seen from Readeck).
        # It's not very elegant though and could probably be improved...

        # assemble content
        parts = []
        # open base tags
        for tag_tuple in base:
            parts.append(open_tag_str(tag_tuple))

        for occ in occurrences:
            ctx = occ.context
            prefix_len = len(base)
            extra = ctx[prefix_len:]
            # open extra tags
            for tag_tuple in extra:
                parts.append(open_tag_str(tag_tuple))
            # append the annotation inner text (already includes entity refs)
            parts.append(occ.text)
            # close extra tags in reverse order
            for tag_tuple in reversed(extra):
                parts.append(close_tag_str(tag_tuple[0]))

        # close base tags in reverse order
        for tag_tuple in reversed(base):
            parts.append(close_tag_str(tag_tuple[0]))

        final_html = "".join(parts)
        results.append(final_html)

    return results

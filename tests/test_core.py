import unittest

from readeck_annotation_export.annotation_extractor import extract_readeck_annotations


class TestWhitespaceNormalization(unittest.TestCase):
    """Whitespace in annotation text nodes should be collapsed outside preformatted blocks."""

    def _text(self, html):
        """Helper: extract the text of the first annotation from the given HTML."""
        return extract_readeck_annotations(html)[0].text

    def _ann(self, content):
        return f'<rd-annotation data-annotation-id-value="x">{content}</rd-annotation>'

    def test_newlines_in_plain_text_collapsed(self):
        html = self._ann("foo\nbar\nbaz")
        self.assertEqual(self._text(html), "foo bar baz")

    def test_multiple_spaces_collapsed(self):
        html = self._ann("foo   bar")
        self.assertEqual(self._text(html), "foo bar")

    def test_mixed_whitespace_collapsed(self):
        html = self._ann("foo \n\t bar")
        self.assertEqual(self._text(html), "foo bar")

    def test_newlines_in_paragraph_collapsed(self):
        html = f"<p>{self._ann('some text\nwith a newline\nand another')}</p>"
        self.assertEqual(self._text(html), "<p>some text with a newline and another</p>")

    def test_newlines_in_pre_preserved(self):
        html = f"<pre>{self._ann('line one\nline two\n  indented')}</pre>"
        self.assertEqual(self._text(html), "<pre>line one\nline two\n  indented</pre>")

    def test_newlines_in_code_preserved(self):
        html = f"<code>{self._ann('a\nb')}</code>"
        self.assertEqual(self._text(html), "<code>a\nb</code>")

    def test_text_before_pre_collapsed_text_in_pre_preserved(self):
        html2 = (
            '<p><rd-annotation data-annotation-id-value="a">intro\ntext</rd-annotation></p>'
            '<pre><rd-annotation data-annotation-id-value="b">code\nhere</rd-annotation></pre>'
        )
        results = {a.id: a.text for a in extract_readeck_annotations(html2)}
        self.assertEqual(results["a"], "<p>intro text</p>")
        self.assertEqual(results["b"], "<pre>code\nhere</pre>")


if __name__ == "__main__":
    unittest.main()

#! /usr/bin/env python3
#
# lib/rudiweb/transformers/markdown2html.py

"""Transform Markdown to HTML.
"""

import markdown

from lib.htmlwriter import Element, HTML5ElementFactory, HTMLParser


MARKDOWN_EXTENSIONS = [
    "admonition",
    "codehilite",
    "extra",
    "fenced_code",
    "tables",
    "toc",
]

ef = HTML5ElementFactory()

# TODO: instantiate markdown with extensions to speed up


def main(rudic, content, root, *args, **kwargs):
    """Transformer main.

    Keyword Args:
        extensions (list): Markdown extensions by name.
    """
    try:
        if type(content) == bytes:
            content = content.decode("utf-8")

        extensions = kwargs.get("extensions", [])

        # markdown content -> HTML -> HTMLWriter tree
        hp = HTMLParser()
        hp.feed(markdown.markdown(content, extensions=extensions, output_format="html"))

        body = root.find1(Element("body"))
        body.add(*hp.get_root().children)

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

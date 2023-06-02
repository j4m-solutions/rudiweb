#! /usr/bin/env python3
#
# lib/rudiweb/transformers/html2html.py

"""Transform raw html to HTMLWriter tree.
"""

from lib.htmlwriter import HTML5ElementFactory, HTMLParser

ef = HTML5ElementFactory()


def main(rudif, content, root, *args, **kwargs):
    try:
        head, body = root.get_headbody()

        if type(content) == bytes:
            content = content.decode("utf-8")

        # HTML content -> HTMLWriter tree
        hp = HTMLParser()
        hp.feed(content)

        body.addl(hp.get_root().children)

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

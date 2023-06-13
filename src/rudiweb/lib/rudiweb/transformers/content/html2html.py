#! /usr/bin/env python3
#
# lib/rudiweb/transformers/html2html.py

"""Transform raw html to HTMLWriter tree.
"""

from lib.htmlwriter import Element, HTMLParser


def main(rudic, content, root, *args, **kwargs):
    try:
        if type(content) == bytes:
            content = content.decode("utf-8")

        # HTML content -> HTMLWriter tree
        hp = HTMLParser()
        hp.feed(content)

        newroot = hp.get_root()
        if newroot.find1(Element("html")):
            # full document; use newroot instead
            return newroot
        else:
            body = root.find1(Element("body"))
            body.add(*hp.get_root().children)
            return root
    except Exception as e:
        raise Exception(f"error: {e}")

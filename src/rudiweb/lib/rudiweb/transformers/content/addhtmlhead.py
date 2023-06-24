#! /usr/bin/env python3
#
# lib/rudiweb/transformers/content/addhtmlhead.py

"""Add content to HTML <head> block.
"""

from lib.htmlwriter import Element, HTML5ElementFactory, Raw

ef = HTML5ElementFactory()


def main(rudic, content, root, *args, **kwargs):
    try:
        if rudic.rudif.get_extension() in [".html", ".htm"]:
            _content = kwargs.get("_content", None)

            head = root.find1(Element("head"))

            head.add(Raw(_content))

            return root
    except Exception as e:
        raise Exception(f"error: {e}")

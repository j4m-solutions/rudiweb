#! /usr/bin/env python3
#
# lib/rudiweb/transformers/txt2html.py

"""Transform plain text to HTML.
"""

from lib.htmlwriter import Element, HTML5ElementFactory


ef = HTML5ElementFactory()


def main(rudic, content, root, *args, **kwargs):
    try:
        if type(content) == bytes:
            content = content.decode("utf-8")

        body = root.find1(Element("body"))
        body.add(ef.pre(content.replace("<", "&lt;")))

        return root
    except Exception as e:
        raise Exception(f"error: {e}")


if __name__ == "__main__":
    main()

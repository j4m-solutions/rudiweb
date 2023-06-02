#! /usr/bin/env python3
#
# lib/rudiweb/transformers/txt2html.py

"""Transform plain text to HTML.
"""

from lib.htmlwriter import HTML5ElementFactory


ef = HTML5ElementFactory()


def main(rudif, content, root, *args, **kwargs):
    try:
        head, body = root.get_headbody()

        if type(content) == bytes:
            content = content.decode("utf-8")

        body.add(ef.pre(content.replace("<", "&lt;")))

        return root
    except Exception as e:
        raise Exception(f"error: {e}")


if __name__ == "__main__":
    main()

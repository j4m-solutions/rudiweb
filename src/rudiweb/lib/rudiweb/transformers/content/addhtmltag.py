#! /usr/bin/env python3
#
# lib/rudiweb/transformers/content/addhtmltag.py

"""Add "tag" to HTML.
"""

from lib.htmlwriter import Element, HTML5ElementFactory, HTMLParser

ef = HTML5ElementFactory()


def main(rudic, content, root, *args, **kwargs):
    """Transformer main.

    Keyword Args:
        bgcolor (str): CSS background color. Defaults to "black".
        border-radius (str): CSS Border radius. Defaults to "3px".
        color (str): CSS text color. Defaults to "white".
        html (str): Raw HTML content. No default.
        link (str): Link for `string`. No default.
        padding (str): CSS padding. Defaults to "8px 4px 8px 4px".
        string (str): Text. Used if `html` not provided. Defaults to
            "tag".
        style (str): CSS style settings. Defaults to none/empty.
        writing-mode: CSS writing mode. Defaults to "sideways-lr".
        z-index: CSS z-index. Defaults to "100".
    """
    try:
        if rudic.rudif.get_extension() in [".html", ".htm"]:
            bgcolor = kwargs.get("bgcolor", "black")
            border_radius = kwargs.get("border-radius", "3px")
            color = kwargs.get("color", "white")
            html = kwargs.get("html")
            link = kwargs.get("link")
            padding = kwargs.get("padding", "8px 4px 8px 4px")
            string = kwargs.get("string", "tag")
            style = kwargs.get("style", "")
            writing_mode = kwargs.get("writing-mode", "sideways-lr")
            z_index = kwargs.get("z-index", "100")

            body = root.find1(Element("body"))

            if html:
                hp = HTMLParser()
                hp.feed(html)
                contents = hp.get_root().children
            elif link:
                contents = [ef.a(string, _href=link)]
            else:
                contents = [string]

            # print(f"{contents=}")
            body.add(
                ef.div(
                    *contents,
                    _style=f" position: fixed;"
                    f"writing-mode: {writing_mode};"
                    f"background-color: {bgcolor};"
                    f"border-radius: {border_radius};"
                    f"color: {color};"
                    f"padding: {padding};"
                    f"z-index: {z_index};"
                    f"{style};",
                )
            )

            return root
    except Exception as e:
        raise Exception(f"error: {e}")

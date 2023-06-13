#! /usr/bin/env python3
#
# lib/rudiweb/transformers/content/addhtmltag.py

"""Add footer to HTML.
"""

from lib.htmlwriter import Element, HTML5ElementFactory

ef = HTML5ElementFactory()


def main(rudic, content, root, *args, **kwargs):
    try:
        if rudic.rudif.get_extension() in [".html", ".htm"]:
            bgcolor = kwargs.get("bgcolor", "black")
            border_radius = kwargs.get("border-radius", "3px")
            color = kwargs.get("color", "white")
            padding = kwargs.get("padding", "4px")
            string = kwargs.get("string", "footer")
            style = kwargs.get("style", "")
            writing_mode = kwargs.get("writing-mode", "sideways-lr")
            z_index = kwargs.get("z-index", "100")

            body = root.find1(Element("body"))

            body.add(
                ef.div(
                    string,
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

#! /usr/bin/env python3
#
# lib/rudiweb/transformers/bootstrap/decorate.py

"""Decorations using bootstrap.

* `<head>` settings for bootstrap
* navbar
* footer
"""

import logging

from lib.htmlwriter import Element, HTML5ElementFactory, Text


BRAND_LOGO_HREF = "/asis/img/brand-logo.png"
BRAND_NAME_TEXT = Text("brand name")
COPYRIGHT_STRING_TEXT = Text("Ⓒ 2023 company name")

logger = logging.getLogger(__name__)

ef = HTML5ElementFactory()

# static parts of the tree
HEAD = [
    ef.meta(_charset="utf-8"),
    ef.meta(_name='"viewport" content="width=device-width, initial-scale=1"'),
    ef.link(_href="/asis/bootstrap/css/bootstrap.min.css", _rel="stylesheet"),
    ef.link(_href="/asis/extra.css", _rel="stylesheet"),
    ef.link(_href="/asis/codehilite.css", _rel="stylesheet"),
]

NAVBAR = [
    ef.nav(
        _class=[
            "navbar",
            "sticky-top",
            "navbar-dark",
            "bg-dark",
            "navbar-expand-md",
            "py-1",
            "border-bottom",
            "border-success",
            "border-2",
        ],
    ).add(
        ef.div(_class="container").add(
            ef.a(_href="/", _class="navbar-brand",).add(
                BRAND_LOGO_IMG_ELEMENT := ef.img(
                    # TODO: bg-light!?!
                    _class=["img-fluid", "w-30"],
                    # _style="border-radius: 4px; max-width: 30px; max-height: 30px; margin: 4px;",
                    _style="border-radius: 4px; max-width: 30px; max-height: 30px; margin: 4px 4px 4px 0px;",
                    _src=BRAND_LOGO_HREF,
                    _alt="brand logo",
                ),
                " ",
                BRAND_NAME_TEXT,
            ),
            ef.button(
                _class="navbar-toggler",
                _type="button",
            )
            .add_attrs(
                ("data-bs-toggle", "collapse"),
                ("data-bs-target", "#navmenu"),
            )
            .add(
                ef.span(_class="navbar-toggler-icon"),
            ),
            ef.div(
                _class=["collapse", "navbar-collapse", "justify-content-md-center"],
                _id="navmenu",
            ).add(
                NAVBAR_UL_ELEMENT := ef.ul(_class=["navbar-nav", "ms-auto"]),
            ),
        ),
    )
]

FOOTER = [
    ef.section(_class="container").add(
        ef.div(_align="center").add(
            ef.hr(),
            COPYRIGHT_STRING_TEXT,
            " | ",
            "Powered by ",
            ef.a("rudiweb", _href="https://j4m-solutions.com/"),
            ".",
        ),
    ),
]

BOTTOM = [
    ef.script(_src="/asis/bootstrap/js/bootstrap.bundle.min.js"),
]


def main(rudic, content, root, *args, **kwargs):
    """Transformer main.

    Keyword Args:
        brand_logo_href (str): Reference to brand logo. Defaults to
            `/asis/img/brand-logo.png`. Located at top left.
        brand_logo_image_classes: Additional class attributes values
            for brand logo image. E.g., "bg-dark", "bg-light".
        brand_name (str): Brand name. Located at top left, after the
            logo.
        copyright_string (str): Copyright string for footer. Must include
            the Ⓒ symbol if wanted.
        navbar_items (list[dict]): List of dictionaries containing
            `text` and `link` items. These will be added to the navbar
            from left to right, right justified on the navbar.
    """
    try:
        head, body = root.get_headbody()

        # update from kwargs
        bootstrap_theme = kwargs.get("bootstrap_theme")
        brand_logo_image_classes = kwargs.get("brand_logo_image_classes")
        brand_logo_href = kwargs.get("brand_logo_href")
        brand_name = kwargs.get("brand_name")
        copyright_string = kwargs.get("copyright_string")
        navbar_items = kwargs.get("navbar_items")

        if bootstrap_theme:
            html = root.children[0]
            html.set_attr("data-bs-theme", bootstrap_theme)
        if brand_logo_image_classes:
            BRAND_LOGO_IMG_ELEMENT.add_attrs(_class=brand_logo_image_classes)
        if brand_logo_href:
            BRAND_LOGO_IMG_ELEMENT.set_attr("src", brand_logo_href)
        if brand_name:
            BRAND_NAME_TEXT.set(brand_name)
        if copyright_string:
            COPYRIGHT_STRING_TEXT.set(copyright_string)
        if navbar_items:
            # reset children (to avoid duplication)
            NAVBAR_UL_ELEMENT.children = []

            for d in navbar_items:
                text = d.get("text")
                link = d.get("link", "")
                if text:
                    NAVBAR_UL_ELEMENT.add(
                        ef.li(_class="nav-item").add(
                            ef.a(
                                text,
                                _href=link,
                                _class="nav-link",
                            ),
                        ),
                    )

        # TODO: prepend?
        head.addl(HEAD)
        try:
            parent, base = rudic.rudif.nameroot.rsplit("/", 1)
            head.add(ef.title(f"{base} ({parent})"))
        except:
            pass

        # navbar (slip in before the content)
        children = body.children
        body.children = []
        body.addl(NAVBAR)
        # body.add(ef.section(div := ef.div(_class="container")))
        # div.children.extend(children)
        body.addl(children)

        body.addl(FOOTER)
        body.addl(BOTTOM)

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

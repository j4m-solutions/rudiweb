#! /usr/bin/env python3
#
# lib/rudiweb/transformers/bootstrap/patchhtml.py

"""Patch plain HTML (and Markdown-originated HTML) with bootstrap
settings.
"""

import re

from lib.htmlwriter import Element, HTML5ElementFactory

ADMONITION2ATTRS = {
    "danger": ["alert", "alert-danger"],
    "dark": ["alert", "alert-dark"],
    "info": ["alert", "alert-info"],
    "light": ["alert", "alert-light"],
    "note": ["alert", "alert-note"],
    "primary": ["alert", "alert-primary"],
    "success": ["alert", "alert-success"],
    "secondary": ["alert", "alert-secondary"],
    "tip": ["alert", "alert-tip"],
    "warning": ["alert", "alert-warning"],
}

ef = HTML5ElementFactory()


def main(rudif, content, root, *args, **kwargs):
    try:
        passthroughs = kwargs.get("passthroughs", [".bhtml"])
        if rudif.get_extension() not in passthroughs:
            head, body = root.get_headbody()

            def patch(o):
                if type(o) != Element:
                    return

                # general
                if o.tag == "table":
                    o.add_attr("class", ["table", "table-striped", "table-hover"])

                elif o.tag == "div":
                    attr = o.attrs.get("class")
                    if attr == None:
                        return

                    # from markdown
                    if "admonition" in attr.values:
                        # in order of likelihood
                        if "info" in attr.values:
                            attr.extend(["alert", "alert-info"])
                        elif "note" in attr.values:
                            attr.extend(["alert", "alert-note"])
                        elif "warning" in attr.values:
                            attr.extend(["alert", "alert-warning"])
                        elif "tip" in attr.values:
                            attr.extend(["alert", "alert-tip"])
                        elif "danger" in attr.values:
                            attr.extend(["alert", "alert-danger"])
                        elif "success" in attr.values:
                            attr.extend(["alert", "alert-success"])
                        elif "primary" in attr.values:
                            attr.extend(["alert", "alert-primary"])
                        elif "secondary" in attr.values:
                            attr.extend(["alert", "alert-secondary"])
                        elif "dark" in attr.values:
                            attr.extend(["alert", "alert-dark"])
                        elif "light" in attr.values:
                            attr.extend(["alert", "alert-light"])
                        o.add_attr("role", "alert")

            body.walk_callback(patch)

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

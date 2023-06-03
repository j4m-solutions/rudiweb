#! /usr/bin/env python3
#
# lib/rudiweb/transformers/bootstrap/html2bhtml.py

"""Transform html to bhtml (support for bootstrap).

Simply wrap HTML as appropriate for bootstrap:
    <section>
        <div class="container">
            ...
        </div>
    </section>
"""

from lib.htmlwriter import HTML5ElementFactory

ef = HTML5ElementFactory()


def main(rudif, content, root, *args, **kwargs):
    try:
        head, body = root.get_headbody()

        passthroughs = kwargs.get("passthroughs", [".bhtml"])
        if rudif.get_extension() not in passthroughs:
            children = body.children
            body.children = []
            body.add(ef.section(ef.div(_class="container").addl(children)))

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

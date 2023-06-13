#! /usr/bin/env python3
#
# lib/rudiweb/transformers/bootstrap/image2html.py

"""Transform image file to inline HTML.
"""

import base64

from lib.htmlwriter import Element, HTML5ElementFactory


ef = HTML5ElementFactory()


def transform_base(content_type, s):
    return ef.img(
        _src=f'data:{content_type};charset=utf-8;base64,{base64.b64encode(s).decode("utf-8")}'
    )


def transform_gif(s):
    return transform_base("image/gif", s)


def transform_jpeg(s):
    return transform_base("image/jpeg", s)


def transform_png(s):
    return transform_base("image/png", s)


IMGTYPE2FN = {
    "gif": transform_gif,
    "jpeg": transform_jpeg,
    "jpg": transform_jpeg,
    "png": transform_png,
    # "svg": transform_svg,
}


def main(rudic, content, root, *args, **kwargs):
    """Transformer main.

    Keyword Args:
        imgtype (str): Image type (e.g., "png").
    """
    try:
        body = root.find1(Element("body"))
        body.add(ef.h1("Image"))

        imgtype = kwargs.get("imgtype")

        if not imgtype:
            body.add("no image type given")
        else:
            fn = IMGTYPE2FN.get(imgtype)
            if fn:
                body.add(fn(content))
            else:
                body.add(f"image type ({imgtype}) not supported")

        return root
    except Exception as e:
        raise Exception(f"error: {e}")

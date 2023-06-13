#! /usr/bin/env python3
#
# lib/rudiweb/transformers/directory2html.py

"""Show (optional) content followed by directory.
"""

import os
import os.path
from pathlib import Path

from lib.htmlwriter import Element, HTML5ElementFactory


ef = HTML5ElementFactory()


def main(rudic, content, root, *args, **kwargs):
    try:
        body = root.find1(Element("body"))

        server = rudic.server
        transpath = server.resolve_docpath(rudic.docpath)
        docdirname = rudic.docpath
        if not os.path.isdir(transpath):
            transpath = os.path.dirname(transpath)
            docdirname = os.path.dirname(rudic.docpath)

        table = ef.table(
            ef.thead(
                ef.tr(
                    ef.th("Name"),
                    ef.th("Type"),
                    ef.th("Size"),
                )
            ),
            tbody := ef.tbody(),
        )

        names = os.listdir(transpath)
        names.sort()

        for name in names:
            # hide index files
            if name in server.index_files:
                continue

            pp = Path(f"{transpath}/{name}")
            if pp.is_dir():
                stem = name
                ext = "directory"
                size = pp.stat().st_nlink
                name = f"{name}/"
            else:
                stem = pp.stem
                ext = pp.suffix[1:]
                size = pp.stat().st_size

            href = f"{docdirname}/{name}"

            tbody.add(
                ef.tr(
                    ef.td(ef.a(stem, _href=href)),
                    ef.td(ext),
                    ef.td(
                        str(size),
                    ),
                )
            )

        if not tbody.children:
            tbody.add(ef.tr(ef.td("No items", _colspan="3")))

        body.add(
            ef.div(f"Location: {docdirname}"),
            table,
        )

        return root
    except Exception as e:
        raise Exception(f"no directory listing {e}")


if __name__ == "__main__":
    main()

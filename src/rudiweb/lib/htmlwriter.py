#! /usr/bin/env python
#
# htmlwriter.py

"""Helper to write HTML.

HTMLWriter is a programmatic interface to building HTML documents. It
supports:

* well-formed documents (e.g., no missing tags)
* auto-escaping of text and attribute values
* inherited "defaults" (e.g., for attributes)
* overridable defaults (e.g., for attributes)
* reusable components

and more.

The main disadvantage of this package is that it is slower than using
strings and templates. But, this may not be an issue for many use
cases.
"""

from html import escape, unescape
from html.parser import HTMLParser as _HTMLParser

HTML5TAGS = {
    "a",
    "abbr",
    # "acronym",
    "address",
    # "applet",
    "area",
    "article",
    "aside",
    "audio",
    "b",
    "base",
    "basefont",
    "bdi",
    "bdo",
    # "big",
    "blockquote",
    "body",
    "br",
    "button",
    "canvas",
    "caption",
    # "center",
    "cite",
    "code",
    "col",
    "colgroup",
    "data",
    "datalist",
    "dd",
    "del",
    "details",
    "dfn",
    "dialog",
    # "dir",
    "div",
    "dl",
    "dt",
    "em",
    "embed",
    "fieldset",
    "figcaption",
    "figure",
    # "font",
    "footer",
    "form",
    # "frame",
    # "framset",
    "head",
    "header",
    "hgroup",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "html",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "keygen",
    "label",
    "legend",
    "li",
    "link",
    "main",
    "map",
    "mark",
    "menu",
    "menuitem",
    "meta",
    "meter",
    "nav",
    # "noframes",
    "noscript",
    "object",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "param",
    "picture",
    "pre",
    "progress",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "script",
    "section",
    "select",
    "small",
    "source",
    "span",
    # "strike",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "svg",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "track",
    # "tt",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
}

# render with newline after closing tag
NL_ELEMENTS = {
    "body",
    "br",
    "div",
    "hr",
    "p",
    "td",
    "th",
    "thead",
    "tbody",
    "tr",
}

# elements that do not take a closing tag
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "keygen",  # deprecated
    "link",
    "meta",
    "param",  # deprecated
    "source",
    "track",
    "wbr",
}


def is_void(tag):
    """Return if tag is for a void element."""
    return tag in VOID_ELEMENTS


class Attr:
    """Element attribute."""

    def __init__(self, name, values=None):
        """Initialize.

        Args:
            name (str): Attribute name.
            values (list): List of strings.
        """
        self.name = name
        self.values = values or []

    def append(self, v):
        """Add a value."""
        self.values.append(v)

    def clear(self):
        """Clear current values."""
        self.values = []

    def get(self):
        """Get values."""
        return self.values[:]

    def extend(self, values):
        """Extend with values."""
        self.values.extend(values)

    def render(self, extra=None):
        """Render safe attribute (name and value) string.

        Args:
            extra (Attr): Extra attr with values to apply.
        """
        values = self.values[:]
        if extra:
            values.extend(extra.values)
        return '%s="%s"' % (self.name, " ".join([escape(v) for v in values]))

    def set(self, values):
        """Set attribute values."""
        self.values = values[:]

    def tree(self, writer, parent):
        d = {
            "name": self.name,
            "type": "attribute",
            "self": self,
            "values": self.values,
        }
        return d


class Defaults:
    """Set of defaults to be applied when rendering.

    This makes it easy to apply defaults across many elements without
    repeatedly cluttering up the individual elements, themselves.
    """

    def __init__(self, name=None):
        self.name = name
        self.tag2attrs = {}

    def append_attrs(self, tag, **kwargs):
        """Append atttributes for tag."""
        attrs = self.tag2attrs.setdefault(tag, {})
        for k, values in kwargs.items():
            k = k.lstrip("_")
            attr = attrs.setdefault(k, Attr(k))
            attr.extend(values)

    def clear_attrs(self, tag):
        """Clear attributes for tag."""
        try:
            del self.tag2attrs[tag]
        except:
            pass

    def get_attrs(self, tag):
        """Get attributes for tag."""
        return self.tag2attrs.setdefault(tag, {})

    def keys(self):
        """Get tags."""
        return self.tag2attrs.keys()

    def load(self, filename):
        """Load settings from a YAML file.

        The format is:
            defaults:
                &lt;tag>:
                    attributes:
                        &lt;attr:
                            - &lt;value>
        """
        try:
            import yaml

            with open(filename, "r") as f:
                d = yaml.safe_load(f)

            defaults = d.get("defaults")
            if defaults:
                for tag, v in defaults.items():
                    self.append_attrs(tag, **v.get("attributes", {}))
        except Exception as e:
            import sys

            print(f"error: exception ({e})", file=sys.stderr)

    def set_attrs(self, tag, **kwargs):
        """Set (overwrite) attributes for tag.

        Args:
            tag (str): Tag.
            kwargs: Key-value settings for attributes.
        """
        attrs = self.tag2attrs.setdefault(tag, {})
        for k, values in kwargs.items():
            k = k.lstrip("_")
            attrs[k] = Attr(k, values)

    def tree(self, writer, parent):
        d = {
            "name": self.name,
            "type": "defaults",
            "self": self,
        }


class Comment:
    """HTML comment."""

    def __init__(self, s):
        self.s = s

    def render(self, writer, parent):
        return f"<!-- {escape(self.s)} -->"

    def set(self, s):
        self.s = s

    def tree(self, writer, parent):
        d = {
            "type": "comment",
            "self": self,
            "value": self.s,
        }
        return d


class Element:
    """HTML element."""

    def __init__(self, tag, *children, **kwargs):
        """Initialize.

        Args:
            tag (str): Tag.
            children (list): List of `str`, `Text`, `Element`.

        Keyword Args:
            defaults (Defaults): Additional (on top of those from
                `HTMLWriter`) defaults for rendering.
            <name>_ (list): List of attribute values for attribute
                `<name>` (trailing _ is stripped).
        """
        self.tag = tag
        self.children = []
        if children:
            self.addl(children)
        self.attrs = {}
        if kwargs:
            self.defaults = kwargs.get("defaults")
            self.add_attrs(**kwargs)
        else:
            self.defaults = None

    def __repr__(self):
        return f"""<Element tag="{self.tag}" nattrs="{len(self.attrs)}" at {hex(id(self))})>"""

    def add(self, *children) -> "Element":
        """Add child elements.

        Args:
            children (list): List of `str`, `Text`, or `Element`
                values.

        Returns:
            Self.
        """
        return self.addl(children)

    def addl(self, children) -> "Element":
        """Add list of child elements.

        Args:
            children (list): List of `str`, `Text`, or `Element`
                values.

        Returns:
            Self.
        """
        # TODO: validate object type of children
        for child in children:
            if isinstance(child, str):
                child = Text(child)
            self.children.append(child)
        return self

    def add_attr(self, name, value):
        attr = self.attrs.get(name)
        if not attr:
            attr = self.attrs[name] = Attr(name)
        if type(value) == str:
            value = [value]
        attr.extend(value)

    def add_attrs(self, *kvs, **kwargs):
        """Add attribute values.

        Args:
            *kvs (List[Tuple]): List of (key, value) tuples.

        Keyword Args:
            &lt;name> (str, list): List of string values associated with the
                attribute.
        """

        def _add(k, v):
            attr = self.attrs.get(k)
            if not attr:
                attr = self.attrs[k] = Attr(k)
            if type(v) == str:
                v = [v]
            attr.extend(v)

        for k, v in kvs:
            _add(k, v)

        for k, v in kwargs.items():
            k = k.lstrip("_")
            _add(k, v)

        return self

    def is_void(self):
        """Return True if this is a void element."""
        return is_void(self.tag)

    def render(self, writer, parent):
        """Render element (and children) with attributes.

        Args:
            writer (HTMLWriter)
            parent (Element|None): Parent element. `None` if topmost
                element (typically `&lt;html>`).

        The opening and closing tags enclose zero or more child
        elements. `render()` is called on each child. As a
        convenience, `str` children are converted to `Text`.
        """
        # print(f"render {self.tag=} {self.children=} {self.attrs=}")
        defaults = self.defaults or writer.defaults
        if defaults:
            defattrs = defaults.get_attrs(self.tag)
        else:
            defattrs = {}

        nl = self.tag in NL_ELEMENTS and "\n" or ""

        attrsl = []
        attrnames = set(self.attrs.keys()).union(defattrs.keys())
        for attrname in attrnames:
            attr = self.attrs.get(attrname)
            extra = defattrs.get(attrname)
            if attr == None:
                attr = extra
                extra = None
            if attr:
                attrsl.append(attr.render(extra))

        if self.is_void():
            # no closing tag, not children
            return "<%s %s>%s" % (self.tag, " ".join(attrsl), nl)
        else:
            childrenl = []
            for child in self.children:
                childrenl.append(child.render(writer, self))
            return "<%s%s%s>%s</%s>%s" % (
                self.tag,
                " " if attrsl else "",
                " ".join(attrsl),
                "".join(childrenl),
                self.tag,
                nl,
            )

    def set_attr(self, name, value):
        self.attrs[name] = Attr(name, [value])

    def tree(self, writer, parent):
        """Return tree of element (and children) with attributes.

        Args:
            writer (HTMLWriter)
            parent (Element|None): Parent element. `None` if topmost
                element (typically `&lt;html>`).

        The opening and closing tags enclose zero or more child
        elements. `render()` is called on each child. As a
        convenience, `str` children are converted to `Text`.
        """
        # print(f"render {self.tag=} {self.children=} {self.attrs=}")
        d = {
            "attrs": [attr.tree(writer, parent) for attr in self.attrs.values()],
            "defaults": self.defaults,
            "children": [child.tree(writer, self) for child in self.children],
            "tag": self.tag,
            "type": "element",
            "self": self,
            "void": self.is_void(),
        }
        return d

    def walk(self):
        """Walk the tree and return each object."""
        for child in self.children:
            yield child
            if type(child) == Element:
                yield from child.walk()

    def walk_callback(self, callback):
        """Walk tree and call callback for each object."""
        for o in self.walk():
            callback(o)


class Raw:
    """Raw markup."""

    def __init__(self, s):
        self.s = s

    def render(self, writer, parent):
        return self.s

    def set(self, s):
        self.s = s

    def tree(self, writer, parent):
        d = {
            "self": self,
            "type": "raw",
            "value": self.s,
        }
        return d


class Root:
    def __init__(self, *children):
        """Root."""
        self.children = []
        self.addl(children)

    def add(self, *children):
        self.addl(children)

    def addl(self, children):
        for child in children:
            if isinstance(child, str):
                child = Text(child)
            self.children.append(child)
        return self

    def get_headbody(self):
        try:
            return self.children[0].children[0:2]
        except:
            raise

    def render(self, writer, parent):
        childrenl = []
        for child in self.children:
            childrenl.append(child.render(writer, self))
        return "".join(childrenl)

    def tree(self, writer, parent):
        d = {
            "children": [child.tree(writer, self) for child in self.children],
            "type": "root",
            "self": self,
        }
        return d


class Text:
    """Text."""

    def __init__(self, s):
        self.s = s

    def render(self, writer, parent):
        """Render safely."""
        return escape(self.s)

    def set(self, s):
        self.s = s

    def tree(self, writer, parent):
        d = {
            "self": self,
            "type": "text",
            "value": self.s,
        }
        return d


class HTMLWriter:
    """Top-level object.

    Holds writer defaults and the top-level root element.
    """

    def __init__(self, defaults=None):
        """Initialize.

        Args:
            defaults (Defaults|None): Writer defaults applied to
                respective elements when rendered.
        """
        self.defaults = defaults or Defaults()
        self.root = Root()

    def render(self):
        """Render the document."""
        return self.root.render(self, None)

    def tree(self, writer, parent):
        return self.root.tree()


class ElementFactory:
    """Return an `Element` for the named tag."""

    def __init__(self, tags=None):
        self.tags = tags

    def __getattr__(self, name):
        def _Element(*args, **kwargs):
            return Element(name, *args, **kwargs)

        if self.tags == None or name in self.tags:
            return _Element

        raise Exception(f"invalid tag ({name})")


class HTML5ElementFactory(ElementFactory):
    def __init__(self, tags=None):
        tags = tags if tags != None else HTML5TAGS
        super().__init__(tags)

    def __getattr__(self, name):
        return super().__getattr__(name.lower())


class MatchException(Exception):
    pass


class Matcher:
    def __init__(self, fn):
        self._matchfn = fn

    def match1(self, o):
        for oo in self.match(o):
            return oo

    def match(self, o):
        try:
            if self._matchfn(o):
                yield o
            for child in getattr(o, "children", []):
                if self._matchfn(child):
                    yield o
        except:
            raise MatchException("bad match function")


class HTMLParser(_HTMLParser):
    """Parse html string to produce an `HTMLWriter` document."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hw = HTMLWriter()
        self.last = self.hw.root
        self.stack = [self.last]

    def handle_comment(self, data):
        self.last.add(Comment(unescape(data)))

    def handle_data(self, data):
        # print(f"data ({data=})")
        self.last.add(unescape(data))

    def handle_endtag(self, tag):
        # print(f"end tag ({tag=}) ({self.last=})")
        if type(self.last) == Root or tag != self.last.tag:
            print(
                f"warning: ignoring end tag ({tag}) void tag? ({is_void(tag)}) at ({self.getpos()}) stack ({self.stack})"
            )
            return

        self.stack.pop()
        try:
            last = self.last
            self.last = self.stack[-1]
        except:
            print(f"error: cannot pop last ({last=}) for tag ({tag=})")

    def handle_starttag(self, tag, attrs):
        el = Element(tag)
        # print(f"start tag ({tag=}) ({el=})")
        for attr in attrs:
            k, v = attr
            if k == "class":
                v = v.split()
            el.add_attr(k, unescape(v))
        self.last.add(el)
        if not is_void(tag):
            self.stack.append(el)
            self.last = el

    def is_valid(self):
        return len(self.stack) == 1

    def render(self):
        return self.hw.root.render(self.hw, None)

    def get_root(self):
        return self.hw.root

    def tree(self):
        return self.hw.root.tree(self.hw, None)

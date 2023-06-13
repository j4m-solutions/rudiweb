#! /usr/bin/env python3
#
# rudiweb/main.py

# rudiweb
#
# Copyright 2023 J4M Solutions
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Rudimentary web server.

Classes:

* `RudiAccess`
* `RudiConfig`
* `RudiFile`
* `RudiHandler`
* `RudiServer`
* `RudiSpace`
* `RudiTransformer`
"""

__VERSION__ = "0.2"

import base64
import calendar
from email.utils import formatdate, parsedate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import logging
import os
import os.path
import pathlib
import re
import secrets
import stat
import subprocess
import sys
import traceback
from urllib.parse import unquote, urlparse
import yaml

from lib.htmlwriter import HTML5ElementFactory, HTMLWriter

logger = logging.getLogger(__name__)

CGI_REQUEST_HEADERS = {
    "Content-Type": "CONTENT_TYPE",
    "Content-Length": "CONTENT_LENGTH",
    "Accept": "HTTP_ACCEPT",
    "Accept-Language": "HTTP_ACCEPT_LANGUAGE",
    "Cookie": "HTTP_COOKIE",
    "Date": "HTTP_DATE",
    "Host": "HTTP_HOST",
    "Origin": "HTTP_ORIGIN",
    "Referer": "HTTP_REFERER",
    "Range": "HTTP_RANGE",
    "User-Agent": "HTTP_USER_AGENT",
}

DEFAULT_SPACE_TYPE = "asis"

EXT_TO_CONTENTTYPE = {
    ".aac": "audio/aac",
    ".avi": "video/x-msvideo",
    ".bz": "application/x-bzip",
    ".bz2": "application/x-bzip2",
    ".css": "text/css",
    ".csv": "text/csv",
    ".directory": "application/directory",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".gif": "image/gif",
    ".htm": "text/html",
    ".html": "text/html",
    ".ico": "image/ico",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript",
    ".json": "application/json",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".odg": "application/vnd.oasis.opendocument.graphics",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".oga": "audio/ogg",
    ".ogv": "video/ogg",
    ".ogx": "application/ogg",
    ".opus": "audio/opus",
    ".otf": "font/otf",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".ppt": "application/ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".py": "text/plain",
    ".rtf": "application/rtf",
    ".svg": "image/svg+xml",
    ".sxc": "application/vnd.sun.xml.calc",
    ".sxd": "application/vnd.sun.xml.draw",
    ".sxi": "application/vnd.sun.xml.impress",
    ".sxw": "application/vnd.sun.xml.writer",
    ".tar": "application/x-tar",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".ts": "video/mp2t",
    ".ttf": "font/ttf",
    ".txt": "text/plain",
    ".vsd": "application/vnd.visio",
    ".wav": "audio/wav",
    ".weba": "audio/webm",
    ".webm": "video/webm",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".xhtml": "application/xhtml+xml",
    ".xls": "application/ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xml": "application/xml",
    ".zip": "application/zip",
    None: "application/octet-stream",
}

ASIS_EXTENSIONS = set(EXT_TO_CONTENTTYPE.keys())
for key in [".html", None]:
    ASIS_EXTENSIONS.discard(key)

DECORATABLE_EXTENSIONS = [".html"]

# available globally
server = None


class RudiAccess:
    """Access control manager.

    Note: Currently all or nothing access."""

    def __init__(self, topconfig):
        self.config = topconfig

    def is_authorized(self, headers, docpath):
        """Check if authorization is required for document."""
        try:
            # TODO: support realms by docpath
            if self.config.get("require-authorization", True) == False:
                return True
            else:
                authorization = headers.get("Authorization")
                if not authorization:
                    return False

                authkind, authuserpasswd = authorization.split(None, 1)
                if authkind.lower() != "basic":
                    return False

                userpasswd = base64.b64decode(authuserpasswd).decode("utf-8")
                user, passwd = userpasswd.split(":")
                if self.config.get("accounts", {}).get(user, {}).get("password") == passwd:
                    logger.debug(f"authorized user ({user=})")
                    return True
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

        return False


class RudiConfig(dict):
    """Dictionary with special methods."""

    def setup_authorization(self):
        """Set up authorization and account info."""
        if self.get("create-ephemeral-account", False):
            user, passwd = "user", secrets.token_urlsafe()
            accounts = self.setdefault("accounts", {})
            accounts[user] = {
                "name": user,
                "password": passwd,
            }
            return (user, passwd)


class RudiContext:
    """Content for processing."""

    def __init__(self, docpath, server, handler, rudis, rudif):
        self.docpath = docpath
        self.server = server
        self.handler = handler
        self.rudis = rudis
        self.rudif = rudif


class RudiFile:
    """File interface.

    *All* access to (content for serving) files must be done through
    this class.

    Note: Depends on global `server` for some information."""

    def __init__(self, handler, docpath, dtype=None, fallback=None):
        # TODO: should upgrade be done by caller?
        docpath = server.upgrade_index_file(docpath)

        self.handler = handler
        self.docpath = docpath
        self.dtype = dtype
        self.fallback = fallback

        self.path = server.resolve_docpath(self.docpath)

        # TODO: docpath should never be None!
        if self.docpath != None:
            self.nameroot, self.nameext = os.path.splitext(self.docpath)
        else:
            self.nameroot, self.nameext = None, None
        self.content_type = EXT_TO_CONTENTTYPE.get(self.nameext, EXT_TO_CONTENTTYPE.get(None))

        try:
            self.st = os.stat(self.path)
        except:
            self.st = None

    def _execute(self):
        """Execute file.

        Returns:
            Results as `str` or `bytes`. None on failure."""
        try:
            cp = subprocess.run(
                [self.path],
                capture_output=True,
                text=(self.dtype == "t"),
                env=self.get_cgi_variables(),
            )
            return cp.stdout
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def _read(self):
        """Read file.

        Returns:
            Results as `str` or `bytes`. None on failure."""
        try:
            if self.exists():
                plp = pathlib.Path(self.path)
                if self.dtype == "t":
                    return plp.read_text()
                else:
                    return plp.read_bytes()
            else:
                logger.debug(f"file not found ({self.path})")
                return self.fallback
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def exists(self):
        return self.st != None

    def get_cgi_variables(self):
        """Get dictionary of CGI variables.

        Request docpath is different from script docpath. This is
        important when includes/decorations are processed.
        """
        parsed = urlparse(self.handler.path)

        # TODO: trim some environ variables?
        env = os.environ.copy()

        # add CGI-specific variables
        env.update(
            {
                #
                # rudi-specific
                #
                "DOCPATH": self.docpath or "",
                "DOCUMENT_ROOT": server.document_root,
                "RUDI_ROOT": server.rudi_root,
                "SITE_ROOT": server.site_root,
                #
                # cgi
                #
                "PATH_INFO": parsed.path or "",
                "PATH_TRANSLATED": server.resolve_docpath(parsed.path) or "",
                "QUERY_STRING": parsed.query or "",
                # TODO: ensure ip address
                "REQUEST_ADDR": self.handler.client_address[0],
                # TODO: ensure fqdn
                "REQUEST_HOST": self.handler.client_address[0],
                "REQUEST_METHOD": self.handler.command,
                # TODO: set user
                "REQUEST_USER": "",
                # not real CGI setup, so get real path
                "SCRIPT_NAME": self.path and os.path.realpath(self.path) or "",
                "SERVER_NAME": server.server_name,
                "SERVER_PORT": str(server.server_port),
            }
        )

        # cgi request headers
        reqheaders = self.handler.headers
        for k, varname in CGI_REQUEST_HEADERS.items():
            v = reqheaders.get(k)
            if v != None:
                env[varname] = str(v)

        return env

    def get_content_type(self):
        """Get content type (based on extension)."""
        return self.content_type

    def get_extension(self):
        """Get extension from docpath."""
        return self.nameext

    def get_http_date(self):
        """Get modification time for non-executable in HTTP-Date
        format."""
        if not self.is_executable():
            return formatdate(self.st.st_mtime, usegmt=True)

    def is_dir(self):
        """Return if directory file type or not."""
        return stat.S_ISDIR(self.st.st_mode) != 0 if self.st != None else False

    def is_executable(self):
        """Return if executable or not."""
        return self.st.st_mode & stat.S_IXUSR != 0 if self.st != None else False

    def is_file(self):
        """Return if regular file type or not."""
        return stat.S_ISREG(self.st.st_mode) != 0 if self.st != None else False

    def is_newer(self, httpdate):
        """Return if given httpdate is newer than file modification
        time or not."""
        return (
            calendar.timegm(parsedate(httpdate)) > self.st.st_mtime if self.st != None else False
        )

    def load(self):
        """Load content. May be from regular file or executed results."""
        try:
            if self.is_dir():
                return "unavailable"
            elif self.is_executable():
                return self._execute()
            else:
                return self._read()
        except Exception as e:
            logger.debug(f"EXCEPTION ({e})")
            if self.fallback:
                return self.fallback
            else:
                return "" if self.dtype == "t" else b""


class RudiHandler(BaseHTTPRequestHandler):
    """Handler for all requests."""

    server_version = f"rudiweb/{__VERSION__}"

    def __init__(self, *args, **kwargs):
        # note: super() calls handler in its `__init__`!
        super().__init__(*args, **kwargs)
        # note: does not get here until close

    def do_GET(self):
        self.do_ALL()

    def do_HEAD(self):
        # not sending payload handled elsewhere (`write_payload()`)
        self.do_ALL()

    def do_POST(self):
        if 0:
            # TODO: only applies to an executable
            self.do_ALL()

    def do_ALL(self):
        """Centralized do_XXX (e.g., from `do_HEAD`, `do_GET`, and
        `do_POST`)."""

        # get docpath (cleaned up)
        parsed = urlparse(self.path)
        docpath = os.path.abspath(unquote(parsed.path))
        if parsed.path.endswith("/") and parsed.path != "/":
            docpath = f"{docpath}/"

        # setup `RudiSpace`, `RudiFile`
        rudis = self.server.get_space(docpath)
        rudif = RudiFile(self, docpath)

        # setup `RudiContext`
        rudic = RudiContext(docpath, self.server, self, rudis, rudif)

        # no space found
        if rudis == None:
            self.do_404_response(rudic)
            return

        # SECURITY: deny access to "/.rudi/"
        if docpath.startswith("/.rudi/"):
            self.do_404_response(rudic)
            return

        # SECURITY: check access
        if server.rudi_access.is_authorized(self.headers, docpath) == False:
            self.do_401_response(rudic)
            return

        # redirect if dir and docpath without trailing "/"
        if not rudif.docpath.endswith("/") and rudif.is_dir():
            # force use of trailing "/"
            self.do_301_response(rudic, f"{rudif.docpath}/")
            return

        # check that document/file exists
        if not rudif.exists():
            self.do_404_response(rudic)
            return

        # generate response
        if rudis.type == "asis":
            self.do_asis_response(rudic)
        else:
            self.do_default_response(rudic)

    def do_301_response(self, rudic, location):
        """301 Redirect response.

        Redirect to a new location."""
        status = HTTPStatus.MOVED_PERMANENTLY
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def do_304_response(self, rudic):
        """304 Not Modified response.

        Headers with *no* body."""
        status = HTTPStatus.NOT_MODIFIED
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.end_headers()

    def do_401_response(self, rudic):
        """401 Unauthorized response.

        Require authentication info in request."""
        status = HTTPStatus.UNAUTHORIZED
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.send_header("WWW-Authenticate", 'Basic realm="site"')
        self.end_headers()

    def do_404_response(self, rudic):
        """404 Not Found response."""
        status = HTTPStatus.NOT_FOUND
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.end_headers()

    def do_asis_response(self, rudic):
        """Respond with content as-is (unchanged), without decoration.

        This is suitable for as-is content.

        Note: All purely static content is subject to caching."""

        try:
            logger.debug(f"do_asis_response ({rudic.docpath=})")

            modified_since = self.headers.get("If-Modified-Since")
            if modified_since != None and not rudic.rudif.is_newer(modified_since):
                self.do_304_response(rudic)
            else:
                # load initial content
                content = rudic.rudif.load()

                # apply transformers
                transformers = rudic.rudis.get_transformers(rudic.rudif.get_extension())
                logger.debug(f"transformers ({transformers})")
                if transformers:
                    # load initial document
                    hw = HTMLWriter()
                    ef = HTML5ElementFactory()
                    hw.root.add(ef.html(ef.head(), ef.body()))

                    try:
                        for transformer in transformers:
                            hw.root = transformer.run(rudic, content, hw.root) or hw.root
                    except Exception as e:
                        print("====================================")
                        import traceback

                        traceback.print_exc()
                        raise

                    if hw.root:
                        payload = hw.render()
                    else:
                        payload = content
                else:
                    payload = content

                self.send_response(200)
                self.send_header("Content-Type", rudic.rudif.get_content_type())
                self.send_header("Content-Length", str(len(payload)))

                last_modified = rudic.rudif.get_http_date()
                if last_modified:
                    self.send_header("Cache-Control", "max-age=120")
                    self.send_header("Last-Modified", last_modified)
                self.end_headers()

                self.write_payload(payload)
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def do_debug_response(self, rudic):
        """Test response for debugging."""
        parts = [
            "<pre>\n",
            f"{self.headers=}\n",
            f"{self.client_address=}\n",
            f"{self.command=}\n",
            f"{self.path=}\n",
            "</pre>\n",
        ]
        payload = "".join(parts)

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()

        self.write_payload(payload)

    def do_decorated_response(self, rudic):
        """Response with decorated HTML content."""
        parts = []

        # load initial document
        hw = HTMLWriter()
        ef = HTML5ElementFactory()
        hw.root.add(ef.html(ef.head(), ef.body()))

        # load initial content
        content = rudic.rudif.load()

        # apply transformers
        transformers = rudic.rudis.get_transformers(rudic.rudif.get_extension())
        logger.debug(f"transformers ({transformers})")
        if transformers:
            try:
                for transformer in transformers:
                    hw.root = transformer.run(rudic, content, hw.root) or hw.root
            except Exception as e:
                raise

        payload = hw.render()

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()

        self.write_payload(payload)

    def do_default_response(self, rudic):
        """Main method to respond according to name extension.

        HTML is returned with transformers applied. All other content is
        returned as-is.

        If the HTML file has the user execute bit set (like
        `XBitHack`), it is executed in its own process with the output
        taken as the body.
        """
        try:
            logger.debug(f"do_default_response ({rudic.docpath=})")

            ext = rudic.rudif.get_extension()
            if ext in DECORATABLE_EXTENSIONS:
                self.do_decorated_response(rudic)
            elif ext in ASIS_EXTENSIONS:
                self.do_asis_response(rudic)
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def write(self, buf):
        """Convert/ensure buf to bytes as needed for the underlying
        byte stream.

        *All* writes must use this method."""
        try:
            if type(buf) == str:
                self.wfile.write(bytes(buf, "utf-8"))
            elif type(buf) == bytes:
                self.wfile.write(buf)
            else:
                raise Exception(f"unsupported data type ({type(buf)}")
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def write_payload(self, payload):
        """Write payload to stream."""
        if self.command in ["GET"]:
            self.write(payload)


class RudiServer(ThreadingHTTPServer):
    """HTTP server.

    Provide rudi-specific support.
    """

    server_version = f"rudiweb/{__VERSION__}"

    def __init__(self, config, *args, **kwargs):
        self.config = config

        #
        # basic
        self.site_root = config["site-root"]
        self.document_root = config["document-root"]
        self.rudi_root = config["rudi-root"]
        self.debug = config.get("debug", {}).get("enable", False)

        # setup
        self.setup_access()
        # self.setup_asis()
        self.setup_index_files()
        self.setup_space_order()
        self.setup_spaces()

        # init superclass
        logger.debug(f"{self.site_root=} {self.document_root=} {self.rudi_root}")
        logger.debug(f"{args=} {kwargs=}")
        logger.debug(f"{config=}")
        super().__init__((config["host"], config["port"]), *args, **kwargs)

        self.setup_ssl()

    def get_space(self, docpath):
        """Return match of space for docpath."""
        for spacename in self.spaceorder:
            rudis = self.spaces.get(spacename)
            if rudis.is_match(docpath):
                return rudis

    def match_asis_document(self, docpath):
        """Return match for asis settings."""
        for cregexp in self.asis_cregexps:
            m = cregexp.match(docpath)
            if m:
                return m

    def resolve_docpath(self, docpath):
        """Get real path from path for the docpath."""
        if docpath != None:
            if docpath.startswith("/.rudi/"):
                relpath = docpath[6:]
                basepath = self.rudi_root
            else:
                relpath = docpath
                basepath = self.document_root
        else:
            return None

        relpath = os.path.abspath(f"/{relpath}")
        path = os.path.normpath(f"{basepath}{relpath}")
        return path

    def resolve_sitepath(self, sitepath):
        """Get real path for the sitepath."""
        if sitepath != None:
            if sitepath.startswith("/"):
                return sitepath
            return f"{self.site_root}/{sitepath}"
        return None

    def setup_access(self):
        self.rudi_access = RudiAccess(self.config)

    def setup_asis(self):
        # TODO: move this out of server (but ensure it is computed once?)
        self.asis_cregexps = [
            re.compile(x)
            for x in self.config.get("content", {}).get("asis", {}).get("regexps", [])
        ]

    def setup_index_files(self):
        self.index_files = self.config.get("index-files", ["index.html"])

    def setup_space_order(self):
        self.spaceorder = self.config.get("space-order", [])

    def setup_spaces(self):
        self.spaces = {}
        for spacename, spaceconfig in self.config.get("spaces").items():
            self.spaces[spacename] = RudiSpace(spaceconfig)

    def setup_ssl(self):
        """Set up SSL for server socket.

        TODO: Complete implementation.
        """
        try:
            if not self.config.get("ssl", {}).get("enable", False):
                # SECURITY: open communication!
                return

            ssl_keyfile = self.config.get("ssl", {}).get("key-file")
            ssl_certfile = self.config.get("ssl", {}).get("cert-file")

            if None in [ssl_keyfile, ssl_certfile]:
                return

            if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
                os.exit(1)
        except Exception as e:
            logger.debug(f"EXCEPTION ({e})")
            raise

    def upgrade_index_file(self, docpath):
        # return upgrade to index file, if appropriate
        if docpath.endswith("/"):
            for index_file in self.index_files:
                _docpath = f"{docpath}{index_file}"
                path = server.resolve_docpath(_docpath)
                if os.path.exists(path):
                    docpath = _docpath
                    break
        return docpath


class RudiSpace:
    """Content space."""

    def __init__(self, config):
        self.config = config
        self.type = config.get("type", DEFAULT_SPACE_TYPE)

        self.cregexps = []
        self.ext2transformers = {}
        self.transformers = {}

        self.setup_regexps()
        self.setup_extensions()
        self.setup_transformers()

    def get_transformers(self, ext, extonly=False):
        """Return transformers according to ext. By default, also
        include those registered for "pre" and "post".
        """
        # get a *copy* so it can be updated below!
        transformers = self.ext2transformers.get(ext, [])[:]
        if not extonly:
            pre = self.ext2transformers.get("pre")
            post = self.ext2transformers.get("post")
            if pre:
                transformers = pre + transformers
            if post:
                transformers.extend(post)

        return transformers

    def get_transformer_extensions(self):
        return list(self.ext2transformers.keys())

    def is_match(self, docpath):
        for cregexp in self.cregexps:
            m = cregexp.match(docpath)
            if m:
                return m

    def setup_extensions(self):
        # TODO: extensions by space?
        EXT_TO_CONTENTTYPE.update(self.config.get("extensions", {}))

    def setup_regexps(self):
        for regexp in self.config.get("regexps", []):
            self.cregexps.append(re.compile(regexp))

    def setup_transformers(self):
        """Set up transformers."""
        try:
            self.ext2transformers = {}

            config = self.config.get("transformers", {})
            for ext, tconfigs in config.items():
                l = []
                for tconfig in tconfigs:
                    absfname = tconfig.get("function")
                    args = tconfig.get("args", [])
                    kwargs = tconfig.get("kwargs", {})
                    l.append(RudiTransformer(absfname, args, kwargs))
                self.ext2transformers[ext] = l

            DECORATABLE_EXTENSIONS.extend(self.get_transformer_extensions())
        except Exception as e:
            raise


class RudiTransformer:
    """Content transformer."""

    def __init__(self, absfname, args, kwargs):
        try:
            self.absfname = absfname

            pkgname, modname, fname = absfname.rsplit(".", 2)
            logger.debug(f"loading pkg ({pkgname}) module ({modname}) function ({fname})")

            mod = importlib.import_module(f".{modname}", pkgname)
            fn = getattr(mod, fname)

            self.fn = fn
            self.args = args
            self.kwargs = kwargs
        except Exception as e:
            logger.debug(f"error: {e}")

            # SECURITY: do not continue if transformer is not available
            raise

    def __repr__(self):
        return f"<RudiTransformer absfname={self.absfname}>"

    def run(self, rudic, content, root):
        return self.fn(rudic, content, root, *self.args, **self.kwargs)


def setup_logging(topconfig):
    """Set up logging."""
    global logger

    loggingconf = topconfig.get("logging")
    if loggingconf == None or not loggingconf.get("enable", False):
        return

    logfilename = loggingconf.get("filename")
    logformat = loggingconf.get("format", "%(asctime)s - %(levelname)s - %(message)s")
    loghandler = loggingconf.get("handler")
    loglevel = loggingconf.get("level", logging.CRITICAL)

    kwargs = {
        "level": logging.getLevelName(loglevel),
        "format": logformat,
    }
    if loghandler == "file":
        if logfilename:
            kwargs["handlers"] = [logging.FileHandler(logfilename)]
    elif loghandler == "stream":
        kwargs["handlers"] = [logging.StreamHandler()]

    # only if there is a handler
    if kwargs.get("handlers"):
        logging.basicConfig(**kwargs)
    logger = logging.getLogger(__name__)


def print_usage():
    progname = os.path.basename(sys.argv[0])
    print(
        f"""\
usage: {progname} [<args>] <configfile>
       {progname} -h|--help

Arguments:
--create-ephemeral-account
                Create a one-time ephemeral account and password.
--document-root Path of "document" tree.
--require-authorization
                Require authorization to access the site.
--rudi-root     Path for internal docpaths starting at "/.rudi/".
--site-root     Path of "site" tree.
<configfile>    YAML configuration file.
""",
        end="",
    )


class ArgOpts:
    pass


def main():
    global logger, server

    try:
        argopts = ArgOpts()
        argopts.config_filename = None
        argopts.create_ephemeral_account = None
        argopts.document_root = None
        argopts.require_authorization = None
        argopts.rudi_root = None
        argopts.site_root = None

        config = None

        args = sys.argv[1:]
        while args:
            arg = args.pop(0)
            if arg in ["-h", "--help"]:
                print_usage()
                sys.exit(0)
            elif arg == "--create-ephemeral-account":
                argopts.create_ephemeral_account = True
            elif arg == "--document-root" and args:
                argopts.document_root = args.pop(0)
            elif arg == "--require-authorization":
                argopts.require_authorization = True
            elif arg == "--rudi-root" and args:
                argopts.rudi_root = args.pop(0)
            elif arg == "--site-root" and args:
                argopts.site_root = args.pop(0)
            elif not args:
                argopts.config_filename = arg

        try:
            if argopts.config_filename == None:
                raise Exception()
            config = RudiConfig()
            config.update(yaml.safe_load(open(argopts.config_filename)))

        except Exception as e:
            raise Exception("bad/missing configuration file")

        # argument overrides
        if argopts.create_ephemeral_account != None:
            config["create-ephemeral-account"] = argopts.create_ephemeral_account
        if argopts.document_root != None:
            config["document-root"] = argopts.document_root
        if argopts.require_authorization != None:
            config["require-authorization"] = argopts.require_authorization
        if argopts.rudi_root != None:
            config["rudi-root"] = argopts.rudi_root
        if argopts.site_root != None:
            config["site-root"] = argopts.site_root

        # default overrides
        if config.get("host") == None:
            config["host"] = "localhost"
        if config.get("port") == None:
            config["port"] = 8090

        # validate
        if config.get("site-root") == None:
            raise Exception("site-root not set")
        if not config.get("site-root").startswith("/"):
            path = os.path.dirname(os.path.abspath(argopts.config_filename))
            path = f"{path}/{config['site-root']}"
            config["site-root"] = path
        if not os.path.isdir(config["site-root"]):
            raise Exception("site-root does not exist")
        if config.get("document-root") == None:
            config["document-root"] = f"{config['site-root']}/html"
        if config.get("rudi-root") == None:
            config["rudi-root"] = f"{config['site-root']}/rudi"

        # tweak
        config["site-root"] = os.path.abspath(config.get("site-root"))
        config["document-root"] = os.path.abspath(config.get("document-root"))
        config["rudi-root"] = os.path.abspath(config.get("rudi-root"))
    except SystemExit:
        raise
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    # connection info
    print(f"starting at http://{config['host']}:{config['port']} ...")

    # setup authorization, account info
    userpasswd = config.setup_authorization()
    if userpasswd:
        print(f"ephemeral account: user={userpasswd[0]} password={userpasswd[1]}")

    # logging
    setup_logging(config)

    # update sys.path
    sys.path.insert(0, f"""{config["site-root"]}/lib""")

    # start server
    server = RudiServer(
        config,
        RudiHandler,
    )

    try:
        print("running ...")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass

    print(f"exiting ...")


if __name__ == "__main__":
    main()

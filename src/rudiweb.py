#! /usr/bin/env python3
#
# rudiweb.py

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
"""

__VERSION__ = "0.1"

import base64
import calendar
from email.utils import formatdate, parsedate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

EXT_TO_CONTENTTYPE = {
    ".aac": "audio/aac",
    ".avi": "video/x-msvideo",
    ".bz": "application/x-bzip",
    ".bz2": "application/x-bzip2",
    ".css": "text/css",
    ".csv": "text/csv",
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


# available globally
server = None


class RudiAccess:
    """Access control manager.

    Note: Currently all or nothing access."""

    def __init__(self, config):
        self.config = config

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
        if 0:
            # TODO: drop body
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

        # SECURITY: deny access to "/.rudi/"
        if docpath.startswith("/.rudi/"):
            self.do_404_response(None)
            return

        # SECURITY: check access
        if server.rudi_access.is_authorized(self.headers, docpath) == False:
            self.do_401_response(None)
            return

        # set up `RudiFile` (work with rudif here and below)
        rudif = RudiFile(self, docpath)

        # redirect if dir and docpath without trailing "/"
        if not rudif.docpath.endswith("/") and rudif.is_dir():
            # force use of trailing "/"
            self.do_301_response(rudif, f"{rudif.docpath}/")

        # generate response
        if server.match_asis_document(rudif.docpath):
            self.do_asis_response(rudif)
        else:
            self.do_default_response(rudif)

    def do_301_response(self, rudif, location):
        """301 Redirect response.

        Redirect to a new location."""
        status = HTTPStatus.MOVED_PERMANENTLY
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def do_304_response(self, rudif):
        """304 Not Modified response.

        Headers with *no* body."""
        status = HTTPStatus.NOT_MODIFIED
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.end_headers()

    def do_401_response(self, rudif):
        """401 Unauthorized response.

        Require authentication info in request."""
        status = HTTPStatus.UNAUTHORIZED
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.send_header("WWW-Authenticate", 'Basic realm="site"')
        self.end_headers()

    def do_404_response(self, rudif):
        """404 Not Found response."""
        status = HTTPStatus.NOT_FOUND
        logger.debug(f"""{status.value} {status.phrase}""")

        self.send_response(status)
        self.end_headers()

    def do_asis_response(self, rudif):
        """Respond with content as-is (unchanged), without decoration.

        This is suitable for as-is content.

        Note: All purely static content is subject to caching."""

        try:
            logger.debug(f"do_asis_response ({rudif.docpath=})")

            modified_since = self.headers.get("If-Modified-Since")
            if modified_since != None and not rudif.is_newer(modified_since):
                self.do_304_response(rudif)
            else:
                payload = rudif.load()

                self.send_response(200)
                self.send_header("Content-Type", rudif.get_content_type())
                self.send_header("Content-Length", str(len(payload)))

                last_modified = rudif.get_http_date()
                if last_modified:
                    self.send_header("Cache-Control", "max-age=120")
                    self.send_header("Last-Modified", last_modified)
                self.end_headers()
                self.write(payload)
        except Exception as e:
            if server.debug:
                traceback.print_exc()
            logger.debug(f"EXCEPTION ({e})")

    def do_debug_response(self, rudif):
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
        self.write(payload)

    def do_decorated_response(self, rudif):
        """Response with decorated HTML content."""
        parts = []

        # TODO: missing <title> in <head> block!
        parts.append(RudiFile(self, "/.rudi/includes/top.html", dtype="t").load())
        parts.append(RudiFile(self, "/.rudi/includes/navbar.html", dtype="t").load())
        parts.append(rudif.load())
        parts.append(RudiFile(self, "/.rudi/includes/footer.html", dtype="t").load())
        parts.append(RudiFile(self, "/.rudi/includes/bottom.html", dtype="t").load())

        # clean up
        if None in parts:
            logger.debug("found None in respl")
            parts = filter(None, parts)
        parts = [b if type(b) == bytes else b.encode("utf-8") for b in parts]
        payload = b"".join(parts)

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.write(payload)

    def do_default_response(self, rudif):
        """Main method to respond according to name extension.

        HTML is returned with decorations. All other content is
        returned asis without decoration.

        Decoration is taken from files under `{site_doc}/includes/`:
        - `top.html` - First content: from `&lt;html>` to `&lt;body>`,
            including any content for &lt;head>.
        - `navbar.html` - Navigation bar content using &lt;navbar>.
        - `footer.html` - Footer content at the bottom of the output.
        - `bottom.html` - Last content: up to and including
            `&lt;body>&lt;html>`.

        If the HTML file has the user execute bit set (like
        `XBitHack`), it is executed in its own process with the output
        taken as the body. Decorations still apply.
        """
        try:
            docpath = rudif.docpath

            logger.debug(f"do_default_response ({docpath=})")

            _, ext = os.path.splitext(docpath)
            path = server.resolve_docpath(docpath=docpath)
            if not os.path.exists(path):
                self.do_404_response(docpath)
                return

            if ext in [".html"]:
                self.do_decorated_response(rudif)
            elif ext in ASIS_EXTENSIONS:
                self.do_asis_response(rudif)
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


class RudiServer(ThreadingHTTPServer):
    """HTTP server.

    Provide rudi-specific support.
    """

    server_version = "rudiweb/0.1"

    def __init__(self, config, *args, **kwargs):
        self.config = config

        #
        # basic
        self.site_root = config["site-root"]
        self.document_root = config["document-root"]
        self.rudi_root = config["rudi-root"]
        self.debug = config.get("debug", {}).get("enable", False)

        self.rudi_access = RudiAccess(config)

        # content
        # TODO: move this out of server (but ensure it is computed once?)
        self.asis_cregexps = [
            re.compile(x) for x in config.get("content", {}).get("asis", {}).get("regexps", [])
        ]
        self.index_files = config.get("index-files", ["index.html"])

        # init superclass
        logger.debug(f"{self.site_root=} {self.document_root=} {self.rudi_root}")
        logger.debug(f"{args=} {kwargs=}")
        logger.debug(f"{config=}")
        super().__init__((config["host"], config["port"]), *args, **kwargs)

        if config.get("ssl", {}).get("enable", False) == True:
            self.setup_ssl()

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

    def setup_ssl(self):
        """Set up SSL for server socket."""
        # TODO: complete implementation
        try:
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


def setup_logging(config):
    """Set up logging."""
    global logger

    loggingconf = config.get("logging")
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

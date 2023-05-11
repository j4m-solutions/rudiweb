# rudiweb

A rudimentary web server based on the Python library `HTTPServer`.

The primary goals of rudiweb are:

* Support dynamic content for any content type.
* Support reusable decorations (e.g., top, bottom, navbar).
* Have minimimal dependencies (Python, Python standard library, yaml).
* Be useful for quick setup applications (small, single file, single
    configuration).

## Components

rudiweb is provides components:

* `RudiAccess` - Access control helper.
* `RudiConfig` - Configuration.
* `RudiFile` - Interface for content file access.
* `RudiHandler` - Subclass of `HTTPRequestHandler`.
* `RudiServer` - Subclass of `HTTPServer`.
* `RudiTransformer` - Transforms native content to HTML.

## Site Organization

Content is served from various locations in the filesystem:

* `site-root` - Base site content. See [Site Root](#site-root).
* `document-root` - Document content. See [Document Root](#document-root).
* `rudi-root` - Rudi content. See [rudi-root](#rudi-root).

A site is typically organized as:

```
{site-root}/
  bin/
  html/
    asis/
  rudi/
    includes/
```

`bin/` contains executable files that are symlinked to from the `html/` area. Symlinking is used so that the `.html` extension can be used conveniently in url paths without trying to serve up code files as regular, decorated pages.

`rudi/includes/` contains decoration files for `top.html`, `bottom.html`, `navbar.html`, and `footer.html`. These are not kept in the main `html/` area as they are not intended to be served up independently (as general content).

`html/` contains all servable content.

`html/asis/` contains all as-is content that is to be served without decorations.

## Features

### As-is Content

Content that should not be decorated must be served up as-is. This is specified in the configuration using regular expressions which are used to match against document paths.

A recommended base setup is:

```
content:
  asis:
    regexps:
      - "^/asis/.*"
      - "^/favicon\\.ico$"
```

Make sure to deal with "." and ".*" properly.

### Authorization and Accounts

To restrict access to the web server content, authorization can be required. Also, an emphemeral account and password can be generated. This is suitable for short term, one-shot instances, after which the
server is shut down.

### Cache Control

Basic cache control is supported for static, as-is content.

* Default cache setting: `max-age=120`.
* Support request `If-Modified-Since` and response `Last-Modified`
    headers.

Non-static, and non-as-is content is never to be cached.

### Content Type

A non-exhaustive map of filename extension to mime-type is provided. This is used in the response header `Content-Type`.

### Debugging:

Debugging may be enabled so that additional debugging information is output.

### Document Root

Documents are served from the document root.

### Index Files

When the URL path component refers to a directory, the default is to look for a `index.html` file. Which index files to look for.

A recommended base configuration is:

```
index-files:
  - index.html
  - index.htm
```

### Listening for Connections

The web server listens on a host and port.

### Logging

By default, the server outputs results for each request.

Additional logging is supported for logger calls.


### RudiFile

`RudiFile` provides the sole interface to loading content. It supports static (read) and dynamic (executable) content. Regardless of filename extension, if the user execute bit is set (like `XBitHack`), it is executed. Its content is then served.

### SSL

For long term usage, SSL is best supported using another web server like Apache or Nginx where it handles SSL, keys, and certificates, and forwards requests and responses.

For short term usage, a locally generated SSL key and certificate work fine.

See also, Authorization and Accounts

### rudi-root

Some content is *not* within the document tree (i.e., under [Document Root](#document-root)). Such things as decorations are kept separate because they are not intended to be served by themselves. These are stored under the `rudi-root` which maps to `/.rudi/` but is inaccessible to outside.

Internally, references to `/.rudi/<path>` are served up from `<rudi-root>/<path>` and subject to standard content serving rules.

By default, `rudi-root` is set to `<site-root>/rudi`.

### Site Root

By default, site content is served from the `site-root`.

See also [Document Root](#document-root) and [rudi-root](#rudi-root).

### Transformers

A transformer is used when content needs to be transformed. This is typically done to convert from native format (non-HTML) content to HTML. Such is the case for converting markdown to HTML.

Other kinds of transformations may be done, too, such as decorating HTML.

Extensions (".".prefixed) are the primary means to select transformations to apply. There are also special `pre` and `post` extensions (non "."-prefix) which are applied before and after the extension transformers are called, respectively.

Note: Transformers are *not* applied to asis content.

A configuration could look like:

```
content:
  transformers:
    .md:
      - function: rudiweb.transformers.markdown2html.main
        args: []
        kwargs: {}
      ...
    pre: []
    post:
      - function: rudiweb.transformers.cleanup.main
```

A transformer is applied to content *after* it is loaded in the normal fashion. Which means that static and dynamic (see [RudiFile](#rudifile)) content works as before.

## Configuration

rudiweb uses a YAML file for configuration.

| Field | Default | Required? | Description |
|-|-|-|-|
| `accounts.<user>.name` | - | - | User account name. Should match `<user>`. |
| `accounts.<user>.password` | - | - | User account password. |
| `content.asis.regexps` | - | - | List of regular expressions against which to match url paths for as-is content. |
| `content.transformers.<ext>` | - | - | List of transformers to call for extension. Extensions are "."-prefixed (e.g., `.gif`). Special cases are `pre` and `post` which are applied before and after the normal extension transformations. |
| `content.transformers.<ext>.<element>.args` | - | - | List of arguments to pass to the transformer. |
| `content.transformers.<ext>.<element>.function` | - | - | Absolute function name (`pkgname.modname.fname`) of transformer. |
| `content.transformers.<ext>.<element>.kwargs` | - | - | Dictionary of keyword arguments to pass to the transformer. |
| `create-ephemeral-account` | False | - | Create one-time ephemeral account with a generate password. |
| `debug.enable` | False | - | Enable debugging. |
| `document-root` | `{site-root}/html` | - | Where content is located. |
| `host` | localhost | - | Interface on which to listen. Use the host name to listen for network connections. |
| `index-files` | `["index.html"]` | - | List of index file filenames. |
| `port` | 8090 | - | Port on which to listen. |
| `ssl.enable` | False | - | Enable SSL. |
| `ssl.key-file` | - | - | SSL key file. Keep secure (user readable only). |
| `ssl.cert-file` | - | - | SSL certificate file.|
| `logging.enable` | False | - | Enable logging. |
| `logging.filename` | - | - | Log filename for `file` handler. |
| `logging.format` | `%(asctime)s - %(levelname)s - %(message)s` | - | Log entry format. |
| `logging.handler` | - | - | Handler to use: stream (`StreamHandler`), file (`FileHandler`). |
| `logging.level` | `CRITICAL` | - | Logging level (see Python docs). |
| `require-authorization` | `False` | - | Require authentication for authorization to access content. |
| `rudi-root` | `{site-root}/rudi` | - | Where internal content is located. |
| `site-root` | - | ✅ | Site root where support files are location (e.g., under `bin/`, `html/`, and possibly `rudi/`). A relative path is checked under the same directory as the configuration file.  |

## Install

```
mkdir ~/tmp
cd ~/tmp
git clone https://github.com/j4m-solutions/rudiweb.git
```

## Run Server

If there is an existing rudiweb site configuration file available:
```
~/tmp/rudiweb/src/rudiweb/main.py <configfile>
```

See [demos](https://github.com/j4m-solutions/rudiweb-examples).

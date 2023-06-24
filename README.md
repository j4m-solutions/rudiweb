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
* `RudiContext` - Context for generating response.
* `RudiFile` - Interface for content file access.
* `RudiHandler` - Subclass of `HTTPRequestHandler`.
* `RudiServer` - Subclass of `HTTPServer`.
* `RudiSpace` - Space configuration within the site.
* `RudiTransformer` - Transforms native content, not just HTML.

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

### RudiContext

Among other arguments, transformers accept a `RudiContext` argument, which contains:

* `docpath` - The resolved document path for object being served.
* `server` - The `RudiServer` object.
* `handler` - The `RudiHandler` object.
* `rudis` - The `RudiSpace` object matched for the `docpath` and user.
* `rudif` - The `RudiFile` object corresponding to the `docpath`.

These objects provide full access to all objects need for information and communication.

### RudiFile

`RudiFile` provides the sole interface to loading content. It supports static (read) and dynamic (executable) content. Regardless of filename extension, if the user execute bit is set (like `XBitHack`), it is executed. Its content is then served.

### RudiSpace

Web site content is defined by spaces (`RudiSpace)`). Spaces are independent of the others, each with their own regular expressions for document path matching, extras extensions, transformers, and type of content (e.g., "asis", "type").

Although not useful/accessible at the moment, overlapping of document paths is supported. This will become useful once access control is applied to spaces.

### RudiTransformer

A transformer transforms content prior to being sent to the client. This process typically converts from native format (non-HTML) content to HTML. Such is the case for converting markdown to HTML.

Other kinds of transformations may be done, too, such as decorating HTML, modifying non-HTML content (e.g., raw images, etc).

Extensions ("."-prefixed) are the primary means to select transformations to apply. There are also special `pre` and `post` pseudo-extensions (non "."-prefixed) which are applied before and after the extension-specific transformers are called.

Note: Transformers can now be applied to asis content.

A configuration (under the `spaces` section) could look like:

```
spaces:
  main:
    regexp:
      - ".*"
    transformers:
      .md:
        - function: lib.rudiweb.transformers.content.markdown2html.main
          args: []
          kwargs: {}
        ...
      pre: []
      post:
        - function: lib.rudiweb.transformers.bootstrap.decorate.main
    type: html
```

There is no "pre" transformer. The `markdown2html` transformer is applied to files with the ".md" extension. The `bootstrap.decorate` "post" transformer is applied to the html tree. The result is markdown content is presented as HTML with decorations using Bootstrap support.

### rudi-root

Some content is *not* within the document tree (i.e., under [Document Root](#document-root)). Such things as decorations are kept separate because they are not intended to be served by themselves. These are stored under the `rudi-root` which maps to `/.rudi/` but is inaccessible to outside.

Internally, references to `/.rudi/<path>` are served up from `<rudi-root>/<path>` and subject to standard content serving rules.

By default, `rudi-root` is set to `<site-root>/rudi`.

### Site Root

By default, site content is served from the `site-root`.

See also [Document Root](#document-root) and [rudi-root](#rudi-root).

### SSL

For long term usage, SSL is best supported using another web server like Apache or Nginx where it handles SSL, keys, and certificates, and forwards requests and responses.

For short term usage, a locally generated SSL key and certificate work fine.

See also, Authorization and Accounts

## Configuration

rudiweb uses a YAML file for configuration.

| Field | Default | Required? | Description |
|-|-|-|-|
| `accounts.<user>.name` | - | - | User account name. Should match `<user>`. |
| `accounts.<user>.password` | - | - | User account password. |
| `create-ephemeral-account` | False | - | Create one-time ephemeral account with a generate password. |
| `debug.enable` | False | - | Enable debugging. |
| `document-root` | `{site-root}/html` | - | Where content is located. |
| `host` | localhost | - | Interface on which to listen. Use the host name to listen for network connections. |
| `index-files` | `["index.html"]` | - | List of index file filenames. |
| `logging.enable` | False | - | Enable logging. |
| `logging.filename` | - | - | Log filename for `file` handler. |
| `logging.format` | `%(asctime)s - %(levelname)s - %(message)s` | - | Log entry format. |
| `logging.handler` | - | - | Handler to use: stream (`StreamHandler`), file (`FileHandler`). |
| `logging.level` | `CRITICAL` | - | Logging level (see Python docs). |
| `port` | 8090 | - | Port on which to listen. |
| `require-authorization` | `False` | - | Require authentication for authorization to access content. |
| `rudi-root` | `{site-root}/rudi` | - | Where internal content is located. |
| `site-root` | - | ✅ | Site root where support files are location (e.g., under `bin/`, `html/`, and possibly `rudi/`). A relative path is checked under the same directory as the configuration file.  |
| `spaces.<spacename>.extensions` | - | - | Dictionary of extensions to content-type. These are in addition to the standard support. |
| `spaces.<spacename>.regexps` | - | ✅ | List of regular expressions against which to match document (url) paths. |
| `spaces.<spacename>.transformers.<ext>` | - | - | List of transformers to call for extension. Extensions are "."-prefixed (e.g., `.gif`). Special cases are `pre` and `post` which are applied before and after the normal extension transformations. |
| `spaces.<spacename>.transformers.<ext>.<element>.args` | - | - | List of arguments to pass to the transformer. |
| `spaces.<spacename>.transformers.<ext>.<element>.function` | - | - | Absolute function name (`pkgname.modname.fname`) of transformer. |
| `spaces.<spacename>.transformers.<ext>.<element>.kwargs` | - | - | Dictionary of keyword arguments to pass to the transformer. |
| `spaces.<spacename>.type` | `asis` \| `html` | ✅ | Type of content to serve. Use `asis` for non-HTML content (undecorated images, CSS, HTML). Use `html` for decorated HTML content. |
| `ssl.enable` | `False` | - | Enable SSL. |
| `ssl.key-file` | - | - | SSL key file. Keep secure (user readable only). |
| `ssl.cert-file` | - | - | SSL certificate file.|

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

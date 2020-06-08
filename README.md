# DPack

DPack is a static asset packager, written primarily for Django applications.

## Installation

`pip install dpack`

DPack has a number of optional processors for things like minification and compilation:

* `pip install dpack[cssmin]`
* `pip install dpack[jsmin]`
* `pip install dpack[sass]`

Or get everything with `pip install dpack[all]`.

## Configuration

DPack can be configured either via a `dpack.yaml` file, or via a `DPACK` setting if using Django. The following options
are available:

* `assets` - a dictionary whose keys are paths of files to be created (relative to `output`), and whose values are
  lists of files to process and concatenate into said file. Each input file in the list may be prefixed by one or more
  processors by specifying the processor name followed by a colon. For instance, `cssmin:sass:somefile.scss` tells
  DPack to first compile `somefile.scss` (found by searching in `search` directories) using SASS, then minify it
  using the `cssmin` processor.
* `defaults` - a dictionary whose keys are file extensions (without the `.`), and whose values are lists of
  processors to use by default for input files of that type.
* `output` - the path to store packed assets under. If not specified, this will be a temporary directory created using
  `tempfile`.
* `prefix` - the URL prefix compiled assets will ultimately be served from, used when rewriting `url` and `@import`
  declarations in CSS files via the `rewrite` processor. If using Django, this defaults to `STATIC_URL`.
* `register` - a dictionary whose keys are processor names you wish to register (or override), and whose values are
  dotted-path strings that resolve to a callable. See processors below.
* `search` - a list of directories to search for input files in. If using Django, input files will be searches by using
  any `STATICFILES_FINDERS` that are not DPack itself.

### `dpack.yaml`

```yaml
assets:
  compiled/site.css:
  - app1/first.css
  - app2/second.css
  - cssmin:sass:app3/third.scss
  compiled/site.js:
  - app1/first.js
  - app2/second.js
defaults:
  css:
  - rewrite
  - cssmin
  js:
  - jsmin
output: ./build
prefix: /static/
register:
  custom: myapp.processors.custom
search:
- ./app1/static
- ./app2/static
```

### `DPACK` Setting

```python
DPACK = {
    "assets": {
        "compiled/site.css": [
            "app1/first.css",
            "app2/second.css",
            "cssmin:sass:app3/third.scss",
        ],
        "compiled/site.js": [
            "app1/first.js",
            "app2/second.js",
        ],
    },
    "defaults": {
        "css": ["rewrite", "cssmin"],
        "js": ["jsmin"]
    },
    "output": "./build",
    "register": {
        "custom": "myapp.processors.custom"
    },
}
```

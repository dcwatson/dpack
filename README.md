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
  `tempfile.mkdtemp(prefix="dpack-")`.
* `prefix` - the URL prefix compiled assets will ultimately be served from, used when rewriting `url` and `@import`
  declarations in CSS files via the `rewrite` processor. If using `DPackFinder`, this defaults to `STATIC_URL`.
* `register` - a dictionary whose keys are processor names you wish to register (or override), and whose values are
  dotted-path strings that resolve to a callable. See processors below.
* `search` - a list of directories to search for input files in. If using `DPackFinder`, input files will be searches
  by using any `STATICFILES_FINDERS` that are not `DPackFinder` itself.

### Example `dpack.yaml`

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

### Example `DPACK` Setting

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

## Using DPackFinder With Django

Simply add `dpack.finders.DPackFinder` to your `STATICFILES_FINDERS` setting, and DPack will search for inputs using
Django's `staticfiles` app, output compiled assets when `collectstatic` is called, and generate assets on-the-fly when
serving with `runserver` (`DEBUG=True`) or via the `django.contrib.staticfiles.views.serve` view.

```python
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "dpack.finders.DPackFinder",
)
```

If you compile an asset to `compiled/css/site.css`, you can reference it as you would any other static asset, with
`{% static "compiled/css/site.css" %}` in your templates. These assets are also then post-processed by your
`STATICFILES_STORAGE`, so you can use things like [Whitenoise](http://whitenoise.evans.io)'s `CompressedManifestStaticFilesStorage` with no extra configuration.

## Command Line Interface

DPack comes with a command-line utility, unsurprisingly named `dpack`. Run by itself, it will look for a `dpack.yaml`
config file and pack any assets it finds according to the config. You can specify a config file (`-c`) or Django
settings module (`-s`), and dump out the loaded config using `dpack -y`. Run `dpack -h` for a full list of options.

## Processors

Processors are simply Python callables that take three arguments: `text` (the processed text so far), `input` (the
`dpack.base.Input` object containing things like relative `name` and absolute `path`), and `packer` (an instance of
`dpack.DPack` containing things like `prefix`). For example, the `cssmin` processor is implemented as:

```python
def process(text, input, packer):
    return rcssmin.cssmin(text)
```

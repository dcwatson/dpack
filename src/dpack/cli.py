import argparse
import os
import sys

import yaml

from .base import DPack
from .serve import serve


def main(*args):
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="config file to use (dpack.yaml by default)",
    )
    parser.add_argument(
        "-s", "--settings", default=settings_module, help="Django settings module"
    )
    parser.add_argument(
        "-o", "--output", default=None, help="override output directory"
    )
    parser.add_argument(
        "-y", "--yaml", action="store_true", default=False, help="print YAML config"
    )
    parser.add_argument("command", nargs="*")
    options = parser.parse_args(args=args or None)
    overrides = {}
    if options.output:
        overrides["output"] = options.output
    if options.settings:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", options.settings)
        # If you call dpack -s at the same level as manage.py, you probably expect it to
        # find your settings module.
        sys.path.insert(0, os.getcwd())
        import django

        from .finders import DjangoDPack

        django.setup()
        packer = DjangoDPack(options.config, **overrides)
    else:
        packer = DPack(options.config, **overrides)
    if options.yaml:
        print(yaml.safe_dump(packer.dump_config()))
        sys.exit(1)
    if not options.command:
        packer.pack()
    elif options.command[0] == "serve":
        serve(packer.__class__, options.config, overrides)
    else:
        print("Unknown command: {}".format(options.command[0]), file=sys.stderr)
        sys.exit(1)

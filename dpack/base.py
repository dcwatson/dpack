import importlib
import logging
import os
import tempfile

import yaml

from .processors import __all__ as builtin_processors

logger = logging.getLogger("dpack")


class Input:
    def __init__(self, name, path, processors=None):
        self.name = name
        self.path = path
        self.processors = processors

    def __str__(self):
        return self.name

    def modified(self, mtime):
        return os.path.getmtime(self.path) > mtime

    def process(self, packer):
        with open(self.path, "r") as f:
            text = f.read()
        for proc in self.processors:
            module_name, method_name = proc.rsplit(".", 1)
            module = importlib.import_module(module_name)
            method = getattr(module, method_name)
            text = method(text, self, packer)
        return text


class DPack:
    def __init__(self, config=None, **options):
        config_opts = self.load_config(config or "dpack.yaml", raise_if_missing=bool(config))
        config_opts.update(options)
        self.configure(config_opts)

    def load_config(self, config_file, raise_if_missing=False):
        try:
            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError as e:
            if raise_if_missing:
                raise e
        return {}

    def dump_config(self):
        return {
            "output": self.location,
            "search": self.search,
            "prefix": self.prefix,
            "register": {name: method for name, method in self.processors.items() if name not in builtin_processors},
            "defaults": self.defaults,
            "concat": self.concat,
            "assets": self.assets,
        }

    def configure(self, config):
        self.location = config.get("output") or tempfile.mkdtemp(prefix="dpack-")
        self.search = config.get("search", ".")
        self.prefix = config.get("prefix", "")
        if isinstance(self.search, str):
            self.search = [self.search]
        self.processors = {name: "dpack.processors.{}.process".format(name) for name in builtin_processors}
        self.processors.update(config.get("register", {}))
        self.defaults = {"css": ["rewrite"]}
        for name, procs in config.get("defaults", {}).items():
            if isinstance(procs, str):
                procs = [procs]
            for proc in procs:
                if proc not in self.processors:
                    raise Exception("Unknown processor: {}".format(proc))
            self.defaults[name] = procs
        self.concat = {"js": "\n;\n"}
        self.concat.update(config.get("concat", {}))
        self.assets = config.get("assets", {})

    def find_input(self, name):
        """
        Returns the full path of the specified input name, if it exists. By default, all directories in self.search
        are searched.
        """
        for root in self.search:
            path = os.path.join(root, name)
            if os.path.exists(path):
                return path
        return None

    def iter_assets(self):
        """
        Yields (asset_name, inputs) pairs, where inputs is a list of Input objects.
        """
        for name, specs in self.assets.items():
            if isinstance(specs, str):
                specs = [specs]
            inputs = []
            for spec in specs:
                *processors, input_name = spec.split(":")
                if processors:
                    # cssmin:sass:somefile.sass should process as cssmin(sass(somefile.sass))
                    processors = list(reversed(processors))
                else:
                    ext = os.path.splitext(input_name)[1].replace(".", "").lower()
                    processors = self.defaults.get(ext, [])
                # Check for unknown processors.
                for proc in processors:
                    if proc not in self.processors:
                        raise Exception("Unknown processor: {}".format(proc))
                # Resolved processors into dotted method paths.
                processors = [self.processors[proc] for proc in processors]
                path = self.find_input(input_name)
                if path:
                    inputs.append(Input(input_name, path, processors))
                else:
                    # TODO: should probably raise an exception here, with an option to ignore missing inputs.
                    logger.error("Input not found: {}".format(input_name))
            yield name, inputs

    def modified(self, inputs, mtime=0):
        """
        Returns (quickly) if any of the inputs were modified since mtime.
        """
        for i in inputs:
            if i.modified(mtime):
                return True
        return False

    def pack(self, asset=None, force=False):
        """
        Packs one or all assets. By default, assets will only be packed if they have not been previously packed, or if
        any of the inputs to an asset have changed since the last time it was packed. To force packing, set force=True.
        To pack only a single asset, specify a path.
        """
        for name, inputs in self.iter_assets():
            if asset and asset != name:
                continue
            path = os.path.join(self.location, name)
            mtime = os.path.getmtime(path) if os.path.exists(path) else 0
            if force or mtime == 0 or self.modified(inputs, mtime):
                ext = os.path.splitext(name)[1].replace(".", "").lower()
                sep = self.concat.get(ext, "\n")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                logger.debug("Packing {} <<< {}".format(name, " | ".join(str(i) for i in inputs)))
                with open(path, "w") as output:
                    for idx, i in enumerate(inputs):
                        if idx > 0:
                            output.write(sep)
                        output.write(i.process(self))

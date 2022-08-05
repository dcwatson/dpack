import glob
import importlib
import logging
import os
import tempfile

import yaml

from .processors import __all__ as builtin_processors

logger = logging.getLogger("dpack")


class Input:
    def __init__(self, name, path, processors=None, depends=None):
        self.name = name
        self.path = path
        self.processors = processors or []
        self.depends = depends or []

    def __str__(self):
        return self.name

    def check_paths(self):
        yield self.path
        root = os.path.dirname(self.path)
        for dep in self.depends:
            yield from glob.iglob(os.path.join(root, dep))

    def modified(self, mtime):
        for path in self.check_paths():
            if os.path.getmtime(path) > mtime:
                return True
        return False

    def process(self, packer):
        with open(self.path, "r", encoding="utf-8") as f:
            text = f.read()
        for proc in self.processors:
            module_name, method_name = proc.rsplit(".", 1)
            module = importlib.import_module(module_name)
            method = getattr(module, method_name)
            text = method(text, self, packer)
        return text


class DPack:
    def __init__(self, config=None, base_dir=None, **options):
        self.base_dir = base_dir
        config_opts = self.load_config(
            config or "dpack.yaml", raise_if_missing=bool(config)
        )
        config_opts.update(options)
        self.configure(config_opts)

    def resolve(self, path):
        path = str(path)
        if path.startswith("/") or not self.base_dir:
            return path
        return os.path.abspath(os.path.normpath(os.path.join(self.base_dir, path)))

    def load_config(self, config_file, raise_if_missing=False):
        try:
            with open(self.resolve(config_file), "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError as e:
            if raise_if_missing:
                raise e
        return {}

    def dump_config(self):
        defaults = self.defaults.copy()
        if defaults.get("css") == ["rewrite"]:
            defaults.pop("css")
        concat = self.concat.copy()
        if concat.get("js") == "\n;\n":
            concat.pop("js")
        register = {
            name: method
            for name, method in self.processors.items()
            if name not in builtin_processors
        }
        config = {
            "assets": self.assets,
        }
        if not self.ephemeral:
            config["output"]: self.location
        if self.search != ["."]:
            config["search"] = self.search
        if self.prefix:
            config["prefix"] = self.prefix
        if register:
            config["register"] = register
        if defaults:
            config["defaults"] = defaults
        if concat:
            config["concat"] = concat
        return config

    def configure(self, config):
        self.location = config.get("output") or tempfile.mkdtemp(prefix="dpack-")
        self.ephemeral = not config.get("output")
        self.search = config.get("search", ".")
        if isinstance(self.search, str):
            self.search = [self.search]
        self.prefix = config.get("prefix", "")
        self.processors = {
            name: "dpack.processors.{}.process".format(name)
            for name in builtin_processors
        }
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

    @property
    def storage_path(self):
        return self.resolve(self.location)

    def find_input(self, name):
        """
        Returns the full path of the specified input name, if it exists. By default,
        all directories in self.search are searched.
        """
        for root in self.search:
            path = os.path.join(self.resolve(root), name)
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
                if isinstance(spec, str):
                    depends = []
                elif isinstance(spec, dict):
                    spec, depends = list(spec.items())[0]
                else:
                    raise ValueError("Unknown input type: {}".format(spec))
                *processors, input_name = spec.split(":")
                if processors:
                    # cssmin:sass:somefile.sass --> cssmin(sass(somefile.sass))
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
                    inputs.append(Input(input_name, path, processors, depends))
                else:
                    # TODO: should probably raise an exception here, with an option to
                    # ignore missing inputs.
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

    def pack_to(self, asset, output, encoding="utf-8"):
        """
        Packs a single asset directly into an output buffer with the specified encoding.
        Used when serving assets directly for development.
        """
        for name, inputs in self.iter_assets():
            if asset != name:
                continue
            ext = os.path.splitext(name)[1].replace(".", "").lower()
            sep = self.concat.get(ext, "\n").encode(encoding)
            logger.debug(
                "Packing {} <<< {}".format(name, " | ".join(str(i) for i in inputs))
            )
            for idx, i in enumerate(inputs):
                if idx > 0:
                    output.write(sep)
                output.write(i.process(self).encode(encoding))

    def pack(self, asset=None, force=False):
        """
        Packs one or all assets. By default, assets will only be packed if they have not
        been previously packed, or if any of the inputs to an asset have changed since
        the last time it was packed. To force packing, set force=True. To pack only a
        single asset, specify a path.
        """
        for name, inputs in self.iter_assets():
            if asset and asset != name:
                continue
            path = self.resolve(os.path.join(self.location, name))
            mtime = os.path.getmtime(path) if os.path.exists(path) else 0
            if force or mtime == 0 or self.modified(inputs, mtime):
                ext = os.path.splitext(name)[1].replace(".", "").lower()
                sep = self.concat.get(ext, "\n")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                logger.debug(
                    "Packing {} <<< {}".format(name, " | ".join(str(i) for i in inputs))
                )
                with open(path, "w", encoding="utf-8") as output:
                    for idx, i in enumerate(inputs):
                        if idx > 0:
                            output.write(sep)
                        output.write(i.process(self))

import os

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder, get_finders
from django.contrib.staticfiles.utils import matches_patterns
from django.core.checks import Warning
from django.core.files.storage import FileSystemStorage

from .base import DPack


class DjangoDPack(DPack):
    def __init__(self, config=None, **overrides):
        dpack_setting = getattr(settings, "DPACK", None)
        if config is None:
            config = dpack_setting if isinstance(dpack_setting, str) else None
        options = dpack_setting if isinstance(dpack_setting, dict) else {}
        options.update(overrides)
        if "output" not in options:
            options["output"] = settings.STATIC_ROOT
        if "prefix" not in options:
            options["prefix"] = settings.STATIC_URL
        base_dir = getattr(settings, "BASE_DIR", None)
        super().__init__(config, base_dir=base_dir, **options)

    def find_input(self, name):
        for finder in get_finders():
            if isinstance(finder, DPackFinder):
                continue
            found = finder.find(name)
            if found:
                return found
        # TODO: should this call through to super? maybe only if `search` is specified?
        return None


class DPackFinder(BaseFinder):
    def __init__(self, *args, **kwargs):
        self.packer = DjangoDPack()
        self.storage = FileSystemStorage(self.packer.storage_path)

    def check(self, **kwargs):
        errors = []
        if not self.packer.assets:
            errors.append(
                Warning(
                    "You have not specified any assets to pack.",
                    hint='Make sure you specify an "assets" dict in your dpack.yaml '
                    "or DPACK setting.",
                    id="dpack.W001",
                )
            )
        return errors

    def find(self, path, all=False):
        # Only pack the path being searched for, and only if it's out of date.
        if path in self.packer.assets:
            self.packer.pack(path)
            full_path = os.path.join(self.packer.location, path)
            return [full_path] if all else full_path
        return []

    def list(self, ignore_patterns):
        # This is called from collectstatic, pack everything up front.
        self.packer.pack(force=True)
        for asset in self.packer.assets:
            if matches_patterns(asset, ignore_patterns):
                continue
            yield asset, self.storage

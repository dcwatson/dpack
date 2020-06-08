import re

from setuptools import find_packages, setup

with open("README.md", "r") as readme:
    long_description = readme.read()

with open("dpack/__init__.py", "r") as src:
    version = re.match(r'.*__version__ = "(.*?)"', src.read(), re.S).group(1)

setup(
    name="dpack",
    version=version,
    description="Asset packager for Django.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Dan Watson",
    author_email="dcwatson@gmail.com",
    url="https://github.com/dcwatson/dpack",
    license="MIT",
    install_requires=["PyYAML"],
    packages=find_packages(),
    extras_require={
        "cssmin": ["rcssmin"],
        "jsmin": ["rjsmin"],
        "sass": ["libsass"],
        "all": ["rcssmin", "rjsmin", "libsass"],
    },
    entry_points={"console_scripts": ["dpack=dpack.cli:main"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)

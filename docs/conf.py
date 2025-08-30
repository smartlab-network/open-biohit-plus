# Configuration file for the Sphinx documentation builder.
from glob import glob
from os.path import dirname, join, relpath

import biohit_pipettor

project = "biohit-pipettor"
author = "Niklas Mertsch"
copyright = f"2022, {author}"
release = biohit_pipettor.__version__
language = "en"

exclude_patterns = ["_build"]

html_theme = "nature"
html_static_path = ["_static"]
static_dir = join(dirname(__file__), "_static")
html_css_files = [relpath(p, static_dir) for p in glob(join(static_dir, "css", "*.css"))]

pygments_style = "sphinx"  #

autoclass_content = "both"
autodoc_default_options = {
    "inherited-members": True,  # I don't know why, but this is required here
}
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]
autodoc_member_order = "groupwise"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

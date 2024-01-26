import os

from pycook.parser import parse_includes, parse_single_cook
from pycook.recipe import Recipe
from pycook.utils import _load_file


def parse(title: str, content: list[str]) -> Recipe:
    content = parse_includes(content)
    recipe = parse_single_cook(title, content)
    return recipe


def parse_file(filepath: str) -> Recipe:
    content = _load_file(filepath)
    title = os.path.basename(filepath).rsplit(".", 1)[0]
    recipe = parse(title, content)
    recipe.filepath = filepath
    return recipe

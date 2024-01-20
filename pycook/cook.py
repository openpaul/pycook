from pycook.parser import parse_includes, parse_single_cook
from pycook.recipe import Recipe


def parse(title: str, content: list[str]) -> Recipe:
    content = parse_includes(content)
    recipe = parse_single_cook(title, content)
    return recipe

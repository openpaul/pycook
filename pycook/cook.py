from typing import Optional

from pycook.parser import parse_includes, parse_single_cook
from pycook.recipe import Recipe

from .types import Metadata, RowType, Step, TextRow
from .utils import (get_line_type, group_steplines, parse_comments,
                    parse_cookware, parse_ingredients, parse_metadata,
                    parse_timer)



def parse(title: str, content: list[str]) -> Recipe:
    content = parse_includes(content)
    recipe = parse_single_cook(title, content)
    return recipe

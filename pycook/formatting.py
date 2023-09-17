from typing import Union

from pycook.types import Cookware, Ingredient


def item_table(items: list[Union[Ingredient, Cookware]]) -> str:
    rows = []
    if len(items) == 0:
        raise ValueError("No items to format")
    name_len = max([len(str(item.name)) for item in items])
    unit_len = max([len(str(item.unit)) for item in items])

    header_line = "-" * (unit_len) + " |" + "-" * (name_len)

    rows.append("| How much  | What |")
    rows.append(f"| {header_line} |")

    for item in items:
        unit_space = " " * (unit_len - len(str(item.unit)))
        name_space = " " * (name_len - len(str(item.name)))
        if item.unit is None:
            row = f"| | {item.name}{name_space} |"
        else:
            row = f"| **{str(item.unit)}**{unit_space} | {item.name}{name_space} |"
        rows.append(row)

    return "\n".join(rows)

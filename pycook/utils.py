import re
from .types import (
    Cookware,
    Ingredient,
    InlineComment,
    Metadata,
    Position,
    Timer,
    Units,
    Unit,
    RowType,
)
from typing import Union
from loguru import logger


def get_line_type(line: str) -> str:
    if is_comment_line(line):
        return RowType.comment
    elif is_metadata_line(line):
        return RowType.metadata
    else:
        return RowType.step


def is_comment_line(line: str) -> bool:
    return line.strip().startswith("-- ")


def is_metadata_line(line: str) -> bool:
    return line.strip().startswith(">> ")


def parse_metadata(line: str) -> dict[str, str]:
    if not is_metadata_line(line):
        raise ValueError(f"Line '{line}' is not a metadata line")
    line = line[3:].strip()
    key, value = line.split(":")
    return Metadata(key=key.strip(), value=value.strip())


def _load_file(filename: str) -> list[str]:
    with open(filename) as f:
        return [line.strip() for line in f.readlines]


def _divide_fraction(fraction: str) -> float:
    numerator, denominator = fraction.split("/")
    return float(numerator) / float(denominator)


def create_unit(unit_str: str, unit_value: Union[float, int] = 1.0) -> Unit:
    unit_str = unit_str.lower()
    if unit_str.endswith("s") and unit_str != "s":
        unit_str = unit_str[:-1]

    if unit_str in Units.__members__.keys():
        si = Units[unit_str]
    else:
        try:
            si = Units(unit_str)
        except ValueError:
            logger.error(
                f"Unit {unit_str} not found in Units. Valid units are '{Units.__members__.keys()}'"
            )
            raise ValueError(f"Unit {unit_str} not found in Units")

    return Unit(unit=si, amount=unit_value)


def parse_ingredients(cooklang_text: str) -> list[Ingredient]:
    return parse_stuff(cooklang_text, control_char="@")


def parse_cookware(cooklang_text: str) -> list[Cookware]:
    return parse_stuff(cooklang_text, control_char="#", T=Cookware)


def parse_timer(cooklang_text: str) -> list[Timer]:
    return parse_stuff(cooklang_text, control_char="~", T=Timer)


def parse_stuff(
    cooklang_text,
    control_char: int = "@",
    T: Union[Ingredient, Cookware, Timer] = Ingredient,
    rowcounter: int = 0,
) -> list[Union[Ingredient, Cookware, Timer]]:
    # Define the regex pattern to match @stuff {} and @stuff{1%kg} and @stuff @morestuff
    regex = (
        r"(?:"
        + control_char
        + r"((?:[\s+\w+])*)\s*\{((?:[\d\/.]+)?)%?((?:\w+))?\})|(?:"
        + control_char
        + r"(\w+))"
    )
    ingredients_list = []
    for match in re.finditer(regex, cooklang_text):
        groups = match.groups()
        position = Position(row=rowcounter, start=match.start(), length=match.end() - match.start())

        if groups[0] is None and groups[3]:
            ingredient = T(name=groups[3], unit=None, position=position)
        else:
            ingredient_name = groups[0]
            quantity = groups[1] if groups[1] else None
            unit = groups[2] if groups[2] else None
            # parse fractions
            if quantity is not None and "/" in quantity:
                quantity = _divide_fraction(quantity)
            elif quantity:
                quantity = float(quantity) if "." in quantity else int(quantity)

            if unit is not None:
                try:
                    parsed_unit = create_unit(unit, quantity)
                except ValueError:
                    logger.error(f"Could not parse unit '{unit}'")
                    raise ValueError(f"Could not parse unit '{unit}'")

                ingredient = T(
                    name=ingredient_name,
                    unit=parsed_unit,
                    position=position,
                )
            else:
                ingredient = T(name=ingredient_name, unit=quantity, position=position)

        ingredients_list.append(ingredient)

    return ingredients_list


def group_steplines(cooklang_text: list[str]) -> list[str]:
    steptext = []
    for line in cooklang_text:
        line = line.strip()
        if is_comment_line(line) or is_metadata_line(line):
            continue
        elif line != "":
            steptext.append(line)

        if line == "" and len(steptext) > 0:
            yield steptext
            steptext = []

    if len(steptext) > 0:
        yield steptext


def remove_control_chars(text: list[str]) -> list[str]:
    for s in text:
        for i, c in ["@", "#", "~"]:
            s = s.replace(c, "")


def parse_comments(cooklang_text: str, rowcounter: int = 0) -> list[str]:
    # Define the regex pattern to match @stuff {} and @stuff{1%kg} and @stuff @morestuff
    regex = r"\[\-\s([\w\d]*)\s\-\]"
    comments = []
    for match in re.finditer(regex, cooklang_text):
        groups = match.groups()
        position = Position(row=rowcounter, start=match.start(), length=match.end() - match.start())
        comments.append(InlineComment(text=groups[0], position=position))
    return comments

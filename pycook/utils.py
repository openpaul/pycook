import datetime
import os
import re
from typing import Generator, Union

import git
from loguru import logger

from .types import (
    Cookware,
    Ingredient,
    InlineComment,
    Metadata,
    Position,
    PositionEventEnum,
    RowType,
    Timer,
    Unit,
    Units,
)


def get_line_type(line: str) -> RowType:
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


def parse_metadata(line: str) -> Metadata:
    if not is_metadata_line(line):
        raise ValueError(f"Line '{line}' is not a metadata line")
    line = line[3:].strip()
    key, value = line.split(":")
    return Metadata(key=key.strip(), value=value.strip())


def _load_file(filename: str) -> list[str]:
    with open(filename) as f:
        return [line.strip() for line in f.readlines()]


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
    return [
        x
        for x in parse_stuff(cooklang_text, control_char=PositionEventEnum.Ingredient)
        if isinstance(x, Ingredient)
    ]


def parse_cookware(cooklang_text: str) -> list[Cookware]:
    return [
        x
        for x in parse_stuff(cooklang_text, control_char=PositionEventEnum.Cookware)
        if isinstance(x, Cookware)
    ]


def parse_timer(cooklang_text: str) -> list[Timer]:
    return [
        x
        for x in parse_stuff(cooklang_text, control_char=PositionEventEnum.Timer)
        if isinstance(x, Timer)
    ]


def parse_stuff(
    cooklang_text,
    control_char: PositionEventEnum,
    rowcounter: int = 0,
) -> list[Union[Ingredient, Timer, Cookware]]:
    # Define the regex pattern to match @stuff {} and @stuff{1%kg} and @stuff @morestuff
    regex = (
        r"(?:"
        + control_char.value
        + r"((?:[\s+\w+_()-])*)\s*\{((?:[\d\/.]+)?)%?((?:\w+))?\})|(?:"
        + control_char.value
        + r"(\w+))"
    )

    results = []
    match_object: Union[Ingredient, Cookware, Timer]
    for match in re.finditer(regex, cooklang_text):
        groups = match.groups()
        position = Position(
            row=rowcounter, start=match.start(), length=match.end() - match.start()
        )
        # We matched a open ended event aka @eggs ...
        if groups[0] is None and groups[3]:
            if control_char == PositionEventEnum.Ingredient:
                match_object = Ingredient(
                    name=groups[3].strip(), unit=None, position=position
                )
            elif control_char == PositionEventEnum.Timer:
                # This can not be a timer, so we ignore it. Maybe this is just a normal word
                continue
            elif control_char == PositionEventEnum.Cookware:
                match_object = Cookware(
                    name=groups[3].strip(), unit=None, position=position
                )
        else:
            # We matched something finished with {}
            name = groups[0].strip()
            quantity = groups[1].strip() if groups[1] else None
            unit = groups[2].strip() if groups[2] else None

            # parse fractions
            if isinstance(quantity, str) and "/" in quantity:
                quantity = _divide_fraction(quantity)
            elif isinstance(quantity, str):
                quantity = float(quantity) if "." in quantity else int(quantity)

            if unit is not None and quantity is not None:
                try:
                    parsed_unit = create_unit(unit, quantity)
                except ValueError:
                    logger.error(f"Could not parse unit '{unit}'")
                    raise ValueError(f"Could not parse unit '{unit}'")
            elif quantity is not None:
                parsed_unit = quantity
            else:
                parsed_unit = None

            if control_char == PositionEventEnum.Ingredient:
                match_object = Ingredient(
                    name=name, unit=parsed_unit, position=position
                )
            elif control_char == PositionEventEnum.Timer:
                match_object = Timer(name=name, unit=parsed_unit, position=position)
            elif control_char == PositionEventEnum.Cookware:
                match_object = Cookware(
                    name=name,
                    unit=quantity,
                    position=position,
                )
        results.append(match_object)

    return results


def group_steplines(cooklang_text: list[str]) -> Generator[list[str], None, None]:
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


def parse_comments(cooklang_text: str, rowcounter: int = 0) -> list[InlineComment]:
    # Define the regex pattern to match @stuff {} and @stuff{1%kg} and @stuff @morestuff
    regex = r"\[\-\s([\w\d]*)\s\-\]"
    comments = []
    for match in re.finditer(regex, cooklang_text):
        groups = match.groups()
        position = Position(
            row=rowcounter, start=match.start(), length=match.end() - match.start()
        )
        comments.append(InlineComment(text=groups[0], position=position))
    return comments


def find_files_in_folder(folder_path, file_extension=None):
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file_extension is None or file.endswith(file_extension):
                file_list.append(os.path.join(root, file))
    # sort the files alphabetically
    file_list.sort()

    return file_list


def replace_file_suffix(file_path: str, new_suffix: str) -> str:
    base_name = os.path.basename(file_path)
    name, current_extension = os.path.splitext(base_name)
    new_file_name = f"{name}{new_suffix}"

    return os.path.join(os.path.dirname(file_path), new_file_name)


def load_tex_assets() -> list[str]:
    # function loading tex header and footer files
    # list all files *tex in folder assets
    folder_path = os.path.dirname(__file__)
    all_tex_files = find_files_in_folder(os.path.join(folder_path, "assets"), ".tex")
    text_contens = []
    logger.debug(f"Found {len(all_tex_files)} tex files")
    for tex_file in all_tex_files:
        with open(tex_file) as f:
            text_contens.append(f.read())
    return text_contens


def find_git_parent_of_file(path: str) -> str:
    # function to determine parent git repo of a file
    # https://stackoverflow.com/questions/957928/is-there-a-way-to-get-the-git-root-directory-in-one-command
    return git.Repo(path, search_parent_directories=True).working_tree_dir


def find_git_path_of_file(path: str) -> str:
    # function to determine the path of a file in a git repo
    git_repo = os.path.abspath(find_git_parent_of_file(path))
    path = os.path.abspath(path)
    return path[len(git_repo) + 1 :]


def git_get_last_change(git_location: str, filepath: str) -> datetime.datetime:
    # function to get the last change of a file in a git repo
    git_location = find_git_parent_of_file(git_location)
    filepath = find_git_path_of_file(filepath)

    repo = git.Repo(git_location)
    file_log = repo.git.log(filepath, max_count=1, date="short")
    if not file_log:
        logger.warning(f"File {filepath} not found in git repo")
        return datetime.datetime.now()
    else:
        date = file_log.splitlines()[2].split("Date:")[1].strip()
        return datetime.datetime.strptime(date, "%Y-%m-%d")

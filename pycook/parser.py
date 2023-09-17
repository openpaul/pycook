

import os
from loguru import logger
from pycook.recipe import Recipe
from pycook.types import RowType, Step, TextRow
from pycook.utils import _load_file, get_line_type, group_steplines, parse_comments, parse_cookware, parse_ingredients, parse_metadata, parse_timer


def parse_single_cook(title: str, content: list[str]) -> Recipe:
    allsteplines: list[str] = []
    metadata = []
    for line in content:
        line_type = get_line_type(line)
        if line_type == RowType.metadata:
            metadata.append(parse_metadata(line))
            pass
        elif line_type == RowType.comment:
            pass
        elif line_type == RowType.step:
            allsteplines.append(line)

    # now group the steps and parse them
    all_steps: list[Step] = []
    for stepid, steplines in enumerate(group_steplines(allsteplines)):
        steprows = []
        for rowid, row in enumerate(steplines):
            r = TextRow(
                id=rowid,
                text=row,
                type=get_line_type(row),
                ingredients=parse_ingredients(row),
                cookware=parse_cookware(row),
                timers=parse_timer(row),
                comments=parse_comments(row),
            )
            steprows.append(r)
        all_steps.append(Step(id=stepid, rows=steprows))
    return Recipe(title=title, metadata=metadata, steps=all_steps)



def parse_includes(lines: list[str]) -> list[str]:
    """
    This is an extension to the cook format.
    Comment lines that start with -- include:
    are considered like latex includes and should be parsed first.

    This means, we parse it as a recipe BUT add a level to each headline. Meaning each ^# will become ^##
    """
    return_lines = []
    for line in lines:
        if line.startswith("-- include:"):
            include_path = None
            try:
                _, include_path = line.split(":", 1)
                include_path = include_path.strip()
            except Exception:
                logger.error("Could not find include path")
                continue

            if include_path and os.path.exists(include_path):
                if not include_path.endswith(".cook"):
                    # we just open and append
                    return_lines.extend(_load_file(include_path))
                else:
                    # we parse it
                    try:
                        title = os.path.basename(include_path).replace(".cook", "")
                        recipe = parse_single_cook(title, _load_file(include_path))
                        return_lines.extend(reduce_headers(str(recipe)))
                    except Exception:
                        logger.error(f"Could not parse include {include_path}")
            else:
                logger.error(f"Include file {include_path} does not exist?")
        else:
            return_lines.append(line)
    return return_lines


def reduce_headers(content: str, prefix: str="#")-> list[str]:
    result = []
    for line in content.split("\n"):
        if line.startswith("#"):
            line = f"{prefix}{line}"
        result.append(line)
    return result
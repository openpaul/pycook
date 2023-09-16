from typing import Optional

from .types import Metadata, RowType, Step, TextRow
from .utils import (get_line_type, group_steplines, parse_comments,
                    parse_cookware, parse_ingredients, parse_metadata,
                    parse_timer)


class Recipe:
    def __init__(self, title: str, metadata: list[Metadata], steps: list[Step]):
        self.title = title
        if self.title.endswith(".cook"):
            self.title = self.title[:-5]

        self.metadata = metadata
        self.steps = steps

    def _load(self, filepath: str):
        pass

    def _find_picture(
        self,
        filepath: Optional[str] = None,
        suffixes: list[str] = ["jpg", "png", "jpeg", "webp"],
    ):
        if filepath is None:
            pass
        pass

    def _ingredients(self):
        return [
            ingredient
            for step in self.steps
            for row in step.rows
            for ingredient in row.ingredients
        ]

    def _cookware(self):
        return [
            cookware
            for step in self.steps
            for row in step.rows
            for cookware in row.cookware
        ]

    def __str__(self):
        steps = "\n\n".join([str(step) for step in self.steps])
        ingredients = "\n".join(["- " + str(x) for x in self._ingredients()])
        cookware = "\n".join(["- " + str(x) for x in self._cookware()])
        s = f"""# {self.title}
## :salt: Ingredients
{ingredients}
##  :cooking: Cookware
{cookware}
## :pencil: Instructions
{steps}
"""
        return s


def parse(title: str, content: list[str]) -> Recipe:
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

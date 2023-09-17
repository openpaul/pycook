
from typing import Optional

from pycook.types import Metadata, Step


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
    
    def _metadata(self):
        lines = ["---"]
        lines.append(f"title: {self.title}")
        for metadata in self.metadata:
            lines.append(str(metadata))
        lines.append("---")
        return lines

    def __str__(self):
        steps = "\n\n".join([str(step) for step in self.steps])
        ingredients = "\n".join(["- " + str(x) for x in self._ingredients()])
        cookware = "\n".join(["- " + str(x) for x in self._cookware()])
        metadata = "\n".join(self._metadata())
        s = f"""{metadata}\n
# {self.title}\n
{'## :salt: Ingredients' if len(ingredients) > 0 else ''}
{ingredients}
{'##  :cooking: Cookware' if len(cookware) > 0 else ''}
{cookware}
{'## :pencil: Instructions' if len(steps) > 0 else ''}
{steps}
"""
        return s
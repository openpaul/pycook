import os
from typing import Optional

from pycook.formatting import item_table
from pycook.types import Metadata, Step


class Recipe:
    def __init__(
        self,
        title: str,
        metadata: list[Metadata],
        steps: list[Step],
        filepath: Optional[str] = None,
    ):
        self.title = title
        if self.title.endswith(".cook"):
            self.title = self.title[:-5]

        self.metadata = metadata
        self.steps = steps
        self.filepath = filepath
        self.image = None

    def _load(self, filepath: str):
        pass

    def _find_picture(
        self,
        filepath: Optional[str] = None,
        suffixes: list[str] = ["webp", "jpg", "png", "jpeg"],
    ):
        if filepath is None and self.filepath is not None:
            filepath = self.filepath
        else:
            return
        basepath = filepath.rsplit(".", 1)[0]
        for suffix in suffixes:
            test_path = f"{basepath}.{suffix}"
            if os.path.exists(test_path):
                self.image = test_path
                break

    def _ingredients(self) -> str:
        ingredients = [
            ingredient
            for step in self.steps
            for row in step.rows
            for ingredient in row.ingredients
        ]
        return item_table(ingredients)

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
        image = f"![{self.title}]({self.image}){{ loading=lazy }}"

        if len(self.steps) == 0:
            return f"# {self.title}\n{image if self.image is not None else ''}\n"

        ingredients = self._ingredients()
        cookware = "\n".join(["- " + str(x) for x in self._cookware()])
        _metadata = "\n".join(self._metadata())
        s = f"""
# {self.title}\n
{image if self.image is not None else ''}
{'## :salt: Ingredients' if len(ingredients) > 0 else ''}
{ingredients}\n
{'##  :cooking: Cookware' if len(cookware) > 0 else ''}
{cookware}\n
{'## :pencil: Instructions' if len(steps) > 0 else ''}
{steps}
"""
        return s

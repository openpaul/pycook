import os
import re
from typing import Optional

import markdown
from mdx_latex import LaTeXExtension

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

    def to_tex(self):
        return TexRecipe(
            title=self.title,
            metadata=self.metadata,
            steps=self.steps,
            filepath=self.filepath,
        )


class TexRecipe(Recipe):
    def step_to_tex(self, step: Step):
        # \ingredient[250]{g}{eggs}
        ingredients = []
        for row in step.rows:
            for ingredient in row.ingredients:
                ingredients.append(ingredient.to_tex())
        ingredients = "\n".join(ingredients)

        # make text nice
        # step_text = self._replace_chars(str(step))
        # step_text = self._replace_md_headers(step_text)

        step_text = markdown.markdown(str(step), extensions=[LaTeXExtension()])

        if len(ingredients) > 0:
            # now we only need the step as text:
            return f"""\n{ingredients}\n{step_text}\n\n"""
        else:
            return f"""\n\\freeform\n{step_text}\n\n"""

    def __str__(self):
        # lets add a title
        title = "\\begin{recipe}{" + self.title + "}{}{}"

        text = [self.step_to_tex(step) for step in self.steps]

        closing = "\\end{recipe}"

        return "\n".join([title] + text + [closing])

    @staticmethod
    def _replace_chars(text: str) -> str:
        # replace certain strings with the tex version
        replaceme = {"&deg;": "$^{\circ}$"}
        for key, value in replaceme.items():
            text = text.replace(key, value)
        return text

    @staticmethod
    def _replace_md_headers(text: str) -> str:
        # replace # with \section*{#}
        new_lines = []
        header_regex = r"^#{1,6}\s(.+)"
        for line in text.split("\n"):
            if re.match(header_regex, line):
                # we have a header
                header = re.match(header_regex, line).groups()[0]
                new_lines.append(f"\\section*{{{header.strip()}}}")
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

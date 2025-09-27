"""
Cooklang parser for recipe markup language.

This module provides a comprehensive parser for the Cooklang recipe markup language,
which allows writing recipes in a structured text format with ingredients, cookware,
timers, and cooking instructions.

The parser converts Cooklang markup into structured Python objects and can export
to various formats including Markdown, HTML, and plain text.

Main Components:
    CooklangParser: Primary parser class for converting text to Recipe objects
    Recipe: Complete recipe representation with ingredients, steps, and metadata
    Step: Individual cooking step with tokens for different recipe elements
    Token classes: Specialized tokens for ingredients, cookware, timers, etc.
    Data classes: Ingredient, Cookware, Timer for structured recipe data

Examples:
    >>> parser = CooklangParser()
    >>> recipe_text = '''
    ... ---
    ... title: Simple Pasta
    ... ---
    ...
    ... Boil @water{1%L} in a #pot{}.
    ... Add @pasta{200%g} and cook for ~{10%min}.
    ... '''
    >>> recipe = parser.parse(recipe_text)
    >>> recipe.title
    'Simple Pasta'
    >>> len(recipe.ingredients)
    2
    >>> recipe.ingredients[0].name
    'water'
    >>> recipe.to_markdown()  # doctest: +SKIP
    '# Simple Pasta\\n\\n## Ingredients...'

    Reading from file:
    >>> from pathlib import Path
    >>> recipe = read_cook("recipe.cook")  # doctest: +SKIP
    >>> print(recipe.title)  # doctest: +SKIP
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml


@dataclass
class Ingredient:
    """Represents a recipe ingredient with optional quantity, unit, and preparation.

    This class encapsulates all information about a recipe ingredient including
    its name, amount, measurement unit, and any preparation instructions.

    Attributes:
        name: The ingredient name (e.g., "flour", "chicken breast")
        quantity: Amount of ingredient (int, float, or string like "1/2")
        unit: Unit of measurement (e.g., "g", "cups", "tbsp")
        preparation: Preparation method (e.g., "diced", "chopped", "room temperature")

    Examples:
        >>> ingredient = Ingredient("flour", 200, "g")
        >>> str(ingredient)
        '200 g flour'

        >>> ingredient = Ingredient("onion", 1, preparation="diced")
        >>> str(ingredient)
        '1 onion (diced)'

        >>> ingredient = Ingredient("salt")
        >>> str(ingredient)
        'salt'
    """

    name: str
    quantity: Optional[Union[int, float, str]] = None
    unit: Optional[str] = None
    preparation: Optional[str] = None

    def __str__(self) -> str:
        result = self.name
        if self.quantity:
            result = f"{self.quantity} {self.unit or ''} {result}".strip()
        if self.preparation:
            result += f" ({self.preparation})"
        result = result.replace("  ", " ")
        return result

    def to_latex(self):
        """
        Convert to LaTeX ingredient format.
        """

        return f"\\ingredient[{self.quantity}]{{{self.unit or ''}}}{{{self.name}}}"


@dataclass
class Cookware:
    """Represents cookware or equipment needed for the recipe.

    This class encapsulates information about cooking equipment including
    the item name and optional quantity.

    Attributes:
        name: The cookware name (e.g., "pot", "mixing bowl", "baking sheet")
        quantity: Number of items needed (e.g., 2, "large")

    Examples:
        >>> cookware = Cookware("pot")
        >>> str(cookware)
        'pot'

        >>> cookware = Cookware("mixing bowl", 2)
        >>> str(cookware)
        '2 mixing bowl'
    """

    name: str
    quantity: Optional[Union[int, str]] = None

    def __str__(self) -> str:
        if self.quantity:
            return f"{self.quantity} {self.name}"
        return self.name


@dataclass
class Timer:
    """Represents a cooking timer with duration and optional name.

    This class encapsulates timing information for cooking steps including
    duration, time unit, and optional descriptive name.

    Attributes:
        name: Optional timer description (e.g., "pasta cooking", "rest time")
        duration: Time duration (int, float, or string like "1.5")
        unit: Time unit (e.g., "min", "hours", "sec")

    Examples:
        >>> timer = Timer(duration=10, unit="min")
        >>> str(timer)
        '10 min'

        >>> timer = Timer(name="baking", duration=25, unit="min")
        >>> str(timer)
        '25 min'

        >>> timer = Timer()
        >>> str(timer)
        ''
    """

    name: Optional[str] = None
    duration: Optional[Union[int, float, str]] = None
    unit: Optional[str] = None

    def __str__(self) -> str:
        if self.duration:
            return f"{self.duration} {self.unit or ''}".strip()
        return ""


@dataclass
class Comment:
    """Represents a comment in the recipe.

    Comments provide additional context or notes that don't appear in the
    final recipe output. They can be inline (--) or block ([-...-]) format.

    Attributes:
        text: The comment content
        is_block: True for block comments ([-...-]), False for inline (--)

    Examples:
        >>> comment = Comment("This is a note", is_block=False)
        >>> comment.text
        'This is a note'

        >>> block_comment = Comment("Long explanation\\nwith multiple lines", is_block=True)
        >>> block_comment.is_block
        True
    """

    text: str
    is_block: bool = False


@dataclass
class Note:
    """Represents a recipe note (lines starting with >).

    Notes are special annotations that appear as blockquotes in formatted output,
    typically used for tips, warnings, or additional information.

    Attributes:
        text: The note content without the > prefix

    Examples:
        >>> note = Note("Preheat oven to 350°F before starting")
        >>> note.text
        'Preheat oven to 350°F before starting'
    """

    text: str


@dataclass
class Section:
    """Represents a recipe section header (lines with == markers).

    Sections organize recipes into logical groups with hierarchical levels
    based on the number of equals signs used.

    Attributes:
        title: The section title text
        level: Nesting level (1 for =, 2 for ==, etc.)

    Examples:
        >>> section = Section("Preparation", level=1)
        >>> section.title
        'Preparation'

        >>> subsection = Section("Making the dough", level=2)
        >>> subsection.level
        2
    """

    title: str
    level: int = 1


# Token-based approach to maintain position and context
@dataclass
class Token:
    text: str
    start_pos: int
    end_pos: int

    def to_markdown(self) -> str:
        """Convert to Markdown format.

        Returns:
            Markdown representation of the token.
        """
        return self.text

    def to_plain_text(self) -> str:
        """Convert to plain text format.

        Returns:
            Plain text representation without markup.
        """
        return self.text

    def to_html(self) -> str:
        """Convert to HTML format.

        Returns:
            HTML representation of the token.
        """
        return self.text

    def to_latex(self) -> str:
        """Convert to LaTeX format.

        Returns:
            LaTeX representation of the token.
        """
        return self.text


@dataclass
class TextToken(Token):
    """Plain text token containing regular recipe instruction text.

    TextTokens represent portions of recipe text that don't contain
    special Cooklang markup (ingredients, cookware, timers, etc.).

    Examples:
        >>> token = TextToken("Heat oil in a", 0, 13)
        >>> token.to_plain_text()
        'Heat oil in a'
    """

    pass


@dataclass
class IngredientToken(Token):
    """Ingredient token that maintains original markup and parsed data.

    This token represents ingredient references in recipe text, preserving
    both the original Cooklang markup and the parsed ingredient information.

    Attributes:
        ingredient: Parsed Ingredient object with name, quantity, unit, etc.

    Examples:
        >>> ingredient = Ingredient("flour", 200, "g")
        >>> token = IngredientToken("@flour{200%g}", 0, 12, ingredient)
        >>> token.to_markdown()
        '**200 g flour**'
        >>> token.to_plain_text()
        '200 g flour'
    """

    ingredient: Ingredient

    def to_markdown(self) -> str:
        result = f"**{self.ingredient.name}**"
        if self.ingredient.quantity:
            result = f"**{self.ingredient.quantity} {self.ingredient.unit or ''} {self.ingredient.name}**".strip()
        if self.ingredient.preparation:
            result += f" *({self.ingredient.preparation})*"
        result = result.replace("  ", " ")
        return result

    def to_plain_text(self) -> str:
        return str(self.ingredient)

    def to_html(self) -> str:
        result = f"<strong>{self.ingredient.name}</strong>"
        if self.ingredient.quantity:
            result = f"<strong>{self.ingredient.quantity} {self.ingredient.unit or ''} {self.ingredient.name}</strong>".strip()
        if self.ingredient.preparation:
            result += f" <em>({self.ingredient.preparation})</em>"
        return result

    def to_latex(self) -> str:
        # \textbf{150 g water}
        text = f"{self.ingredient.name}"
        if self.ingredient.quantity:
            text += f" {self.ingredient.quantity} {self.ingredient.unit or ''}"
            text = text.strip()
        return "\\textbf{" + text + "}"


@dataclass
class CookwareToken(Token):
    """Cookware token that maintains original markup and parsed data.

    This token represents cookware references in recipe text, preserving
    both the original Cooklang markup and the parsed cookware information.

    Attributes:
        cookware: Parsed Cookware object with name and optional quantity.

    Examples:
        >>> cookware = Cookware("pot", 1)
        >>> token = CookwareToken("#pot{}", 0, 6, cookware)
        >>> token.to_markdown()
        '*pot*'
        >>> token.to_html()
        '<em>1 pot</em>'
    """

    cookware: Cookware

    def to_markdown(self) -> str:
        return f"*{self.cookware.name}*"

    def to_plain_text(self) -> str:
        return str(self.cookware)

    def to_html(self) -> str:
        if self.cookware.quantity:
            return f"<em>{self.cookware.quantity} {self.cookware.name}</em>"
        return f"<em>{self.cookware.name}</em>"

    def to_latex(self) -> str:
        if self.cookware.quantity:
            return f"\\textit{{{self.cookware.quantity} {self.cookware.name}}}"
        return f"\\textit{{{self.cookware.name}}}"


@dataclass
class TimerToken(Token):
    """Timer token that maintains original markup and parsed data.

    This token represents timer references in recipe text, preserving
    both the original Cooklang markup and the parsed timer information.

    Attributes:
        timer: Parsed Timer object with duration, unit, and optional name.

    Examples:
        >>> timer = Timer(duration=10, unit="min")
        >>> token = TimerToken("~{10%min}", 0, 9, timer)
        >>> token.to_markdown()
        '**10 min**'
        >>> token.to_plain_text()
        '10 min'
    """

    timer: Timer

    def to_markdown(self) -> str:
        return f"**{self.timer}**"

    def to_plain_text(self) -> str:
        return str(self.timer)

    def to_html(self) -> str:
        return f"<em>{self.timer}</em>" if str(self.timer) else ""

    def to_latex(self) -> str:
        return f"\\textbf{{{self.timer.duration} {self.timer.unit or ''}}}".strip()


@dataclass
class CommentToken(Token):
    """Comment token that maintains original markup and parsed data.

    This token represents comment text in recipes, which can be either
    inline (--) or block ([-...-]) format.

    Attributes:
        comment: Parsed Comment object with text and block flag.

    Examples:
        >>> comment = Comment("This is a tip", is_block=False)
        >>> token = CommentToken("-- This is a tip", 0, 16, comment)
        >>> token.to_markdown()
        '*(This is a tip)*'
        >>> token.to_plain_text()
        ''
    """

    comment: Comment

    def to_markdown(self) -> str:
        if self.comment.is_block:
            return f"<!-- {self.comment.text} -->"
        return f"*({self.comment.text})*"

    def to_plain_text(self) -> str:
        return ""  # Comments don't appear in plain text

    def to_html(self) -> str:
        if self.comment.is_block:
            return f"<!-- {self.comment.text} -->"
        return f"<em>({self.comment.text})</em>"

    def to_latex(self) -> str:
        if self.comment.is_block:
            text = self.comment.text.replace("\n", " ")
            return f"% {text}"
        return f"\\textit{{({self.comment.text})}}"


@dataclass
class NoteToken(Token):
    """Note token that maintains original markup and parsed data.

    This token represents note text (lines starting with >) which appear
    as blockquotes in formatted output.

    Attributes:
        note: Parsed Note object containing the note text.

    Examples:
        >>> note = Note("Preheat oven first")
        >>> token = NoteToken("> Preheat oven first", 0, 19, note)
        >>> token.to_markdown()
        '> Preheat oven first'
        >>> token.to_html()
        '<blockquote>Preheat oven first</blockquote>'
    """

    note: Note

    def to_markdown(self) -> str:
        return f"> {self.note.text}"

    def to_plain_text(self) -> str:
        return self.note.text

    def to_html(self) -> str:
        return f"<blockquote>{self.note.text}</blockquote>"

    def to_latex(self) -> str:
        return f"\\begin{{quote}}\n{self.note.text}\n\\end{{quote}}"


@dataclass
class Step:
    """Represents a cooking step as a sequence of tokens.

    A Step contains the parsed tokens that make up a single recipe instruction,
    preserving the original text structure while providing access to structured
    data like ingredients, cookware, and timers.

    Attributes:
        tokens: List of Token objects that make up this step
        section: Optional Section this step belongs to

    Examples:
        >>> tokens = [
        ...     TextToken("Heat ", 0, 5),
        ...     IngredientToken("@oil{2%tbsp}", 5, 16, Ingredient("oil", 2, "tbsp")),
        ...     TextToken(" in a ", 16, 22),
        ...     CookwareToken("#pan{}", 22, 28, Cookware("pan"))
        ... ]
        >>> step = Step(tokens)  # doctest: +SKIP
        >>> step.text  # doctest: +SKIP
        'Heat @oil{2%tbsp} in a #pan{}'
        >>> len(step.ingredients)  # doctest: +SKIP
        1
    """

    tokens: List[Token] = field(default_factory=list)
    section: Optional[Section] = None

    @property
    def text(self) -> str:
        """Get the original text by joining all token texts.

        Returns:
            Complete original text of the step.
        """
        return "".join(token.text for token in self.tokens)

    @property
    def ingredients(self) -> List[Ingredient]:
        """Get all ingredients referenced in this step.

        Returns:
            List of Ingredient objects found in this step's tokens.
        """
        return [
            token.ingredient
            for token in self.tokens
            if isinstance(token, IngredientToken)
        ]

    @property
    def cookware(self) -> List[Cookware]:
        """Get all cookware referenced in this step.

        Returns:
            List of Cookware objects found in this step's tokens.
        """
        return [
            token.cookware for token in self.tokens if isinstance(token, CookwareToken)
        ]

    @property
    def timers(self) -> List[Timer]:
        """Get all timers referenced in this step.

        Returns:
            List of Timer objects found in this step's tokens.
        """
        return [token.timer for token in self.tokens if isinstance(token, TimerToken)]

    @property
    def comments(self) -> List[Comment]:
        """Get all comments in this step.

        Returns:
            List of Comment objects found in this step's tokens.
        """
        return [
            token.comment for token in self.tokens if isinstance(token, CommentToken)
        ]

    def to_markdown(self) -> str:
        """Convert to Markdown format.

        Returns:
            Step as Markdown text with formatting.
        """
        return "".join(token.to_markdown() for token in self.tokens)

    def to_plain_text(self) -> str:
        """Convert to plain text format.

        Returns:
            Step as plain text without markup.
        """
        return "".join(token.to_plain_text() for token in self.tokens)

    def to_html(self) -> str:
        """Convert to HTML format.

        Returns:
            Step as HTML text.
        """
        return "".join(token.to_html() for token in self.tokens)

    def to_latex(self) -> str:
        """Convert to LaTeX format.

        Returns:
            Step as LaTeX text.
        """
        text = []
        for ingredient in self.ingredients:
            text.append(ingredient.to_latex())
            text.append("\n")
        for token in self.tokens:
            text.append(token.to_latex())

        return "".join(text) + "\n\n"

    @property
    def is_comment(self) -> bool:
        """Check if this step is a comment.

        Returns:
            True if the step consists only of comment tokens.
        """
        return all(isinstance(token, CommentToken) for token in self.tokens)


@dataclass
class RecipeSettings:
    """
    Settings that affect recipe parsing and rendering.
    The defaults are chosen to align with the Cooklang specification.
    But can be overridden for specific recipes or use cases.
    """

    ignore_section_depth: bool = True


@dataclass
class Recipe:
    """Complete parsed recipe with all components and metadata.

    The Recipe class represents a fully parsed Cooklang recipe including
    title, metadata, cooking steps, and organizational sections. It provides
    methods for extracting ingredients and cookware lists, and converting
    to various output formats.

    It is the class returned by the parser.

    Attributes:
        title: Recipe title (from metadata or inferred from filename)
        metadata: Dictionary of recipe metadata from YAML front matter
        steps: List of Step objects containing the recipe instructions
        sections: List of Section objects for recipe organization

    Examples:
        >>> recipe = Recipe(title="Simple Pasta")
        >>> recipe.title
        'Simple Pasta'
    """

    title: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    settings: RecipeSettings = field(default_factory=RecipeSettings)

    @property
    def ingredients(self) -> List[Ingredient]:
        """Get all unique ingredients from all recipe steps.

        Collects ingredients from all steps and removes duplicates while
        preserving order of first occurrence.

        Returns:
            List of unique Ingredient objects used in the recipe.
        """
        all_ingredients = []
        for step in self.steps:
            all_ingredients.extend(step.ingredients)
        return self._deduplicate_ingredients(all_ingredients)

    @property
    def cookware(self) -> List[Cookware]:
        """Get all unique cookware from all recipe steps.

        Collects cookware from all steps and removes duplicates while
        preserving order of first occurrence.

        Returns:
            List of unique Cookware objects used in the recipe.
        """
        all_cookware = []
        for step in self.steps:
            all_cookware.extend(step.cookware)
        return self._deduplicate_cookware(all_cookware)

    @property
    def timers(self) -> List[Timer]:
        """Get all unique timers from all recipe steps.

        Collects timers from all steps and removes duplicates while
        preserving order of first occurrence.

        Returns:
            List of unique Timer objects used in the recipe.
        """
        all_timers = []
        for step in self.steps:
            all_timers.extend(step.timers)
        return self._deduplicate_timers(all_timers)

    def __len__(self) -> int:
        """Get the number of steps in the recipe.

        Returns:
            Number of Step objects in the recipe.
        """
        return len([step for step in self.steps if not step.is_comment])

    def __bool__(self) -> bool:
        if (
            self.steps
            or self.metadata
            or self.ingredients
            or self.cookware
            or self.sections
            or self.title
        ):
            return True
        return False

    def to_markdown(
        self,
        include_ingredients: bool = True,
        include_cookware: bool = True,
        include_instructions: bool = True,
    ) -> str:
        """Convert recipe to Markdown format.

        Creates a formatted Markdown document with title, ingredients list,
        equipment list, and step-by-step instructions with proper formatting.

        Args:
            include_ingredients: Whether to include ingredients section
            include_cookware: Whether to include equipment section
            include_instructions: Whether to include instructions section

        Returns:
            Complete recipe as Markdown text.
        """
        result = []

        # Add title
        if self.title:
            result.append(f"# {self.title}")
            result.append("")

        # Add ingredients
        if self.ingredients and include_ingredients:
            result.append("## Ingredients")
            result.append("")
            for ingredient in self.ingredients:
                result.append(f"- {ingredient}")
            result.append("")

        # Add cookware
        if self.cookware and include_cookware:
            result.append("## Equipment")
            result.append("")
            for cookware in self.cookware:
                result.append(f"- {cookware}")
            result.append("")

        if self.sections or (self.steps and include_instructions):
            result.append("## Instructions")
            result.append("")
        if self.steps and include_instructions:
            current_section = None
            current_section_index = -1
            for step in self.steps:
                if step.section and step.section != current_section:
                    # what if we have multiple sections with no steps
                    while (
                        current_section != step.section
                        and current_section_index + 1 < len(self.sections)
                    ):
                        current_section_index += 1
                        current_section = self.sections[current_section_index]
                        section_level = (
                            min(current_section.level + 2, 6)
                            if not self.settings.ignore_section_depth
                            else 3
                        )
                        result.append(f"{'#' * section_level} {current_section.title}")
                        result.append("")

                md = step.to_markdown().strip()
                if md:
                    result.append(md)
                    result.append("")
            # add any remaining sections with no steps
            while current_section_index + 1 < len(self.sections):
                current_section_index += 1
                current_section = self.sections[current_section_index]
                section_level = (
                    min(current_section.level + 2, 6)
                    if not self.settings.ignore_section_depth
                    else 3
                )
                result.append(f"{'#' * section_level} {current_section.title}")
                result.append("")

        return "\n".join(result).strip()

    def to_latex(self) -> str:
        """Convert recipe to LaTeX recipe format."""
        results = []
        title = "\n\\begin{recipe}{" + (self.title or "Recipe") + "}{}\n\n"
        closing = "\\end{recipe}\n\\cleardoublepage\n\n"

        results.append(title)
        current_section = None
        current_section_index = -1
        section_level_latex = {
            1: "section",
            2: "subsection",
            3: "subsubsection",
        }
        for step in self.steps:
            if step.section and step.section != current_section:
                print(step.section, current_section)
                # what if we have multiple sections with no steps
                while (
                    current_section != step.section
                    and current_section_index + 1 < len(self.sections)
                ):
                    current_section_index += 1
                    current_section = self.sections[current_section_index]
                    section_level = (
                        min(current_section.level, 3)
                        if not self.settings.ignore_section_depth
                        else 1
                    )
                    results.append(
                        f"\\{section_level_latex[section_level]}{{{current_section.title}}}\n"
                    )
            results.append(step.to_latex())

        while current_section_index + 1 < len(self.sections):
            current_section_index += 1
            current_section = self.sections[current_section_index]
            section_level = (
                min(current_section.level, 3)
                if not self.settings.ignore_section_depth
                else 1
            )
            results.append(
                f"\\{section_level_latex[section_level]}{{{current_section.title}}}\n"
            )

        results.append(closing)
        return "".join(results)

    def to_html(self, image_path: Path | None = None) -> str:
        """Convert recipe to HTML format.

        Creates a formatted HTML document with title, optional image,
        ingredients list, equipment list, and instructions.

        Args:
            image_path: Optional path to recipe image to include

        Returns:
            Complete recipe as HTML text.
        """
        results = []

        # Add title
        if self.title:
            results.append(f"<h1>{self.title}</h1>")

        if self.metadata.get("image") or image_path:
            results.append(
                f'<img src="{self.metadata["image"] if not image_path else image_path}" alt="Recipe Image for {self.title or "Recipe"}"/>'
            )

        # Add Ingredients
        if self.ingredients:
            results.append("<h2>Ingredients</h2>")
            results.append("<ul>")
            for ingredient in self.ingredients:
                results.append(f"<li>{ingredient}</li>")
            results.append("</ul>")
        # Add Cookware
        if self.cookware:
            results.append("<h2>Equipment</h2>")
            results.append("<ul>")
            for cookware in self.cookware:
                results.append(f"<li>{cookware}</li>")
            results.append("</ul>")
        # Sections with no steps need to be shown
        current_section = None
        current_section_index = -1
        if self.sections or self.steps:
            results.append("<h2>Instructions</h2>")
        # Add Instructions
        if self.steps:
            for step in self.steps:
                if step.section and step.section != current_section:
                    # what if we have multiple sections with no steps
                    while (
                        current_section != step.section
                        and current_section_index + 1 < len(self.sections)
                    ):
                        current_section_index += 1
                        current_section = self.sections[current_section_index]
                        section_level = (
                            min(current_section.level + 2, 6)
                            if not self.settings.ignore_section_depth
                            else 3
                        )
                        results.append(
                            f"<h{section_level}>{current_section.title}</h{section_level}>"
                        )

                results.append(f"<p>{step.to_html()}</p>")
        # add any remaining sections with no steps
        while current_section_index + 1 < len(self.sections):
            current_section_index += 1
            current_section = self.sections[current_section_index]
            section_level = (
                min(current_section.level + 2, 6)
                if not self.settings.ignore_section_depth
                else 3
            )
            results.append(
                f"<h{section_level}>{current_section.title}</h{section_level}>"
            )
        return "\n".join(results).strip()

    def to_text(self) -> str:
        """Convert recipe to plain text format.

        Creates a simple text version with title and step instructions
        without any markup or formatting.

        Returns:
            Recipe as plain text.
        """
        results = []
        if self.title:
            results.append(self.title)
            results.append("")

        for step in self.steps:
            results.append(step.to_plain_text())
            results.append("")

        return "\n".join(results).strip()

    def _deduplicate_ingredients(
        self, ingredients: List[Ingredient]
    ) -> List[Ingredient]:
        """Remove duplicate ingredients while preserving order.

        Args:
            ingredients: List of ingredients potentially containing duplicates

        Returns:
            List with duplicate ingredients removed, preserving first occurrence.
        """
        seen = set()
        result = []
        for ingredient in ingredients:
            key = (
                ingredient.name,
                ingredient.unit,
                ingredient.preparation,
                ingredient.quantity,
            )
            if key not in seen:
                seen.add(key)
                result.append(ingredient)
        return result

    def _deduplicate_cookware(self, cookware: List[Cookware]) -> List[Cookware]:
        """Remove duplicate cookware while preserving order.

        Args:
            cookware: List of cookware potentially containing duplicates

        Returns:
            List with duplicate cookware removed, preserving first occurrence.
        """
        seen = set()
        result = []
        for item in cookware:
            if item.name not in seen:
                seen.add(item.name)
                result.append(item)
        return result

    def _deduplicate_timers(self, timers: List[Timer]) -> List[Timer]:
        """Remove duplicate timers while preserving order.

        Args:
            timers: List of timers potentially containing duplicates

        Returns:
            List with duplicate timers removed, preserving first occurrence.
        """
        seen = set()
        result = []
        for timer in timers:
            key = (timer.name, timer.duration, timer.unit)
            if key not in seen:
                seen.add(key)
                result.append(timer)
        return result


def _parse_number(value: str, fractions: bool = False) -> Union[int, float, str]:
    """Parse a string value into a number, handling fractions if enabled.

    Attempts to convert string values to appropriate numeric types (int or float).
    Can optionally handle fraction notation like "1/2".

    Args:
        value: String value to parse (e.g., "10", "1.5", "1/2")
        fractions: Whether to parse fractional values like "1/2"

    Returns:
        Parsed number as int, float, or original string if parsing fails.

    Examples:
        >>> _parse_number("10")
        10
        >>> _parse_number("1.5")
        1.5
        >>> _parse_number("1/2", fractions=True)
        0.5
        >>> _parse_number("invalid")
        'invalid'
    """
    try:
        if fractions and "/" in value:
            num, denom = value.split("/", 1)
            return float(num) / float(denom)
        return float(value) if "." in value else int(value)
    except Exception:
        return value


class CooklangParser:
    """Self-contained parser for Cooklang recipe markup language.

    The CooklangParser class handles conversion of Cooklang markup text into
    structured Recipe objects. It recognizes ingredients (@), cookware (#),
    timers (~), comments (--), notes (>), and section headers (==).

    The parser maintains position information for all tokens, enabling
    round-trip conversion and format-specific rendering.

    Attributes:
        ingredient_pattern: Regex pattern for matching ingredient markup
        cookware_pattern: Regex pattern for matching cookware markup
        timer_pattern: Regex pattern for matching timer markup
        comment_inline_pattern: Regex pattern for inline comments
        comment_block_pattern: Regex pattern for block comments
        note_pattern: Regex pattern for note lines
        section_pattern: Regex pattern for section headers

    Examples:
        >>> parser = CooklangParser()
        >>> recipe_text = '''
        ... ---
        ... title: Simple Recipe
        ... ---
        ...
        ... Heat @oil{2%tbsp} in a #pan{}.
        ... Cook for ~{5%min}.
        ... '''
        >>> recipe = parser.parse(recipe_text)
        >>> recipe.title
        'Simple Recipe'
        >>> len(recipe.steps)
        1
        >>> recipe.ingredients[0].name
        'oil'
    """

    def __init__(self, ignore_section_depth: bool = True):
        """Initialize parser and compile regex patterns."""
        self.settings = RecipeSettings(ignore_section_depth=ignore_section_depth)
        self._setup_regex()

    def _get_matching_regex(
        self, qualifier: str, required_name: bool = True, also_simple: bool = True
    ) -> re.Pattern:
        # (?:~(?P<name>[\w\s()\\/\\-]){(?P<amount>[\d.\/\-]+)?%*(?P<unit>[A-Za-z]+)?}(?:\((?P<shorthand>[\w\s]+)\))?)|(?:~(?P<simple>\w+))
        regex_pattern = r"(?:"
        regex_pattern += re.escape(qualifier)
        regex_pattern += r"(?P<name>[\w\s()\\/\\-]"
        regex_pattern += r"+" if required_name else r"*"
        regex_pattern += r"){(?P<amount>[\d.\/\-]+)?%*(?P<unit>[A-Za-z]+)?}(?:\((?P<shorthand>[\w\s]+)\))?)"
        if also_simple:
            regex_pattern += "|(?:"
            regex_pattern += re.escape(qualifier)
            regex_pattern += r"(?P<simple>\w+))"

        return re.compile(regex_pattern)

    def _setup_regex(self):
        self.ingredient_pattern = self._get_matching_regex(r"@")
        self.cookware_pattern = self._get_matching_regex(r"#")
        self.timer_pattern = self._get_matching_regex(
            r"~", required_name=False, also_simple=False
        )

        self.comment_inline_pattern = re.compile(r"--(.*)$", re.MULTILINE)
        self.comment_block_pattern = re.compile(r"\[-\s*(.*?)\s*-\]", re.DOTALL)
        self.note_pattern = re.compile(r"^>\s*(.*)$", re.MULTILINE)
        self.section_pattern = re.compile(r"^(=+)\s*(.*?)\s*(=*)$")

    def parse(self, text: str) -> Recipe:
        """Parse Cooklang text and return a Recipe object"""
        recipe = Recipe()
        recipe.settings = self.settings  # Use parser settings

        # Extract and parse metadata (YAML front matter)
        text, recipe.metadata = self._parse_metadata(text)

        # Set title from metadata if available
        recipe.title = recipe.metadata.get("title")

        # Split text into paragraphs (steps are separated by empty lines)
        paragraphs = self._split_into_paragraphs(text)

        current_section = None

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check for section headers
            section_match = self.section_pattern.match(paragraph)
            if section_match:
                level = len(section_match.group(1))
                title = section_match.group(2).strip()
                current_section = Section(title=title, level=level)
                recipe.sections.append(current_section)
                continue

            # Parse the paragraph as a step
            step = self._parse_step(paragraph)
            step.section = current_section
            recipe.steps.append(step)

        # Ingredients, cookware, and timers are now automatically available as properties
        return recipe

    def _parse_metadata(self, text: str) -> Tuple[str, Dict]:
        """Extract and parse YAML front matter - improved version"""
        lines = text.split("\n")
        # remove any leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)

        if lines and lines[0].strip() == "---":
            try:
                # Find the closing ---
                end_idx = None
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        end_idx = i
                        break

                if end_idx:
                    yaml_content = "\n".join(lines[1:end_idx])
                    metadata = yaml.safe_load(yaml_content) or {}
                    remaining_text = "\n".join(lines[end_idx + 1 :]).strip()
                    return remaining_text, metadata
            except yaml.YAMLError:
                pass

        return text, {}

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (separated by empty lines)"""
        # Split on double newlines or more
        paragraphs = re.split(r"\n\s*\n", text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def _parse_step(self, text: str) -> Step:
        """Parse a single step into a sequence of tokens"""
        tokens = []
        position = 0

        # Find all matches for different token types
        all_matches = []

        # Find ingredients
        for match in self.ingredient_pattern.finditer(text):
            ingredient = self._create_ingredient_from_match(match)
            all_matches.append((match.start(), match.end(), ingredient, match.group(0)))

        # Find cookware
        for match in self.cookware_pattern.finditer(text):
            cookware = self._create_cookware_from_match(match)
            all_matches.append((match.start(), match.end(), cookware, match.group(0)))

        # Find timers
        for match in self.timer_pattern.finditer(text):
            timer = self._create_timer_from_match(match)
            all_matches.append((match.start(), match.end(), timer, match.group(0)))

        # Find notes
        for match in self.note_pattern.finditer(text):
            note = Note(text=match.group(1).strip())
            all_matches.append((match.start(), match.end(), note, match.group(0)))

        # Find inline comments
        for match in self.comment_inline_pattern.finditer(text):
            comment = Comment(text=match.group(1).strip(), is_block=False)
            all_matches.append((match.start(), match.end(), comment, match.group(0)))

        # Find block comments
        for match in self.comment_block_pattern.finditer(text):
            comment = Comment(text=match.group(1).strip(), is_block=True)
            all_matches.append((match.start(), match.end(), comment, match.group(0)))

        # Sort matches by position
        all_matches.sort(key=lambda x: x[0])

        # Build tokens, filling gaps with text tokens
        for start, end, data, original_text in all_matches:
            # Add text token for any gap before this match
            if position < start:
                gap_text = text[position:start]
                if gap_text.strip():  # Only add non-whitespace text
                    tokens.append(
                        TextToken(text=gap_text, start_pos=position, end_pos=start)
                    )

            # Add the specific token
            if isinstance(data, Ingredient):
                tokens.append(
                    IngredientToken(
                        text=original_text,
                        start_pos=start,
                        end_pos=end,
                        ingredient=data,
                    )
                )
            elif isinstance(data, Cookware):
                tokens.append(
                    CookwareToken(
                        text=original_text, start_pos=start, end_pos=end, cookware=data
                    )
                )
            elif isinstance(data, Timer):
                tokens.append(
                    TimerToken(
                        text=original_text, start_pos=start, end_pos=end, timer=data
                    )
                )
            elif isinstance(data, Comment):
                tokens.append(
                    CommentToken(
                        text=original_text, start_pos=start, end_pos=end, comment=data
                    )
                )
            elif isinstance(data, Note):
                tokens.append(
                    NoteToken(
                        text=original_text, start_pos=start, end_pos=end, note=data
                    )
                )
            else:
                raise ValueError("Unknown data type in token parsing")
            position = end

        # Add any remaining text
        if position < len(text):
            remaining_text = text[position:]
            if remaining_text.strip():
                tokens.append(
                    TextToken(
                        text=remaining_text, start_pos=position, end_pos=len(text)
                    )
                )
        return Step(tokens=tokens)

    def _create_ingredient_from_match(self, match) -> Ingredient:
        """Create an Ingredient object from a regex match"""
        if match.group("simple"):
            return Ingredient(name=match.group("simple").strip())

        name = match.group("name").strip()

        quantity_str = match.group("amount") if match.group("amount") else None
        unit = match.group("unit") if match.group("unit") else None
        # Handle both preparation syntaxes
        preparation = match.group("shorthand")
        quantity = None
        if quantity_str:
            quantity = _parse_number(quantity_str)

        return Ingredient(
            name=name, quantity=quantity, unit=unit, preparation=preparation
        )

    def _create_cookware_from_match(self, match) -> Cookware:
        """Create a Cookware object from a regex match"""
        if match.group("simple"):
            return Cookware(name=match.group("simple").strip())
        name = match.group("name").strip()
        quantity = match.group("amount") if match.group("amount") else None
        return Cookware(name=name, quantity=quantity)

    def _create_timer_from_match(self, match) -> Timer:
        """Create a Timer object from a regex match"""
        name = match.group("name").strip() if match.group("name") else None
        duration_str = match.group("amount") if match.group("amount") else None
        unit = match.group("unit") if match.group("unit") else None

        duration = None
        if duration_str:
            duration = _parse_number(duration_str)

        return Timer(name=name, duration=duration, unit=unit)


def find_related_image(file_path: str | Path) -> Optional[Path]:
    """
    Given a Cooklang file path, look for an image with the same base name
    and common image extensions in the same directory.

    Args:
        file_path: Path to the Cooklang file
    Returns:
        Path to the related image if found, else None
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    image_extensions = [".webp", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".heic"]
    base_name = file_path.stem
    directory = file_path.parent

    for ext in image_extensions:
        candidate = directory / f"{base_name}{ext}"
        if candidate.exists():
            return candidate

    return None


def read_cook(
    file_path: str | Path, infer_title: bool = True, search_image: bool = True
) -> Recipe:
    """
    Read a Cooklang file and parse it into a Recipe object

    Args:
        file_path: Path to the Cooklang file
        infer_title: If True, infer title from filename if not in metadata
    Returns:
        Recipe object parsed from the file
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cooklang not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    parser = CooklangParser()
    try:
        recipe = parser.parse(text)
    except Exception as e:
        raise ValueError(f"Error parsing Cooklang file: {e}")

    if infer_title and not recipe.title:
        recipe.title = file_path.stem.replace("_", " ").replace("-", " ").title()

    if search_image:
        image_path = find_related_image(file_path)
        if image_path:
            recipe.metadata["image"] = str(image_path)

    return recipe


def _load_tex_assets() -> list[str]:
    folder_path = Path(os.path.dirname(__file__)) / "assets"
    all_tex_files = list(folder_path.glob("*.tex"))
    all_tex_files.sort()
    text_contens = []
    for tex_file in all_tex_files:
        with open(tex_file) as f:
            text_contens.append(f.read())
    return text_contens


def latex_document(recipes: Path | list[Recipe]) -> str:
    """Generate a complete LaTeX document for one or more recipes.

    Args:
        recipes: Path to a file or folder or a list of Recipe objects
    Returns:
        Complete LaTeX document as a string
    """
    if isinstance(recipes, Path):
        if recipes.is_file():
            recipes = [read_cook(recipes)]
        elif recipes.is_dir():
            recipes = [
                read_cook(p) for p in sorted(recipes.glob("*.cook")) if p.is_file()
            ]
        else:
            raise ValueError("Provided path is neither a file nor a directory")
    elif not isinstance(recipes, list) or not all(
        isinstance(r, Recipe) for r in recipes
    ):
        raise ValueError("recipes must be a Path or a list of Recipe objects")

    latex_assets = _load_tex_assets()
    if len(latex_assets) < 3:
        raise ValueError("Could not load LaTeX assets")
    document = []
    for asset in latex_assets:
        if asset.strip() == "%% RECIPE":
            for recipe in recipes:
                document.append(recipe.to_latex())
        else:
            document.append(asset)
        document.append("\n")
    return "".join(document)

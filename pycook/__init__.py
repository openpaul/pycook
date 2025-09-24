"""
Cooklang parser for recipe markup language.

This module provides a comprehensive parser for the Cooklang recipe markup language,
which allows writing recipes in a structured text format with ingredients, cookware,
timers, and cooking instructions.

The parser converts Cooklang markup into structured Python objects and can export
to various formats including Markdown, HTML, and plain text.

Examples:
    >>> from pycook import CooklangParser
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
    >>> recipe.to_markdown()
    '# Simple Pasta\\n\\n## Ingredients...'

    Reading from file:
    >>> from pathlib import Path
    >>> from pycook import read_cook
    >>> recipe = read_cook("recipe.cook") # doctest: +SKIP
    >>> print(recipe.title) # doctest: +SKIP
"""

from .parser import CooklangParser, Recipe, read_cook

__version__ = "2.0.0"
__all__ = ["Recipe", "CooklangParser", "read_cook"]

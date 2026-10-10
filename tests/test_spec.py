"""Tests for every example given in the Cooklang spec.

The examples are taken from https://cooklang.org/docs/spec/ and cover the
core language (ingredients, steps, comments, metadata, cookware, timers)
as well as the advanced features (notes, sections, short-hand preparations,
recipe references and optional ingredients/cookware).

LaTeX and typst output are out of scope here, markdown is the primary
output format tested.
"""

import pytest

from pycooklang import CooklangParser
from pycooklang.parser import (
    CommentToken,
    CookwareToken,
    IngredientToken,
    NoteToken,
    TimerToken,
)


@pytest.fixture
def parser() -> CooklangParser:
    return CooklangParser()


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------


def test_ingredient_single_and_multiword(parser):
    recipe = parser.parse("Then add @salt and @ground black pepper{} to taste.")
    assert [(i.name, i.quantity, i.unit) for i in recipe.ingredients] == [
        ("salt", None, None),
        ("ground black pepper", None, None),
    ]


def test_ingredient_quantity(parser):
    recipe = parser.parse("Poke holes in @potato{2}.")
    assert [(i.name, i.quantity, i.unit) for i in recipe.ingredients] == [
        ("potato", 2, None)
    ]


def test_ingredient_unit(parser):
    recipe = parser.parse(
        "Place @bacon strips{1%kg} on a baking sheet and glaze with @syrup{1/2%tbsp}."
    )
    assert [(i.name, i.quantity, i.unit) for i in recipe.ingredients] == [
        ("bacon strips", 1, "kg"),
        ("syrup", "1/2", "tbsp"),
    ]


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def test_steps_are_paragraphs(parser):
    recipe = parser.parse("A step,\nthe same step.\n\nA different step.")
    assert len(recipe) == 2
    assert recipe.steps[0].text == "A step,\nthe same step."


def test_backslash_line_break(parser):
    text = (
        "Lay out the @rice paper{1}.\\\n"
        "Top with @avocado{1/2}(sliced),\\\n"
        "@cucumber{1/2}(julienned),\\\n"
        "and @cooked shrimp{4}."
    )
    recipe = parser.parse(text)
    assert len(recipe) == 1
    step = recipe.steps[0]
    assert "\\" not in step.text
    assert step.text.split("\n") == [
        "Lay out the @rice paper{1}.",
        "Top with @avocado{1/2}(sliced),",
        "@cucumber{1/2}(julienned),",
        "and @cooked shrimp{4}.",
    ]
    assert [(i.name, i.preparation) for i in step.ingredients] == [
        ("rice paper", None),
        ("avocado", "sliced"),
        ("cucumber", "julienned"),
        ("cooked shrimp", None),
    ]
    # markdown keeps the forced line breaks inside the step
    instructions = recipe.to_markdown().split("## Instructions", 1)[1]
    assert instructions.count("\n") >= 4
    assert "\\" not in instructions


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_comment_on_own_line(parser):
    recipe = parser.parse("-- Don't burn the roux!")
    assert len(recipe) == 0  # comment only steps do not count as steps
    assert recipe.steps[0].is_comment
    assert isinstance(recipe.steps[0].tokens[0], CommentToken)
    assert recipe.steps[0].to_plain_text() == ""


def test_inline_comment(parser):
    recipe = parser.parse(
        "Mash @potato{2%kg} until smooth -- alternatively, boil 'em first."
    )
    step = recipe.steps[0]
    assert [(i.name, i.quantity, i.unit) for i in step.ingredients] == [
        ("potato", 2, "kg")
    ]
    assert len(step.comments) == 1
    assert step.comments[0].text == "alternatively, boil 'em first."
    assert "alternatively" not in step.to_plain_text()
    assert "*(alternatively, boil 'em first.)*" in recipe.to_markdown()


def test_block_comment(parser):
    recipe = parser.parse(
        "Slowly add @milk{4%cup} [- TODO change units to litres -], keep mixing"
    )
    step = recipe.steps[0]
    assert [(i.name, i.quantity, i.unit) for i in step.ingredients] == [
        ("milk", 4, "cup")
    ]
    assert step.comments[0].is_block
    assert step.comments[0].text == "TODO change units to litres"
    assert "<!-- TODO change units to litres -->" in recipe.to_markdown()


def test_comment_swallows_markup(parser):
    """Markup inside a comment is not parsed, the comment wins."""
    recipe = parser.parse("Add the spices -- like @salt{} and #pepper{}.")
    step = recipe.steps[0]
    assert recipe.ingredients == []
    assert recipe.cookware == []
    assert len(step.tokens) == 2  # text + comment
    assert step.to_markdown().count("like @salt") == 1
    assert step.to_markdown().count("and #pepper") == 1


def test_block_comment_swallows_inline_comment(parser):
    recipe = parser.parse("Add @salt{} [- a -- b -] and pepper")
    step = recipe.steps[0]
    assert [i.name for i in step.ingredients] == ["salt"]
    assert len(step.comments) == 1
    assert step.comments[0].is_block
    assert step.to_markdown().count("a -- b") == 1


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_metadata_front_matter(parser):
    recipe = parser.parse(
        "---\n"
        "title: Spaghetti Carbonara\n"
        "tags:\n"
        "  - pasta\n"
        "  - quick\n"
        "  - comfort food\n"
        "---\n"
    )
    assert recipe.title == "Spaghetti Carbonara"
    assert recipe.metadata["tags"] == ["pasta", "quick", "comfort food"]


def test_metadata_is_not_a_step(parser):
    recipe = parser.parse("---\nsourced: babooshka\n---\n")
    assert recipe.steps == []
    assert recipe.metadata == {"sourced": "babooshka"}


# ---------------------------------------------------------------------------
# Cookware
# ---------------------------------------------------------------------------


def test_cookware_single_word(parser):
    recipe = parser.parse("Place the potatoes into a #pot.")
    assert [(c.name, c.quantity) for c in recipe.cookware] == [("pot", None)]
    assert recipe.ingredients == []


def test_cookware_multiword(parser):
    recipe = parser.parse("Mash the potatoes with a #potato masher{}.")
    assert [(c.name, c.quantity) for c in recipe.cookware] == [("potato masher", None)]


# ---------------------------------------------------------------------------
# Timers
# ---------------------------------------------------------------------------


def test_timer_without_name(parser):
    recipe = parser.parse(
        "Lay the potatoes on a #baking sheet{} and place into the #oven{}. "
        "Bake for ~{25%minutes}."
    )
    assert [(c.name, c.quantity) for c in recipe.cookware] == [
        ("baking sheet", None),
        ("oven", None),
    ]
    assert len(recipe.timers) == 1
    assert recipe.timers[0].name is None
    assert recipe.timers[0].duration == 25
    assert recipe.timers[0].unit == "minutes"
    assert "**25 minutes**" in recipe.to_markdown()


def test_timer_with_name(parser):
    recipe = parser.parse("Boil @eggs{2} for ~eggs{3%minutes}.")
    assert len(recipe.timers) == 1
    assert recipe.timers[0].name == "eggs"
    assert recipe.timers[0].duration == 3
    assert recipe.timers[0].unit == "minutes"
    assert isinstance(recipe.steps[0].tokens[-2], TimerToken)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def test_note(parser):
    recipe = parser.parse("> Don't burn the roux!")
    step = recipe.steps[0]
    assert len(step.tokens) == 1
    assert isinstance(step.tokens[0], NoteToken)
    assert step.tokens[0].note.text == "Don't burn the roux!"
    assert recipe.to_markdown().endswith("> Don't burn the roux!")


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def test_sections_example(parser):
    recipe = parser.parse(
        "= Dough\n"
        "\n"
        "Mix @flour{200%g} and @water{100%ml} together until smooth.\n"
        "\n"
        "== Filling ==\n"
        "\n"
        "Combine @cheese{100%g} and @spinach{50%g}, then season to taste."
    )
    assert [s.title for s in recipe.sections] == ["Dough", "Filling"]
    assert recipe.steps[0].section.title == "Dough"
    assert recipe.steps[1].section.title == "Filling"
    markdown = recipe.to_markdown()
    assert "### Dough" in markdown
    assert "### Filling" in markdown


def test_section_without_closing_equals(parser):
    recipe = parser.parse("== Filling\n\nCombine @cheese{100%g}.")
    assert [s.title for s in recipe.sections] == ["Filling"]
    assert len(recipe) == 1


def test_section_without_name(parser):
    recipe = parser.parse("=\n\nMix @flour{200%g}.")
    assert [s.title for s in recipe.sections] == [""]
    assert len(recipe) == 1


# ---------------------------------------------------------------------------
# Short-hand preparations
# ---------------------------------------------------------------------------


def test_short_hand_preparation(parser):
    recipe = parser.parse(
        "Mix @onion{1}(peeled and finely chopped) and @garlic{2%cloves}"
        "(peeled and minced) into paste."
    )
    assert [(i.name, i.preparation) for i in recipe.ingredients] == [
        ("onion", "peeled and finely chopped"),
        ("garlic", "peeled and minced"),
    ]
    markdown = recipe.to_markdown()
    assert "*(peeled and finely chopped)*" in markdown
    assert "- 1 onion (peeled and finely chopped)" in markdown


def test_short_hand_preparation_single_word(parser):
    recipe = parser.parse("Or @onion{}(red)")
    assert recipe.ingredients[0].preparation == "red"


# ---------------------------------------------------------------------------
# Referencing other recipes
# ---------------------------------------------------------------------------


def test_recipe_reference(parser):
    recipe = parser.parse("Pour over with @./sauces/Hollandaise{150%g}.")
    assert [(i.name, i.quantity, i.unit) for i in recipe.ingredients] == [
        ("./sauces/Hollandaise", 150, "g")
    ]


def test_recipe_reference_empty_braces(parser):
    """{} ends the name so the reference can be followed by text."""
    recipe = parser.parse("Serve with @./sauces/Hollandaise{} warm.")
    assert [(i.name, i.quantity) for i in recipe.ingredients] == [
        ("./sauces/Hollandaise", None)
    ]
    assert recipe.to_markdown().endswith("Serve with **./sauces/Hollandaise** warm.")


def test_period_in_text_is_not_a_reference(parser):
    """A sentence ending in a dot does not swallow following text."""
    recipe = parser.parse("Add @garlic. Then add @onion{}.")
    assert [i.name for i in recipe.ingredients] == ["garlic", "onion"]


def test_regular_ingredients_are_not_references(parser):
    recipe = parser.parse("Add @flour{200%g}, @?salt, and @./sauces/Hollandaise{}.")
    regular = recipe.ingredients[0], recipe.ingredients[1]
    for ingredient in regular:
        assert ingredient.is_reference is False
        assert ingredient.reference_path is None


def test_reference_path_relative(parser):
    recipe = parser.parse("Use @./Dough/Pizza Dough{}.")
    ref = recipe.ingredients[0]
    assert ref.is_reference is True
    assert ref.reference_path == "Dough/Pizza Dough"


def test_reference_path_leading_slash(parser):
    recipe = parser.parse("Use @/Dough/Pizza Dough{}.")
    assert recipe.ingredients[0].is_reference is True
    assert recipe.ingredients[0].reference_path == "Dough/Pizza Dough"


def test_recipe_references_property(parser):
    recipe = parser.parse(
        "Mix @./Dough/Pizza Dough{} with @./sauces/Hollandaise{} and @salt{}."
    )
    assert [r.reference_path for r in recipe.references] == [
        "Dough/Pizza Dough",
        "sauces/Hollandaise",
    ]


def test_recipe_references_deduplicated(parser):
    recipe = parser.parse("Use @./Dough/Pizza Dough{} twice: @./Dough/Pizza Dough{}.")
    assert len(recipe.references) == 1
    assert recipe.references[0].reference_path == "Dough/Pizza Dough"


# ---------------------------------------------------------------------------
# Optional ingredients and cookware
# ---------------------------------------------------------------------------


def test_optional_multiword_ingredient(parser):
    recipe = parser.parse("Season with @salt and @?chilli flakes{1%pinch}.")
    assert [(i.name, i.optional) for i in recipe.ingredients] == [
        ("salt", False),
        ("chilli flakes", True),
    ]
    assert recipe.ingredients[1].quantity == 1
    assert recipe.ingredients[1].unit == "pinch"


def test_optional_single_word_ingredient(parser):
    recipe = parser.parse("Top with @?chives")
    assert [(i.name, i.optional) for i in recipe.ingredients] == [("chives", True)]


def test_optional_cookware(parser):
    recipe = parser.parse("Use a #?splatter guard{} if you have one.")
    assert [(c.name, c.optional) for c in recipe.cookware] == [("splatter guard", True)]
    assert "- splatter guard (optional)" in recipe.to_markdown()


def test_optional_recipe_reference(parser):
    recipe = parser.parse("Pour over with @?./sauces/chimichurri{}.")
    assert [(i.name, i.optional) for i in recipe.ingredients] == [
        ("./sauces/chimichurri", True)
    ]


def test_optional_marker_needs_name_right_after(parser):
    """>? must follow the sigil directly, otherwise it is plain text."""
    recipe = parser.parse("Add @? thyme")
    assert recipe.ingredients == []
    assert recipe.steps[0].text == "Add @? thyme"
    assert recipe.to_markdown().endswith("Add @? thyme")


def test_question_mark_after_ingredient_is_plain_text(parser):
    recipe = parser.parse("Did you add the @salt{}?")
    assert [(i.name, i.optional) for i in recipe.ingredients] == [("salt", False)]
    assert recipe.steps[0].text.endswith("?")
    assert recipe.to_markdown().endswith("Did you add the **salt**?")


def test_optional_and_required_are_listed_separately(parser):
    recipe = parser.parse(
        "Stir @parmesan{100%g} into the sauce.\n\n"
        "Top with extra @?parmesan{50%g} before serving."
    )
    assert [(i.quantity, i.optional) for i in recipe.ingredients] == [
        (100, False),
        (50, True),
    ]
    markdown = recipe.to_markdown()
    assert "- 100 g parmesan" in markdown
    assert "- 50 g parmesan (optional)" in markdown


def test_optional_marked_inline_in_markdown(parser):
    recipe = parser.parse("Season with @?chilli flakes{1%pinch}.")
    instructions = recipe.to_markdown().split("## Instructions", 1)[1]
    assert "**1 pinch chilli flakes** *(optional)*" in instructions


def test_optional_marked_in_ingredient_list(parser):
    recipe = parser.parse("Season with @?chilli flakes{1%pinch} and @salt.")
    markdown = recipe.to_markdown().split("## Instructions", 1)[0]
    assert "- 1 pinch chilli flakes (optional)" in markdown
    assert "- salt" in markdown


def test_optional_ingredient_token(parser):
    recipe = parser.parse("Season with @?chilli flakes{1%pinch}.")
    token = recipe.steps[0].tokens[-2]
    assert isinstance(token, IngredientToken)
    assert token.ingredient.optional is True
    assert "*(optional)" in token.to_markdown()
    assert "(optional)" in token.to_plain_text()
    assert "(optional)" in token.to_html()


def test_optional_cookware_token(parser):
    recipe = parser.parse("Use a #?splatter guard{}.")
    token = recipe.steps[0].tokens[-2]
    assert isinstance(token, CookwareToken)
    assert token.cookware.optional is True
    assert "*(optional)" in token.to_markdown()
    assert "(optional)" in token.to_html()
    assert "(optional)" in token.to_plain_text()

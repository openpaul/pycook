import os
from pathlib import Path

import pytest

from pycook.parser import CooklangParser, Recipe, Step, read_cook

simple_recipe = Path(
    os.path.join(os.path.dirname(__file__), "examples/seed/Neapolitan Pizza.cook")
)

full_recipe = Path(os.path.join(os.path.dirname(__file__), "examples/seed/full.cook"))
no_title = Path(os.path.join(os.path.dirname(__file__), "examples/seed/no_title.cook"))


def test_CooklangParser_basic():
    if not simple_recipe.exists():
        raise FileNotFoundError("Test recipe file not found.")
    parser = CooklangParser()
    text = simple_recipe.read_text(encoding="utf-8")
    recipe = parser.parse(text)
    assert recipe.title == "Neapolitan Pizza"
    assert len(recipe.ingredients) == 10
    assert recipe.ingredients[0].name == "tipo zero flour"
    assert recipe.ingredients[0].quantity == 820
    assert recipe.ingredients[0].unit == "g"
    assert len(recipe.steps) == 5
    assert recipe.metadata.get("tags") == ["italian", "comfort food"]
    for step in recipe.steps:
        assert isinstance(step, Step)


def test_steps():
    text = "A step,\nthe same step.\n\nA different step.\n"
    parser = CooklangParser()

    paragraphs = parser._split_into_paragraphs(text)
    assert len(paragraphs) == 2
    assert paragraphs[0] == "A step,\nthe same step."

    recipe = parser.parse(text)
    assert len(recipe.steps) == 2
    assert recipe.steps[0].text == "A step,\nthe same step."


@pytest.mark.parametrize(
    "text, expected_ingredients",
    [
        (
            "Mash @potato{2%kg} until smooth -- alternatively, boil 'em first, then mash 'em, then stick 'em in a stew.",
            [("potato", 2, "kg")],
        ),
        (
            "@unbleached all-purpose flour{26%g}",
            [("unbleached all-purpose flour", 26, "g")],
        ),
        (
            "@all-purpose flour/normal flour{26%g}",
            [("all-purpose flour/normal flour", 26, "g")],
        ),
        ("@pepper and salt", [("pepper", None, None)]),
        ("@black pepper{}", [("black pepper", None, None)]),
        ("@black pepper{1-2%tbsp}", [("black pepper", "1-2", "tbsp")]),
        ("@black pepper{1/2%tbsp}", [("black pepper", "1/2", "tbsp")]),
        (
            "@black pepper{} and @salt.",
            [("black pepper", None, None), ("salt", None, None)],
        ),
        (
            "@black pepper{} and @salt and nothing else",
            [("black pepper", None, None), ("salt", None, None)],
        ),
        (
            "@black pepper{1} and @salt and nothing else",
            [("black pepper", 1, None), ("salt", None, None)],
        ),
        (
            "@black pepper{1%g} and @salt and nothing else",
            [("black pepper", 1, "g"), ("salt", None, None)],
        ),
        (
            "@black pepper{1%g} and @salt{} and nothing else",
            [("black pepper", 1, "g"), ("salt", None, None)],
        ),
        (
            "@black pepper{1%g} and @salt{1} and nothing else",
            [("black pepper", 1, "g"), ("salt", 1, None)],
        ),
        ("@flour (405) {450%g}", [("flour (405)", 450, "g")]),
    ],
)
def test_ingredient_match(text, expected_ingredients):
    parser = CooklangParser()
    recipe = parser.parse(text)
    assert len(recipe.ingredients) == len(expected_ingredients)
    for ing, expected in zip(recipe.ingredients, expected_ingredients):
        expected_name, expected_quantity, expected_unit = expected
        assert ing.name == expected_name
        assert ing.quantity == expected_quantity
        assert ing.unit == expected_unit


@pytest.mark.parametrize(
    "text, expected_timers",
    [
        (
            "Lay the potatoes on a #baking sheet{} and place into the #oven{}. Bake for ~{25%minutes}.",
            [(None, 25, "minutes")],
        ),
        ("Boil @eggs{2} for ~eggs{3%minutes}.", [("eggs", 3, "minutes")]),
        (
            "Simmer the sauce for ~{60%seconds} while stirring.",
            [(None, 60, "seconds")],
        ),
        (
            "Cook pasta for ~pasta{10%minutes} and then drain.",
            [("pasta", 10, "minutes")],
        ),
        (
            "Cook pasta for ~{1/2%hour} and then drain.",
            [(None, "1/2", "hour")],
        ),
        (
            "Cook pasta for ~a shoe{1/2%hour} and then drain.",
            [("a shoe", "1/2", "hour")],
        ),
        (
            "Let dough rise for ~dough{120%minutes} before baking.",
            [("dough", 120, "minutes")],
        ),
        ("Roast veggies for ~{45%minutes} and then serve.", [(None, 45, "minutes")]),
    ],
)
def test_timer_match(text, expected_timers):
    parser = CooklangParser()
    recipe = parser.parse(text)
    assert len(recipe.timers) == len(expected_timers)
    for timer, (name, duration, unit) in zip(recipe.timers, expected_timers):
        assert timer.name == name
        assert timer.duration == duration
        assert timer.unit == unit


@pytest.mark.parametrize(
    "text, expected_cookware",
    [
        ("Place the potatoes into a #pot.", [("pot", None)]),
        ("Mash the potatoes with a #potato masher{}.", [("potato masher", None)]),
        (
            "Use a #frying pan{} and a #spatula{} for cooking.",
            [("frying pan", None), ("spatula", None)],
        ),
        ("Bake in #oven{} for ~{30%minutes}.", [("oven", None)]),
        (
            "Combine ingredients in a #mixing bowl{} then transfer to #pan{}.",
            [("mixing bowl", None), ("pan", None)],
        ),
        ("#whisk{} the eggs until fluffy.", [("whisk", None)]),
        ("#grill{} the vegetables over medium heat.", [("grill", None)]),
    ],
)
def test_cookware_match(text, expected_cookware):
    parser = CooklangParser()
    recipe = parser.parse(text)
    assert len(recipe.cookware) == len(expected_cookware)
    for cw, (expected_name, expected_quantity) in zip(
        recipe.cookware, expected_cookware
    ):
        assert cw.name == expected_name
        assert getattr(cw, "quantity", None) == expected_quantity


def test_full_recipe_features():
    text = full_recipe.read_text(encoding="utf-8")
    parser = CooklangParser()
    recipe = parser.parse(text)
    assert recipe.title == "Spaghetti Carbonara"

    expected_ingredient_names = [
        "salt",
        "ground black pepper",
        "potato",
        "bacon strips",
        "syrup",
        "potato",
        "milk",
        "eggs",
        "flour",
        "water",
        "cheese",
        "spinach",
        "onion",
        "garlic",
        "onion",
    ]

    # ingredients
    # assert len(recipe.ingredients) == len(expected_ingredient_names)
    for ingredient, expected_name in zip(recipe.ingredients, expected_ingredient_names):
        assert ingredient.name == expected_name

    # steps
    assert len(recipe.steps) == 15

    assert recipe.metadata.get("tags") == [
        "pasta",
        "quick",
        "comfort food",
    ]


def test_to_markdown():
    text = full_recipe.read_text(encoding="utf-8")
    parser = CooklangParser()
    recipe = parser.parse(text)
    md = recipe.to_markdown()
    expected_markdown_p = (
        Path(os.path.dirname(__file__)) / "examples" / "seed" / "full.md"
    )
    expected_text = expected_markdown_p.read_text(encoding="utf-8")

    assert md.strip() == expected_text.strip()


def test_read_cook():
    recipe = read_cook(simple_recipe)
    assert isinstance(recipe, Recipe)
    assert recipe.title == "Neapolitan Pizza"

    recipe_no_title = read_cook(no_title, infer_title=True)
    assert isinstance(recipe_no_title, Recipe)
    assert recipe_no_title.title == "No Title"

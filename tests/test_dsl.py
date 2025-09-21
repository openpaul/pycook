import os
from pathlib import Path
import pytest
from pycook.dsl import CooklangParser, Recipe, Step, read_cook

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
            ["potato"],
        ),
        ("@unbleached all-purpose flour{26%g}", ["unbleached all-purpose flour"]),
        (
            "@all-purpose flour/normal flour{26%g}",
            ["all-purpose flour/normal flour"],
        ),
        ("@pepper and salt", ["pepper"]),
        ("@black pepper{}", ["black pepper"]),
        ("@black pepper{} and @salt.", ["black pepper", "salt"]),
        ("@black pepper{} and @salt and nothing else", ["black pepper", "salt"]),
        ("@black pepper{1} and @salt and nothing else", ["black pepper", "salt"]),
        ("@black pepper{1%g} and @salt and nothing else", ["black pepper", "salt"]),
        ("@black pepper{1%g} and @salt{} and nothing else", ["black pepper", "salt"]),
        ("@black pepper{1%g} and @salt{1} and nothing else", ["black pepper", "salt"]),
    ],
)
def test_ingredient_match(text, expected_ingredients):
    parser = CooklangParser()
    recipe = parser.parse(text)
    assert len(recipe.ingredients) == len(expected_ingredients)
    for ing, expected in zip(recipe.ingredients, expected_ingredients):
        assert ing.name == expected


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

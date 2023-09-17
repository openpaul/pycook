import os

from pycook.cook import Recipe, parse
from pycook.types import Ingredient, Position, Unit, Units
from pycook.utils import (create_unit, parse_cookware, parse_ingredients,
                          parse_timer)


def test_create_unit():
    for unit in Units:
        assert isinstance(create_unit(unit.name, 1.0), Unit)
        assert isinstance(create_unit(unit.name, 1.0), Unit)

    # esnure an exception is raised if unit can not be parsed
    try:
        create_unit("foo", 1.0)
        assert False
    except ValueError:
        assert True


def test_parse_simple_ingredient():
    cooklang_text = "boil @potatoes {1%Kg} until soft."
    ingredients = parse_ingredients(cooklang_text)
    assert len(ingredients) == 1


def test_parse_multi_word_ingredient():
    cooklang_text = "add @ground pepper{} until tasty."
    ingredients = parse_ingredients(cooklang_text)
    assert len(ingredients) == 1


def test_parse_ingredients():
    # Test a simple case with one ingredient
    cooklang_text = "@salt{}"
    ingredients = parse_ingredients(cooklang_text)
    assert len(ingredients) == 1
    assert ingredients[0] == Ingredient(
        name="salt", position=Position(row=0, start=0, length=7)
    )

    # Test multiple ingredients with units and amounts
    cooklang_text = """
    @salt and @ground black pepper{} to taste.
    Poke holes in @potato{2}.
    Place @bacon strips{1.2%kg} on a baking sheet and glaze with @syrup{1/2%tbsp}.
    """
    ingredients = parse_ingredients(cooklang_text)
    assert len(ingredients) == 5
    assert ingredients[0].name == "salt"

    assert ingredients[3] == Ingredient(
        name="bacon strips",
        unit=create_unit("kg", 1.2),
        position=Position(row=0, start=88, length=21),
    )
    assert ingredients[4] == Ingredient(
        name="syrup",
        unit=create_unit("tablespoon", 1.0 / 2),
        position=Position(row=0, start=143, length=16),
    )


def test_timer():
    text = "Lay the potatoes on a #baking sheet{} and place into the #oven{}. Bake for ~{25%minutes}. Maybe use an eggtimer for eggs of ~eggs{6%min}"
    timers = parse_timer(text)
    assert len(timers) == 2
    assert timers[0].name == ""
    assert timers[0].unit.unit == Units.minute

    assert timers[1].name == "eggs"
    assert timers[1].unit.unit == Units.minute
    assert timers[1].unit.amount == 6


def test_cookware():
    text = """Place the potatoes into a #pot.
Mash the potatoes with a #potato masher{}."""
    cookware = parse_cookware(text)
    assert len(cookware) == 2
    assert cookware[0].name == "pot"
    assert cookware[0].unit == None
    assert cookware[1].name == "potato masher"
    assert cookware[1].unit == None


def test_full_parser():
    example_file = "tests/examples/seed/Neapolitan Pizza.cook"
    lines = [line.strip() for line in open(example_file).readlines()]
    recipe = parse(os.path.basename(example_file), lines)
    assert isinstance(recipe, Recipe)

    assert len(recipe.metadata) == 1

    steps = recipe.steps
    assert len(steps) == 5

    assert steps[0].rows[0].ingredients[0].name == "tipo zero flour"
    assert (
        str(steps[0].rows[0])
        == "Make 6 pizza balls using 820 g tipo zero flour, 533 ml water, 24.6 g salt and 1.6 g fresh yeast. Put in a fridge for 2 days."
    )

def test_egg():
    s = "Add @egg{1}, @salt, @pepper, @paprica and @bread crums{50%g}."
    recipe = parse("test", [s])
    assert recipe.steps[0].rows[0].ingredients[0].unit == 1
    assert recipe.steps[0].rows[0].ingredients[1].name == "salt"

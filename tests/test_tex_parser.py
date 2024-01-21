import os

from pycook.cook import parse
from pycook.recipe import TexRecipe


def test_text_convert():
    example_file = "tests/examples/seed/Neapolitan Pizza.cook"
    lines = [line.strip() for line in open(example_file).readlines()]
    recipe = parse(os.path.basename(example_file), lines)

    # convert to tex
    tex_recipe = recipe.to_tex()
    assert tex_recipe.title == recipe.title
    assert tex_recipe.metadata == recipe.metadata
    assert tex_recipe.steps == recipe.steps
    assert tex_recipe.filepath == recipe.filepath
    assert tex_recipe.image == recipe.image
    assert isinstance(tex_recipe, TexRecipe)

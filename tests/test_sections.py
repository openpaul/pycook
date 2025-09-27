from pycooklang import read_cook


def test_sections(asset_folder):
    recipe = read_cook(asset_folder / "sections.cook")
    html_file = asset_folder / "sections.html"
    with open(html_file, "r", encoding="utf-8") as f:
        expected_html = f.read()
    assert recipe.to_html().strip() == expected_html.strip()


def test_only_sections(asset_folder):
    recipe = read_cook(asset_folder / "only_sections.cook")
    html_file = asset_folder / "only_sections.html"
    with open(html_file, "r", encoding="utf-8") as f:
        expected_html = f.read()
    assert recipe.to_html().strip() == expected_html.strip()

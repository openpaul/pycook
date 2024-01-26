import argparse
import os
import shutil
from typing import Generator

from loguru import logger

from .cook import parse, parse_file
from .utils import (
    _load_file,
    find_files_in_folder,
    load_tex_assets,
    replace_file_suffix,
)


def convert_cook_to_md(input_file, output_file):
    logger.info(f"Processing: {input_file}")
    output_folder = os.path.dirname(output_file)
    content = _load_file(input_file)
    title = os.path.basename(input_file).rsplit(".", 1)[0]

    if os.path.basename(output_file).rsplit(".", 1)[0] != title:
        logger.warning("Output file name does not match input file name")
        output_file = os.path.join(output_folder, title + ".md")

    # if os.path.exists(output_file):
    #    logger.error(f"Output {output_file} already exists")
    #    raise FileExistsError("Output already exists")

    recipe = parse(title, content)
    recipe.filepath = input_file

    # see if we can find the picture for it
    recipe._find_picture()

    # copy and adjust image
    if recipe.image is not None:
        image_target = os.path.join(output_folder, os.path.basename(recipe.image))
        if os.path.exists(image_target):
            os.remove(image_target)
        shutil.copy(recipe.image, image_target)
        recipe.image = os.path.basename(image_target)

    with open(output_file, "w") as fout:
        fout.writelines(str(recipe))

    logger.info(f"Wrote recipe to {output_file}")


def iterate_files(
    folder: str, new_folder: str, new_suffix: str = ".md"
) -> Generator[str, str, None]:
    for file in find_files_in_folder(folder, file_extension=".cook"):
        file_location = replace_file_suffix(file, ".md")
        file_location = file_location[len(folder) :]
        if file_location.startswith("/"):
            file_location = file_location[1:]
        output_file = os.path.join(new_folder, file_location)

        file_output_folder = os.path.dirname(output_file)
        if not os.path.exists(file_output_folder):
            os.makedirs(file_output_folder)

        yield file, output_file


def convert_folder_to_md(input_folder: str, output_folder: str):
    for file, output_file in iterate_files(
        input_folder, output_folder, new_suffix=".md"
    ):
        convert_cook_to_md(input_file=file, output_file=output_file)


def convert_folder_to_tex(input_folder: str, output_folder: str):
    recipe_text = []
    for file in find_files_in_folder(input_folder, file_extension=".cook"):
        recipe = parse_file(file).to_tex()
        recipe_text.append(str(recipe))

    with open(os.path.join(output_folder, "recipes.tex"), "w") as fout:
        for section in load_tex_assets():
            for line in section.split("\n"):
                fout.writelines(f"{line}\n")
                if line == "%% RECIPE":
                    fout.writelines(recipe_text)


def main():
    parser = argparse.ArgumentParser(
        description="Convert folder of .cook file to .md or .tex files."
    )
    parser.add_argument("-i", "--input", help="Input folder of cook files")
    parser.add_argument("-o", "--output", help="Output folder")
    parser.add_argument(
        "-f",
        "--format",
        help="What output format to use (default: md)",
        default="md",
        type=str,
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        logger.error("Input not found")
        raise FileNotFoundError(f"Folder not found: {args.input}")

    logger.debug(f"Output folder: {args.output}")
    if not os.path.exists(args.output) and args.output != "":
        os.makedirs(args.output)
        logger.info(f"Created folder {args.output}")

    if args.format == "md":
        logger.info("Converting to markdown")
        convert_folder_to_md(args.input, args.output)
    elif args.format == "tex":
        logger.info("Converting to tex")
        convert_folder_to_tex(args.input, args.output)
    else:
        raise NotImplementedError(
            f"Requested format not implemented: {args.format}. Choose 'md' or 'tex'."
        )


if __name__ == "__main__":
    main()

import argparse
import os

from loguru import logger

from .cook import parse
from .utils import _load_file, find_files_in_folder, replace_file_suffix


def convert_cook_to_md(input_file, output_file):
    output_folder = os.path.dirname(output_file)
    content = _load_file(input_file)
    title = os.path.basename(input_file).rsplit(".", 1)[0]

    if os.path.basename(output_file).rsplit(".", 1)[0] != title:
        logger.warning("Output file name does not match input file name")
        output_file = os.path.join(output_folder, title + ".md")

    if os.path.exists(output_file):
        logger.error(f"Output {output_file} already exists")
        raise FileExistsError("Output already exists")

    recipe = parse(title, content)
    with open(output_file, "w") as fout:
        fout.writelines(str(recipe))
    logger.info(f"Wrote recipe to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Convert .cook file to .md file")
    parser.add_argument("-i", "--input", help="Input folde of cook files")
    parser.add_argument("-o", "--output", help="Output folder to markdown files")

    args = parser.parse_args()

    input_folder = args.input
    output_folder = args.output

    if not os.path.exists(input_folder):
        logger.error("Input not found")
        raise FileNotFoundError(f"Folder not found: {input_folder}")

    logger.debug(f"Output folder: {output_folder}")
    if not os.path.exists(output_folder) and output_folder != "":
        os.makedirs(output_folder)
        logger.info(f"Created folder {output_folder}")


    for file in find_files_in_folder(input_folder):
        file_location = replace_file_suffix(file, ".md")
        file_location = file_location[len(input_folder):]
        if file_location.startswith("/"):
            file_location = file_location[1:]
        output_file = os.path.join(output_folder, file_location)
        
        file_output_folder = os.path.dirname(output_file)
        if not os.path.exists(file_output_folder):
            os.makedirs(file_output_folder)
        convert_cook_to_md(input_file=file, output_file=output_file)


if __name__ == "__main__":
    main()

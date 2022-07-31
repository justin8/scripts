#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import click
import zipfile
import logging

logging.basicConfig(level=logging.DEBUG)


@click.command()
@click.argument("output-name")
@click.argument("path")
def main(output_name, path):
    dir = Path(path)
    dir = dir.resolve()

    image_list = get_image_list(dir)
    create_cbz(output_name, image_list)


def create_cbz(output_name, file_list):
    if not output_name.endswith(".cbz"):
        output_name = output_name + ".cbz"

    with zipfile.ZipFile(output_name, mode="w") as archive:
        for file in file_list:
            logging.debug(f"Adding file {file.name}...")
            archive.write(str(file), file.name)


def get_image_list(dir):
    files = list(dir.expanduser().iterdir())
    prefix = find_prefix(files)

    image_list = [file for file in files if file.name.startswith(prefix)]
    logging.info(f"Found {len(image_list)} images")

    return image_list


def find_prefix(files):
    prefixes = []

    for file in files:
        prefixes.append(file.name[0:12])

    return Counter(prefixes).most_common()[0][0]


if __name__ == "__main__":
    main()

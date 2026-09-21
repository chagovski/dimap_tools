import os
import glob
import argparse
import zipfile
import yaml

import shutil


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Export selected outputs from a DIMAP product using a YAML config file."
    )
    parser.add_argument(
        "config",
        help="Path to the YAML configuration file."
    )
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """
    Load processing settings from a YAML config file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_filepath(output_dir: str, scene_name: str) -> str:
    """
    Build a base filepath inside <output_dir>/PROCESSED folder.

    For example:
        output_dir = "/tmp/AUT_Vienna_PNEO_01Jan2026/PROCESSED"
        scene_name = "AUT_Vienna_PNEO_01Jan2026"

    returns:
        "/tmp/AUT_Vienna_PNEO_01Jan2026/PROCESSED/AUT_Vienna_PNEO_01Jan2026"

    Args:
        output_dir: Path to the scene input directory.
        scene_name: Scene name to use for the base filename.

    Returns:
        A base filepath for saving outputs with file extensions appended later.
    """
    output_dir = os.path.normpath(output_dir)
    scene_name = scene_name.strip()

    if not scene_name:
        raise ValueError("scene_name must not be empty")

    base_filepath = os.path.join(output_dir, scene_name)
    os.makedirs(output_dir, exist_ok=True)

    return base_filepath



def zip_locator(input_folder: str, pattern: str = "*.zip") -> str:
    """
    Search the input folder for ZIP files.

    Args:
        input_folder (str): Path to the folder in which to search.
        pattern (str): Filename pattern to match, defaulting to `"*.zip"`.

    Returns:
        str: Normalized path to the matching ZIP file.
    """
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    search_pattern = os.path.join(input_folder, pattern)
    matches = glob.glob(search_pattern)

    files = [
        os.path.normpath(path)
        for path in matches
        if os.path.isfile(path)
    ]

    if not files:
        raise FileNotFoundError(
            f"No ZIP files found in: {input_folder}"
        )

    if len(files) > 1:
        raise RuntimeError(
            "More than one ZIP file found:\n" + "\n".join(files)
        )

    return files[0]


def dim_locator(input_folder: str, pattern: str = "DIM*.XML", recursive: bool = True) -> str:
    """
    Search the input folder for files matching the given pattern and return the
    normalized path to the DIM XML file if exactly one match is found.

    Args:
        input_folder: Path to the folder in which to search.
        pattern: Filename pattern to match. Defaults to "DIM*.XML".
        recursive: Whether to search subdirectories recursively. Defaults to True.

    Returns:
        Normalized path to the matching DIM XML file.
    """
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    search_pattern = (
        os.path.join(input_folder, "**", pattern)
        if recursive
        else os.path.join(input_folder, pattern)
    )
    matches = glob.glob(search_pattern, recursive=recursive)

    matches = [os.path.normpath(m) for m in matches if os.path.isfile(m)]

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No DIM XML file found in '{input_folder}' matching pattern '{pattern}'"
        )

    if len(matches) > 1:
        match_list = "\n".join(matches)
        raise RuntimeError(
            f"Expected exactly 1 DIM XML file in '{input_folder}' matching pattern '{pattern}', "
            f"but found {len(matches)}:\n{match_list}"
        )

    return matches[0]


def unzip_image(zip_path: str, output_folder: str) -> None:
    """
    Extract a ZIP archive into the given output folder.

    Args:
        zip_path (str): Path to the ZIP archive.
        output_folder (str): Folder to extract the archive into.
    """
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"ZIP file does not exist: {zip_path}")

    if not os.path.isdir(output_folder):
        raise FileNotFoundError(f"Output folder does not exist: {output_folder}")

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(output_folder)


def _local_output_exists(path: str) -> bool:
    """Return whether a local output file or directory already exists."""
    return os.path.isfile(path) or os.path.isdir(path)


def _remove_local_output(path: str) -> None:
    """Remove an existing local output and any sidecars sharing its full filename prefix."""
    if os.path.isdir(path):
        shutil.rmtree(path)
        return

    if os.path.isfile(path):
        os.remove(path)

    for sidecar in glob.glob(f"{path}.*"):
        if os.path.isfile(sidecar):
            os.remove(sidecar)

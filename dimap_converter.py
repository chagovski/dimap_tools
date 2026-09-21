import os
import shutil
import time
from datetime import timedelta

from utils.io_utils import (
    build_filepath,
    zip_locator,
    unzip_image,
    dim_locator,
    parse_args,
    load_config,
)
from utils.s3_utils import upload_to_s3
from utils.raster_utils import export_from_dim


if __name__ == "__main__":
    start_time = time.perf_counter()    # <-- start the timer 

    # parse and load the config
    args = parse_args()
    config = load_config(args.config)

    # At least one output type must be enabled
    if not any((config.get("export_rgb", False),
                config.get("export_ms", False),
                config.get("export_crf", False))):
        raise ValueError("At least one output must be enabled: export_rgb, export_ms, or export_crf.")

    # Prevent creating outputs just to delete them without s3 upload
    if config.get("remove_local", False) and not config.get("s3_export", False):
        raise ValueError("remove_local=True requires s3_export=True.")

    # build IO paths
    scene = config["scene"]
    input_dir = os.path.join(config["input_root"], scene)
    output_dir = os.path.join(input_dir, "PROCESSED")

    zip_path = zip_locator(input_dir)   # <-- locate the .zip in the input_dir

    if config.get("s3_export", False):
        upload_to_s3({"ZIP image": zip_path}, config)   # <-- archive .zip on s3

    unzip_image(zip_path, input_dir)    # <-- extract .zip contents

    # locate the DIMAP.xml in the extracted files
    dim_xml = dim_locator(
        input_dir,
        config.get("dimap_pattern", "DIM*.XML"),
        recursive=True
    )

    filepath = build_filepath(output_dir)   # <-- construct a base filepath for saving outputs

    # create the outputs chosen in the config
    outputs = export_from_dim(
        dim_xml,
        filepath,
        export_rgb=config.get("export_rgb", False),
        export_ms=config.get("export_ms", False),
        export_crf=config.get("export_crf", False),
        stats=config.get("stats", True),
        overviews=config.get("overviews", True),
        nodata_value=config.get("nodata_value", 0),
        rgb_bands=config.get("rgb_bands", [1, 2, 3]),
    )

    # upload the locally created outputs to their respective s3 buckets
    if config.get("s3_export", False):
        upload_to_s3(outputs, config)

    # delete all local files including the .zip and the scene folder
    if config.get("remove_local", False):
        shutil.rmtree(input_dir, ignore_errors=False)

    elapsed_time = time.perf_counter() - start_time     # <-- stop timer and print elapsed time
    print(f"\nThe script completed in {timedelta(seconds=round(elapsed_time))}.")
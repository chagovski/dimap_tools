import os
import arcpy

from osgeo import gdal
gdal.UseExceptions()
gdal.SetConfigOption("COMPRESS_OVERVIEW", "DEFLATE")

from utils.io_utils import _local_output_exists, _remove_local_output

def calculate_statistics(raster_path, nodata_value):
    """
    Calculate raster statistics while ignoring the specified NoData value.

    Args:
        raster_path: Path to the raster dataset.
        nodata_value: Pixel value to ignore during statistics calculation.
    """
    arcpy.management.CalculateStatistics(
        in_raster_dataset=raster_path,
        x_skip_factor=1,
        y_skip_factor=1,
        ignore_values=str(nodata_value),
        skip_existing="OVERWRITE"
    )


def copy_to_crf(dim_xml, out_crf, nodata_value):
    """
    Copy a raster to CRF format with the specified NoData value.

    Args:
        dim_xml: Path to the input raster.
        out_crf: Path to the output CRF dataset.
        nodata_value: NoData value to assign.
    """
    out_folder = os.path.dirname(out_crf)
    if out_folder and not os.path.exists(out_folder):
        os.makedirs(out_folder)

    arcpy.management.CopyRaster(
        in_raster=dim_xml,
        out_rasterdataset=out_crf,
        pixel_type="16_BIT_UNSIGNED",
        nodata_value=str(nodata_value),
        format="CRF"
    )


def translate_to_geotiff(src, out_tif, band_list, stats, overviews, nodata_value):
    """
    Translate a source raster to GeoTIFF with optional overviews and statistics.

    Args:
        src: Path to the input raster source.
        out_tif: Path to the output GeoTIFF.
        band_list: List of band indices to include.
        stats: Whether to calculate raster statistics after translation.
        overviews: Whether to build overview pyramids.
        nodata_value: NoData value to assign.
    """
    translate_options = gdal.TranslateOptions(
        bandList=band_list,
        outputType=gdal.GDT_UInt16,
        format="GTiff",
        noData=nodata_value,
        creationOptions=[
            "TILED=YES",
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
            "BIGTIFF=IF_SAFER"
        ]
    )

    out_ds = gdal.Translate(out_tif, src, options=translate_options)
    if out_ds is None:
        raise RuntimeError(f"gdal.Translate failed for {out_tif}")

    if overviews:
        out_ds.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32])

    out_ds.FlushCache()
    out_ds = None

    if stats:
        calculate_statistics(out_tif, nodata_value)


def export_from_dim(
    dim_xml,
    filepath,
    export_rgb,
    export_ms,
    export_crf,
    stats,
    overviews,
    nodata_value=0,
    rgb_bands=None,
):
    """
    Export requested raster outputs from a DIMAP XML file.

    Args:
        dim_xml: Path to the DIMAP XML file.
        filepath: Base output filepath without extension.
        export_rgb: Whether to export an RGB GeoTIFF.
        export_ms: Whether to export a multispectral GeoTIFF.
        export_crf: Whether to export a CRF raster.
        stats: Whether to compute raster statistics.
        overviews: Whether to build overview pyramids.
        nodata_value: NoData value to assign to outputs (black edge pixel masking).
        rgb_bands: List of band numbers to use for RGB export.
        overwrite: Whether to overwrite existing local outputs.

    Returns:
        A dictionary mapping output labels to written file paths.
    """
    outputs = {}

    src = None
    raster_count = None

    if export_rgb or export_ms:
        src = gdal.Open(dim_xml, gdal.GA_ReadOnly)
        if src is None:
            raise RuntimeError(f"Could not open DIMAP product: {dim_xml}")

        raster_count = src.RasterCount
        if raster_count < 1:
            raise RuntimeError("No bands found in source raster")

    if export_rgb:
        if raster_count < 3:
            raise RuntimeError(f"RGB requested, but only {raster_count} band(s) available")

        rgb_out = f"{filepath}_RGB.tif"
        print("\nCreating RGB raster locally")
        print(f"  Output path: {rgb_out}")

        if _local_output_exists(rgb_out):
            print("  WARNING:    Local RGB output already exists and will be overwritten")
            _remove_local_output(rgb_out)

        translate_to_geotiff(src, rgb_out, rgb_bands, stats, overviews, nodata_value)
        print("  Status:      done")
        outputs["RGB raster"] = rgb_out

    if export_ms:
        ms_out = f"{filepath}_MS.tif"
        all_bands = list(range(1, raster_count + 1))
        print("\nCreating Multispectral raster locally")
        print(f"  Output path: {ms_out}")

        if _local_output_exists(ms_out):
            print("  WARNING:    Local MS output already exists and will be overwritten")
            _remove_local_output(ms_out)

        translate_to_geotiff(src, ms_out, all_bands, stats, overviews, nodata_value)
        print("  Status:      done")
        outputs["Multispectral raster"] = ms_out

    if src is not None:
        src = None

    if export_crf:
        crf_out = f"{filepath}.crf"
        print("\nCreating CRF raster locally")
        print(f"  Output path: {crf_out}")

        if _local_output_exists(crf_out):
            print("  WARNING:    Local CRF output already exists and will be overwritten")
            _remove_local_output(crf_out)

        copy_to_crf(dim_xml, crf_out, nodata_value)
        print("  Status:      done")
        outputs["CRF raster"] = crf_out

    return outputs

# DIMAP TOOLS

This repository provides tools to process Airbus imagery products (SPOT, P1, and PNEO) directly from `DIMAP.xml` files, generate raster outputs, and upload the results to the corresponding S3 buckets.

## Features

- Compute RGB, multispectral (all-band) and/or CRF raster outputs directly from `DIMAP.xml` files
- Compute statistics and overviews (pyramids) for each of the outputs (where applicable)
- Archive the input scene (.zip) to the S3 archive bucket
- Upload outputs to the appropriate S3 buckets
- Remove the input directory and locally created outputs after a successful S3 upload

## Caveats

- Already existing files will be overwritten, both locally and on S3
- This tool works for a single scene, e.g. delivered by Airbus as a single .zip file. The tool will fail if multiple .zip or `DIMAP.xml` files are found in the input directory.
- This tool is specific to Airbus imagery from sensors PNEO, P1 and SPOT. It could potentially be adapted to other sensors, including from other vendors, provided a `DIMAP.xml` file is available.

## Input requirements

A single configuration `.yaml` file is required to execute the tool.
The tool processes **one scene per run**, so each configuration file should refer to a single scene only.

A template configuration file is provided: `configs/EXAMPLE.yaml`

Create a copy of `EXAMPLE.yaml` in the `configs/` folder and name it after the scene following the convention `ISO3_Locality_Sensor_Date`, for example `AUT_Vienna_SPOT_01Sep2026.yaml`.

### Configuration file template

```yaml
# --- INPUTS: Required ---
scene: AUT_Vienna_PNEO_01Sep2026
input_root: I:\IMAGERY

# --- OUTPUTS: Required ---
export_rgb: false
export_ms: false
export_crf: false

# --- EXPORT & CLEANUP: Required ---
s3_export: false
remove_local: false # <-- ONLY possible after successful S3 upload

# --- DEFAULTS: Optional ---
dimap_pattern: DIM*.XML
stats: true
overviews: true
nodata_value: 0
data_type: 16_BIT_UNSIGNED
rgb_bands: [1, 2, 3]
s3_profile: prod
```

### Parameter reference

> [!IMPORTANT]
> At least one output type must be enabled. One or more of `export_rgb`, `export_ms`, or `export_crf` must be set to `true`.
> [!IMPORTANT]
> Deleting the input directory and the locally created outputs is only possible after a successful S3 upload. Therefore, `remove_local: true` requires `s3_export: true`.

| Parameter | Status | Type | Default | Description |
|----------|--------|------|---------|-------------|
| `scene` | Required | `string` | — | Scene identifier used for processing. Mandatory naming convention: `ISO3_Locality_Sensor_Date`. |
| `input_root` | Required | `string` | — | Root directory containing the input scene data. |
| `export_rgb` | Required | `boolean` | `false` | If `true`, generate an RGB raster output using the configured RGB band combination. |
| `export_ms` | Required | `boolean` | `false` | If `true`, generate a multispectral raster output containing all available bands. |
| `export_crf` | Required | `boolean` | `false` | If `true`, generate a CRF raster output. |
| `s3_export` | Required | `boolean` | `false` | If `true`, upload generated outputs and archive data to the configured S3 buckets. |
| `remove_local` | Required | `boolean` | `false` | If `true`, remove the input directory and locally generated outputs. ONLY possible if `s3_export`: `true`. |
| `dimap_pattern` | Optional | `string` | `DIM*.XML` | File pattern used to locate the Airbus DIMAP metadata file. |
| `stats` | Optional | `boolean` | `true` | If `true`, compute raster statistics for generated outputs where applicable. |
| `overviews` | Optional | `boolean` | `true` | If `true`, build raster overviews/pyramids for generated outputs where applicable. |
| `nodata_value` | Optional | `integer` | `0` | Nodata value assigned to output rasters. |
| `data_type` | Optional | `string` | `16_BIT_UNSIGNED` | Output raster data type. |
| `rgb_bands` | Optional | `list[int]` | `[1, 2, 3]` | Band indices used for the RGB output. |
| `s3_profile` | Optional | `string` | `prod` | AWS profile used for S3 authentication and upload operations. |

## Usage

Run the tool from the repository root by passing the configuration file, for example:

```bash
python dimap_converter.py configs/AUT_Vienna_SPOT_01Sep2026.yaml
```

## Tests

At present, the repository includes a single integration test for validating AWS authentication, connectivity, and basic S3 operations.

### Run the test

Run the test from the repository root:

```bash
python /path/to/repository/tests/test_s3.py
```

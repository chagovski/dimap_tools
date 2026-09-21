import os
import glob
import boto3
import botocore

def _upload_file(s3_client, local_file: str, bucket: str, s3_key: str) -> None:
    """Upload a single file to S3."""
    s3_client.upload_file(local_file, bucket, s3_key)


def _file_with_sidecars(local_file: str) -> list[str]:
    """Return a file and any sidecars that share its full filename prefix."""
    matches = [local_file]
    matches.extend(glob.glob(f"{local_file}.*"))
    return [m for m in matches if os.path.isfile(m)]


def _upload_directory(s3_client, local_dir: str, bucket: str, s3_prefix: str) -> int:
    """Upload a directory tree to S3, preserving relative paths."""
    count = 0
    for root, _, files in os.walk(local_dir):
        for filename in files:
            local_file = os.path.join(root, filename)
            rel_path = os.path.relpath(local_file, local_dir)
            rel_path = rel_path.replace(os.sep, "/")
            s3_key = f"{s3_prefix.rstrip('/')}/{rel_path}"
            _upload_file(s3_client, local_file, bucket, s3_key)
            count += 1
    return count


def _s3_object_exists(s3_client, bucket: str, key: str) -> bool:
    """Return whether the given S3 object exists."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except botocore.exceptions.ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def _s3_prefix_exists(s3_client, bucket: str, prefix: str) -> bool:
    """Return whether the given S3 prefix already contains objects."""
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix.rstrip("/") + "/",
        MaxKeys=1
    )
    return "Contents" in response


def upload_to_s3(outputs: dict[str, str], config: dict) -> None:
    """
    Upload exported outputs to S3 using a configured AWS profile.
    For GeoTIFF outputs, upload the main file and any sidecars sharing the same
    full filename prefix (for example .ovr or .aux.xml). For CRF outputs, upload
    the full directory tree recursively.

    Routing rules:
        - RGB raster -> USER_BUCKET at ISO3/PRIMARY/IMAGERY/{scene}/
        - Multispectral raster -> USER_BUCKET at ISO3/PRIMARY/IMAGERY/{scene}/
        - CRF raster -> CRF_BUCKET at ISO3/IMAGERY/{crf_name}/

    Args:
        outputs (dict[str, str]): Mapping of output labels to local output paths.
        config (dict): Parsed YAML configuration.
    """
    s3_profile = config.get("s3_profile")    
    scene = config.get("scene")

    if not s3_profile:
        raise ValueError("Missing required S3 config: s3.profile")
    if not scene:
        raise ValueError("Missing required config value: scene")

    iso3 = scene.split("_")[0]
    if len(iso3) != 3 or not iso3.isalpha() or not iso3.isupper():
        raise ValueError(
            f"Invalid ISO3 code in scene '{scene}': '{iso3}'. "
            "Expected a 3-letter uppercase code such as 'COD'."
        )

    session = boto3.Session(profile_name=s3_profile)
    s3_client = session.client("s3")

    for label, local_path in outputs.items():
        print(f"\nUploading {label} to s3")
        print(f"  Local path: {local_path}")

        if label == "ZIP image":
            bucket = "prod-msf-eo-archive-s3"
            s3_prefix = f"IMAGERY/{scene}"

            if not os.path.isfile(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            filename = os.path.basename(local_path)
            s3_key = f"{s3_prefix}/{filename}"

            if _s3_object_exists(s3_client, bucket, s3_key):
                print(
                    f"  WARNING:    {label} already exists on s3 and will be overwritten"
                    f"\ns3://{bucket}/{s3_key}"
                )

            _upload_file(s3_client, local_path, bucket, s3_key)

            print(f"  S3 prefix:  s3://{bucket}/{s3_prefix}/")
            print(f"  Uploaded:   1 file(s)")

        elif label in ("RGB raster", "Multispectral raster"):
            bucket = "prod-msf-eo-share-s3"
            s3_prefix = f"{iso3}/PRIMARY/IMAGERY/{scene}"

            if not os.path.isfile(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")

            filename = os.path.basename(local_path)
            s3_key = f"{s3_prefix}/{filename}"

            if _s3_object_exists(s3_client, bucket, s3_key):
                print(
                    f"  WARNING:    {label} already exists on s3 and will be overwritten"
                    f"\ns3://{bucket}/{s3_key}"
                )

            upload_files = _file_with_sidecars(local_path)
            for upload_file in upload_files:
                sidecar_name = os.path.basename(upload_file)
                sidecar_key = f"{s3_prefix}/{sidecar_name}"
                _upload_file(s3_client, upload_file, bucket, sidecar_key)

            print(f"  S3 prefix:  s3://{bucket}/{s3_prefix}/")
            print(f"  Uploaded:   {len(upload_files)} file(s)")

        elif label == "CRF raster":
            bucket = "prod-msf-eo-enterprise-s3"

            if not os.path.isdir(local_path):
                raise FileNotFoundError(f"Local CRF directory not found: {local_path}")

            crf_name = os.path.basename(local_path)
            s3_prefix = f"{iso3}/IMAGERY/{crf_name}"

            if _s3_prefix_exists(s3_client, bucket, s3_prefix):
                print(
                    f"  WARNING:    {label} already exists on s3 and will be overwritten"
                    f"\ns3://{bucket}/{s3_key}"
                )

            count = _upload_directory(s3_client, local_path, bucket, s3_prefix)

            print(f"  S3 prefix:  s3://{bucket}/{s3_prefix}/")
            print(f"  Uploaded:   {count} file(s)")

        else:
            raise RuntimeError(f"Unknown S3 destination mapping for output type: {label}")

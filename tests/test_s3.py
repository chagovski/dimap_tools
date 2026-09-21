import boto3
from botocore.exceptions import ClientError
from pathlib import Path


def test_s3_workflow(
    profile_name: str,
    bucket_name: str,
    local_file: str,
    s3_key: str,
    list_max_keys: int = 5,
    delete_after_upload: bool = True,
) -> None:
    print("=== S3 TEST START ===")
    print(f"Profile: {profile_name}")
    print(f"Bucket: {bucket_name}")
    print(f"Local file: {local_file}")
    print(f"S3 key: {s3_key}")
    print()

    local_path = Path(local_file)
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file does not exist: {local_file}")

    try:
        session = boto3.Session(profile_name=profile_name)
        s3 = session.client("s3")

        print("1. Testing bucket access...")
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=list_max_keys)

        print(f"Connected successfully to bucket: {bucket_name}")
        contents = response.get("Contents", [])
        if contents:
            print("Sample objects:")
            for obj in contents:
                print(f" - {obj['Key']}")
        else:
            print("Bucket is accessible but appears empty.")
        print()

        print("2. Testing file upload...")
        s3.upload_file(str(local_path), bucket_name, s3_key)
        print("Upload successful.")
        print()

        print("3. Verifying uploaded object...")
        s3.head_object(Bucket=bucket_name, Key=s3_key)
        print(f"Verified object exists: {s3_key}")
        print()

        if delete_after_upload:
            print("4. Testing deletion...")
            s3.delete_object(Bucket=bucket_name, Key=s3_key)
            print(f"Deleted: {s3_key}")
            print()

        print("=== S3 TEST COMPLETED SUCCESSFULLY ===")

    except ClientError as e:
        print("AWS Error:")
        print(e)
    except Exception as e:
        print("Error:")
        print(e)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent

    s3_profile = "uat"
    bucket_name = f"{s3_profile}-msf-eo-pub-s3"
    local_file = BASE_DIR / "test_file.txt"
    s3_key = "test/test_file.txt"

    test_s3_workflow(
        profile_name=s3_profile,
        bucket_name=bucket_name,
        local_file=str(local_file),
        s3_key=s3_key,
        list_max_keys=5,
        delete_after_upload=True,
    )

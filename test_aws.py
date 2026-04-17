from utils.aws_client import get_s3_client
import time

print("Connecting to LocalStack...")
s3 = get_s3_client()

# 1. Create a bucket
start = time.time()
s3.create_bucket(
    Bucket="innovitus-test-bucket",
    CreateBucketConfiguration={"LocationConstraint": "ap-south-1"}
)
print(f"✅ Created bucket in {time.time() - start:.2f} seconds")

# 2. List buckets
print("\nScanning for buckets:")
buckets = s3.list_buckets()["Buckets"]
for b in buckets:
    print(f"  👉 Found: {b['Name']}")

# 3. Clean up
s3.delete_bucket(Bucket="innovitus-test-bucket")
print("\n✅ Deleted bucket. Test PASSED!")
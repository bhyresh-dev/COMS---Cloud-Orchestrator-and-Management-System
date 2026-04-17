from agents.executor import execute_request

print("=== S3 Create ===")
r1 = execute_request({
    "intent": "create_s3_bucket", 
    "parameters": {"bucket_name": "executor-demo-01", "region": "ap-south-1", "access_level": "private", "size_gb": 50}
})
print(f"Success: {r1['success']} | Message: {r1.get('message')} | Time: {r1.get('execution_time_seconds')}s")

print("\n=== EC2 Launch ===")
r2 = execute_request({
    "intent": "launch_ec2_instance", 
    "parameters": {"instance_type": "t2.micro", "count": 1}
})
print(f"Success: {r2['success']} | Message: {r2.get('message')}")

print("\n=== IAM Create ===")
r3 = execute_request({
    "intent": "create_iam_role", 
    "parameters": {"role_name": "test-execution-role", "description": "Testing executor"}
})
print(f"Success: {r3['success']} | Message: {r3.get('message')}")
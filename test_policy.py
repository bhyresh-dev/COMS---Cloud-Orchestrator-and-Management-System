from agents.policy_engine import validate_request
from agents.risk_classifier import classify_risk

# The good request from our previous test
s3_req = {
    "intent": "create_s3_bucket", "service": "s3",
    "parameters": {"bucket_name": "dev-data", "region": "ap-south-1", "size_gb": 50},
    "user_context": {"team": "dev", "purpose": "storage"}
}

# A dangerous request (IAM role creation)
iam_req = {
    "intent": "create_iam_role", "service": "iam",
    "parameters": {"role_name": "god-mode-role"},
    "user_context": {"team": "security"}
}

print("=== TEST 1: Developer requesting S3 ===")
p1 = validate_request(s3_req, "developer")
r1 = classify_risk(s3_req)
print(f"Policy Approved? {p1['approved']} | Risk: {r1['tier']}")

print("\n=== TEST 2: Developer requesting IAM ===")
p2 = validate_request(iam_req, "developer")
print(f"Policy Approved? {p2['approved']}")
if not p2['approved']:
    print(f"Violations: {p2['violations']}")

print("\n=== TEST 3: Admin requesting IAM ===")
p3 = validate_request(iam_req, "admin")
r3 = classify_risk(iam_req)
print(f"Policy Approved? {p3['approved']} | Risk: {r3['tier']} (Needs approval: {r3['approval_required']})")
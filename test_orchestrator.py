from agents.orchestrator import MasterOrchestrator, approve_request

orch = MasterOrchestrator()

print("=== TEST 1: Low-Risk Auto-Execute ===")
orch.set_user_role("developer")
# Using a unique bucket name so we don't hit the EntityAlreadyExists error!
r1 = orch.process_message("Create an S3 bucket named final-test-bucket-99, ap-south-1, 50GB")
print(f"Status: {r1['status']} | Message: {r1['message']}")
print(f"Total Pipeline Time: {r1.get('total_time_seconds')}s\n")

print("=== TEST 2: High-Risk Escalation ===")
orch.reset()
orch.set_user_role("admin")
r2 = orch.process_message("Create an IAM admin role named super-admin-99")
print(f"Status: {r2['status']} | Message: {r2['message']}")

if r2['status'] == "pending_approval":
    print(f"\n--- Admin is clicking 'Approve' on ID #{r2['approval_id']} ---")
    auth = approve_request(r2['approval_id'])
    print(f"Post-Approval Status: {auth['status']} | {auth['message']}")
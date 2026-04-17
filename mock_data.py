"""
COMS — Mock Data Module
Pre-loaded data for hackathon demo preview.
"""
from datetime import datetime, timedelta
import random

def get_mock_chat_history():
    return [
        {
            "role": "user",
            "content": "Create an S3 bucket named 'analytics-data-lake' in ap-south-1"
        },
        {
            "role": "assistant",
            "content": "🟢 **Request Processed Successfully**",
            "pipeline": {
                "nlp": {"status": "completed", "intent": "create_s3_bucket", "confidence": 0.97},
                "policy": {"status": "completed", "result": "ALLOWED", "role": "Developer"},
                "risk": {"status": "completed", "level": "Low", "tier": 1},
                "execution": {"status": "completed", "result": "SUCCESS"}
            },
            "resource": {
                "type": "S3 Bucket",
                "name": "analytics-data-lake",
                "region": "ap-south-1",
                "arn": "arn:aws:s3:::analytics-data-lake",
                "created": "2026-04-17T10:32:15Z",
                "encryption": "AES-256",
                "versioning": "Enabled"
            }
        },
        {
            "role": "user",
            "content": "Launch an EC2 t3.large instance with Ubuntu 22.04 in us-east-1"
        },
        {
            "role": "assistant",
            "content": "⚠️ **Approval Required — High-Risk Action Detected**\n\nThis request involves launching a compute instance which is classified as **Tier 3 (High Risk)**. It has been escalated to an Admin for approval.",
            "pipeline": {
                "nlp": {"status": "completed", "intent": "launch_ec2_instance", "confidence": 0.94},
                "policy": {"status": "completed", "result": "ALLOWED", "role": "Developer"},
                "risk": {"status": "completed", "level": "High", "tier": 3},
                "execution": {"status": "pending_approval", "result": "AWAITING_ADMIN"}
            },
            "escalated": True
        },
        {
            "role": "user",
            "content": "List all running EC2 instances in ap-south-1"
        },
        {
            "role": "assistant",
            "content": "🟢 **Request Processed Successfully**\n\nFound **3 running instances** in `ap-south-1`:",
            "pipeline": {
                "nlp": {"status": "completed", "intent": "list_ec2_instances", "confidence": 0.99},
                "policy": {"status": "completed", "result": "ALLOWED", "role": "Developer"},
                "risk": {"status": "completed", "level": "Low", "tier": 1},
                "execution": {"status": "completed", "result": "SUCCESS"}
            },
            "instances": [
                {"id": "i-0a1b2c3d4e5f6a7b8", "type": "t3.micro", "state": "running", "name": "web-server-01"},
                {"id": "i-9c8d7e6f5a4b3c2d1", "type": "t3.small", "state": "running", "name": "api-gateway"},
                {"id": "i-1f2e3d4c5b6a7890f", "type": "m5.large", "state": "running", "name": "data-processor"},
            ]
        }
    ]


def get_mock_approvals():
    return [
        {
            "id": "REQ-20260417-0042",
            "timestamp": "2026-04-17T10:45:22Z",
            "requester": "dev-harsh",
            "role": "Developer",
            "action": "Launch EC2 Instance",
            "service": "Amazon EC2",
            "risk_level": "High",
            "risk_tier": 3,
            "description": "Launch a t3.large EC2 instance with Ubuntu 22.04 AMI in us-east-1 with public IP assignment and 50GB gp3 EBS volume.",
            "params": {
                "InstanceType": "t3.large",
                "ImageId": "ami-0c55b159cbfafe1f0",
                "Region": "us-east-1",
                "KeyName": "prod-key-pair",
                "SecurityGroupIds": ["sg-0a1b2c3d4e5f"],
                "SubnetId": "subnet-abc123",
                "EbsVolumeSize": 50,
                "EbsVolumeType": "gp3",
                "AssociatePublicIp": True,
                "Tags": {"Name": "ml-training-node", "Environment": "staging", "Team": "data-science"}
            },
            "policy_check": "PASSED",
            "status": "pending"
        },
        {
            "id": "REQ-20260417-0051",
            "timestamp": "2026-04-17T11:12:08Z",
            "requester": "dev-sugnesh",
            "role": "Developer",
            "action": "Delete S3 Bucket",
            "service": "Amazon S3",
            "risk_level": "Critical",
            "risk_tier": 4,
            "description": "Permanently delete S3 bucket 'legacy-logs-2024' and all contained objects. This action is irreversible.",
            "params": {
                "BucketName": "legacy-logs-2024",
                "Region": "ap-south-1",
                "ForceDelete": True,
                "DeleteAllObjects": True,
                "ExpectedObjectCount": 14823,
                "EstimatedSizeGB": 42.7
            },
            "policy_check": "PASSED",
            "status": "pending"
        }
    ]


def get_mock_dashboard_data():
    return {
        "total_requests": 1247,
        "auto_executed": 1089,
        "pending_approval": 12,
        "denied": 146,
        "total_delta": "+23%",
        "auto_delta": "+18%",
        "pending_delta": "-4",
        "denied_delta": "-7%",
        "comparison_data": {
            "categories": [
                "Provision VM", "Create Storage", "Configure Network",
                "Set IAM Policy", "Deploy Container", "Scale Cluster"
            ],
            "itsm_hours": [4.5, 2.0, 6.0, 3.5, 8.0, 12.0],
            "coms_seconds": [12, 4, 18, 8, 25, 35]
        },
        "service_breakdown": {
            "EC2": 412,
            "S3": 389,
            "IAM": 198,
            "Lambda": 134,
            "RDS": 78,
            "VPC": 36
        }
    }


def get_mock_audit_log():
    base = datetime(2026, 4, 17, 11, 0, 0)
    return [
        {"time": (base - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ S3 Bucket 'analytics-data-lake' created successfully",
         "user": "dev-harsh", "risk": "Low", "status": "success"},
        {"time": (base - timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "⏳ EC2 Launch (t3.large) escalated to Admin approval",
         "user": "dev-harsh", "risk": "High", "status": "pending"},
        {"time": (base - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ IAM Policy 'ReadOnlyS3Access' attached to role 'data-analyst'",
         "user": "admin-ravi", "risk": "Medium", "status": "success"},
        {"time": (base - timedelta(minutes=22)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "❌ Request denied: Delete production RDS instance (policy violation)",
         "user": "dev-sugnesh", "risk": "Critical", "status": "denied"},
        {"time": (base - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ Lambda function 'image-resizer-v2' deployed (128MB, Python 3.11)",
         "user": "dev-harsh", "risk": "Low", "status": "success"},
        {"time": (base - timedelta(minutes=38)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ VPC Peering connection established (vpc-a1b2 ↔ vpc-c3d4)",
         "user": "admin-ravi", "risk": "Medium", "status": "success"},
        {"time": (base - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "⏳ S3 Bucket deletion 'legacy-logs-2024' escalated to Admin",
         "user": "dev-sugnesh", "risk": "Critical", "status": "pending"},
        {"time": (base - timedelta(minutes=52)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ Security Group 'sg-web-tier' rules updated (port 443 ingress)",
         "user": "dev-harsh", "risk": "Low", "status": "success"},
        {"time": (base - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "✅ CloudWatch alarm 'high-cpu-alert' created for i-0a1b2c3d",
         "user": "admin-ravi", "risk": "Low", "status": "success"},
        {"time": (base - timedelta(minutes=75)).strftime("%Y-%m-%d %H:%M:%S"),
         "action": "❌ Request denied: Terminate EC2 in prod (requires Admin role)",
         "user": "dev-sugnesh", "risk": "Critical", "status": "denied"},
    ]

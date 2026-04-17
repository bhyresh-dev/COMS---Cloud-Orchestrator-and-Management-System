"""
AWS client factory.

Supports two modes (toggled via .env or at runtime):
  - LOCAL  → LocalStack (http://localhost:4566) — zero cost, no real cloud
  - REAL   → Real AWS Free Tier — creates actual resources

To use REAL AWS free tier (create actual S3 buckets by prompting!):
  1. Sign up at https://aws.amazon.com/free  (12-month free tier)
  2. Go to IAM → Create user with programmatic access
  3. Set AWS_ENDPOINT_URL="" (or remove the line) in your .env
  4. Set real AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
  5. Restart the app → all commands now hit real AWS

Free tier limits (12 months):
  S3  : 5 GB storage, 20k GET, 2k PUT requests/month
  EC2 : 750 hrs/month t2.micro or t3.micro
  IAM : Always free
  Lambda: 1M requests/month — always free forever
  SNS : 1M publishes/month — always free
"""
import boto3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# If AWS_ENDPOINT_URL is set → LocalStack mode; if blank/absent → real AWS
_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "").strip() or None
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "test")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

# Expose mode so the UI can show which is active
AWS_MODE = "LocalStack (Dev)" if _ENDPOINT else "Real AWS (Free Tier)"


def _get_client(service: str):
    kwargs = dict(
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )
    if _ENDPOINT:
        kwargs["endpoint_url"] = _ENDPOINT
    return boto3.client(service, **kwargs)


def get_s3_client():       return _get_client("s3")
def get_ec2_client():      return _get_client("ec2")
def get_iam_client():      return _get_client("iam")
def get_lambda_client():   return _get_client("lambda")
def get_sns_client():      return _get_client("sns")
def get_logs_client():     return _get_client("logs")       # CloudWatch Logs

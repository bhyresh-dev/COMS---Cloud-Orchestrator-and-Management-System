"""
COMS — AWS Resource Cleanup Script

Reads every active/pending resource from Firestore and deletes it from AWS.
Run once and discard.

Usage:
    python cleanup_aws.py
"""
import sys
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from utils.aws_client import (
    get_s3_client, get_ec2_client, get_iam_client,
    get_lambda_client, get_sns_client, get_logs_client,
)
from utils.firestore_db import get_resources_multi_status, delete_resource_record

OK  = "✓"
ERR = "✗"


def _delete_s3(name: str):
    s3 = get_s3_client()
    # Empty bucket first (required before deletion)
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=name):
            objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objects:
                s3.delete_objects(Bucket=name, Delete={"Objects": objects})
    except s3.exceptions.NoSuchBucket:
        pass
    s3.delete_bucket(Bucket=name)


def _delete_ec2(instance_id: str):
    ec2 = get_ec2_client()
    ec2.terminate_instances(InstanceIds=[instance_id])


def _delete_iam_role(name: str):
    iam = get_iam_client()
    # Detach all managed policies first
    try:
        attached = iam.list_attached_role_policies(RoleName=name).get("AttachedPolicies", [])
        for p in attached:
            iam.detach_role_policy(RoleName=name, PolicyArn=p["PolicyArn"])
        # Remove inline policies
        inline = iam.list_role_policies(RoleName=name).get("PolicyNames", [])
        for p in inline:
            iam.delete_role_policy(RoleName=name, PolicyName=p)
        # Remove from instance profiles
        profiles = iam.list_instance_profiles_for_role(RoleName=name).get("InstanceProfiles", [])
        for pr in profiles:
            iam.remove_role_from_instance_profile(
                InstanceProfileName=pr["InstanceProfileName"], RoleName=name
            )
    except iam.exceptions.NoSuchEntityException:
        pass
    iam.delete_role(RoleName=name)


def _delete_lambda(name: str):
    lmb = get_lambda_client()
    lmb.delete_function(FunctionName=name)


def _delete_sns(name: str):
    sns = get_sns_client()
    topics = sns.list_topics().get("Topics", [])
    arn = next((t["TopicArn"] for t in topics if t["TopicArn"].endswith(f":{name}")), None)
    if arn:
        sns.delete_topic(TopicArn=arn)
    else:
        raise ValueError(f"SNS topic '{name}' not found in AWS")


def _delete_log_group(name: str):
    logs = get_logs_client()
    logs.delete_log_group(logGroupName=name)


HANDLERS = {
    "S3 Bucket":            ("bucket_name",    _delete_s3),
    "EC2 Instance":         ("instance_name",  _delete_ec2),
    "IAM Role":             ("role_name",       _delete_iam_role),
    "Lambda Function":      ("function_name",  _delete_lambda),
    "SNS Topic":            ("topic_name",     _delete_sns),
    "CloudWatch Log Group": ("log_group_name", _delete_log_group),
}


def main():
    print("\n=== COMS AWS Cleanup ===\n")

    resources = get_resources_multi_status(["active", "pending"])
    if not resources:
        print("No resources found in Firestore. Nothing to delete.")
        return

    print(f"Found {len(resources)} resource(s) to delete:\n")
    for r in resources:
        rtype = r.get("resource_type", "unknown")
        rname = r.get("resource_name", "unknown")
        status = r.get("status", "")
        print(f"  [{status}] {rtype}: {rname}")

    print()
    confirm = input("Type 'yes' to delete all of the above from AWS: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    print()
    deleted = 0
    failed  = 0

    for r in resources:
        rtype = r.get("resource_type", "")
        rname = r.get("resource_name", "")

        if rtype not in HANDLERS:
            print(f"  {ERR} Skipped (no handler): {rtype} — {rname}")
            continue

        _, delete_fn = HANDLERS[rtype]
        try:
            delete_fn(rname)
            delete_resource_record(rname)
            print(f"  {OK} Deleted {rtype}: {rname}")
            deleted += 1
        except Exception as e:
            err = str(e)
            # Treat "not found" as already gone — still mark deleted in Firestore
            if any(x in err.lower() for x in ("nosuchbucket", "nosuchentity", "resourcenotfound",
                                                "not found", "does not exist")):
                delete_resource_record(rname)
                print(f"  {OK} Already gone, cleaned Firestore: {rtype}: {rname}")
                deleted += 1
            else:
                print(f"  {ERR} Failed {rtype}: {rname} — {err}")
                failed += 1

    print(f"\nDone. Deleted: {deleted}  Failed: {failed}")
    if failed:
        print("Check the errors above and delete failed resources manually from the AWS console.")


if __name__ == "__main__":
    main()

"""
AWS Executor — provisions real resources via boto3.
Supports: S3, EC2, IAM, Lambda, SNS, CloudWatch Logs
Works with both LocalStack (dev) and Real AWS Free Tier (prod).
"""
import time
import json
import zipfile
import io
from utils.aws_client import (
    get_s3_client, get_ec2_client, get_iam_client,
    get_lambda_client, get_sns_client, get_logs_client,
)
from utils.database import log_action, record_resource, delete_resource_record, log_budget

# Rough free-tier-safe cost estimates (USD/month) — used for budget tracking
COST_ESTIMATES = {
    "create_s3_bucket": 0.0,        # Free tier: 5 GB
    "delete_s3_bucket": 0.0,
    "list_s3_buckets": 0.0,
    "launch_ec2_instance": 0.0,     # Free tier: t2.micro 750 hrs
    "terminate_ec2_instance": 0.0,
    "describe_ec2_instances": 0.0,
    "create_iam_role": 0.0,
    "list_iam_roles": 0.0,
    "delete_iam_role": 0.0,
    "create_lambda_function": 0.0,  # Free tier: 1M req/month forever
    "list_lambda_functions": 0.0,
    "delete_lambda_function": 0.0,
    "invoke_lambda_function": 0.0,
    "create_sns_topic": 0.0,        # Free tier: 1M publishes/month
    "list_sns_topics": 0.0,
    "delete_sns_topic": 0.0,
    "create_log_group": 0.0,
    "list_log_groups": 0.0,
}


def execute_request(parsed_request: dict, user_role: str = None) -> dict:
    intent = parsed_request.get("intent", "")
    params = parsed_request.get("parameters", {})
    start = time.time()

    handlers = {
        # S3
        "create_s3_bucket":       lambda: _create_s3_bucket(params, user_role),
        "list_s3_buckets":        lambda: _list_s3_buckets(),
        "delete_s3_bucket":       lambda: _delete_s3_bucket(params),
        # EC2
        "launch_ec2_instance":    lambda: _launch_ec2_instance(params, user_role),
        "describe_ec2_instances": lambda: _describe_ec2_instances(),
        "terminate_ec2_instance": lambda: _terminate_ec2_instance(params),
        # IAM
        "create_iam_role":        lambda: _create_iam_role(params, user_role),
        "list_iam_roles":         lambda: _list_iam_roles(),
        "delete_iam_role":        lambda: _delete_iam_role(params),
        # Lambda
        "create_lambda_function": lambda: _create_lambda_function(params, user_role),
        "list_lambda_functions":  lambda: _list_lambda_functions(),
        "delete_lambda_function": lambda: _delete_lambda_function(params),
        "invoke_lambda_function": lambda: _invoke_lambda_function(params),
        # SNS
        "create_sns_topic":       lambda: _create_sns_topic(params, user_role),
        "list_sns_topics":        lambda: _list_sns_topics(),
        "delete_sns_topic":       lambda: _delete_sns_topic(params),
        # CloudWatch Logs
        "create_log_group":       lambda: _create_log_group(params, user_role),
        "list_log_groups":        lambda: _list_log_groups(),
    }

    try:
        handler = handlers.get(intent)
        if not handler:
            return {"success": False, "error": f"Unsupported intent: {intent}"}

        result = handler()
        elapsed = round(time.time() - start, 2)
        result["execution_time_seconds"] = elapsed

        status = "success" if result.get("success") else "failed"
        log_action(intent, {**params, "exec_time": elapsed}, status, user_role, elapsed)

        # Track budget estimate
        est = COST_ESTIMATES.get(intent, 0.0)
        if est > 0:
            log_budget(intent, est, user_role)

        return result

    except Exception as e:
        elapsed = round(time.time() - start, 2)
        log_action(intent, {"error": str(e)}, "error", user_role, elapsed)
        return {"success": False, "error": str(e), "execution_time_seconds": elapsed}


# ======================== HELPERS ========================

def _build_tags(user_role: str, intent: str, extra: dict = None) -> list:
    """Build mandatory + context tags for every resource."""
    tags = [
        {"Key": "CreatedBy", "Value": "COMS"},
        {"Key": "Role", "Value": user_role or "unknown"},
        {"Key": "Intent", "Value": intent},
    ]
    if extra:
        for k, v in extra.items():
            if v:
                tags.append({"Key": k, "Value": str(v)})
    return tags


# ======================== S3 ========================

def _create_s3_bucket(params: dict, user_role: str) -> dict:
    from utils.aws_client import REGION as DEFAULT_REGION
    s3 = get_s3_client()
    name = params.get("bucket_name", f"coms-{int(time.time())}")
    # Fall back to the client's configured region if NLP didn't extract one
    region = params.get("region") or DEFAULT_REGION or "ap-south-1"

    kwargs = {"Bucket": name}
    # us-east-1 must NOT have LocationConstraint — all other regions must have it
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}

    s3.create_bucket(**kwargs)

    if params.get("access_level", "private") == "private":
        try:
            s3.put_public_access_block(
                Bucket=name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True, "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
                },
            )
        except Exception:
            pass

    # Apply tags
    try:
        s3.put_bucket_tagging(
            Bucket=name,
            Tagging={"TagSet": _build_tags(user_role, "create_s3_bucket",
                                           {"Team": params.get("team"),
                                            "Purpose": params.get("purpose")})},
        )
    except Exception:
        pass

    resource = {
        "type": "S3 Bucket", "name": name, "region": region,
        "access": params.get("access_level", "private"),
        "size_gb": params.get("size_gb", "unlimited"),
    }
    record_resource("S3 Bucket", name, region, resource, user_role)
    return {"success": True, "message": f"S3 bucket '{name}' created in {region}.", "resource": resource}


def _list_s3_buckets() -> dict:
    s3 = get_s3_client()
    buckets = s3.list_buckets().get("Buckets", [])
    names = ", ".join([f"`{b['Name']}`" for b in buckets]) or "none"
    return {"success": True, "message": f"Found {len(buckets)} bucket(s): {names}"}


def _delete_s3_bucket(params: dict) -> dict:
    s3 = get_s3_client()
    name = params.get("bucket_name", "")
    if not name:
        return {"success": False, "error": "bucket_name is required to delete."}
    s3.delete_bucket(Bucket=name)
    delete_resource_record(name)
    return {"success": True, "message": f"S3 bucket '{name}' deleted."}


# ======================== EC2 ========================

def _launch_ec2_instance(params: dict, user_role: str) -> dict:
    from utils.aws_client import REGION as DEFAULT_REGION
    ec2 = get_ec2_client()
    itype = params.get("instance_type", "t2.micro")
    count = int(params.get("count", 1))
    region = params.get("region") or DEFAULT_REGION or "ap-south-1"

    tags = _build_tags(user_role, "launch_ec2_instance",
                       {"Team": params.get("team"), "Purpose": params.get("purpose")})
    tag_spec = [{"ResourceType": "instance", "Tags": tags}]

    resp = ec2.run_instances(
        ImageId=params.get("ami_id", "ami-0f5ee92e2d63afc18"),  # Amazon Linux 2 ap-south-1
        InstanceType=itype,
        MinCount=count,
        MaxCount=count,
        TagSpecifications=tag_spec,
    )
    ids = [i["InstanceId"] for i in resp.get("Instances", [])]
    resource = {"type": "EC2 Instance", "instance_ids": ids,
                "instance_type": itype, "region": region, "count": count}
    for iid in ids:
        record_resource("EC2 Instance", iid, region, resource, user_role)
    return {
        "success": True,
        "message": f"Launched {count} EC2 {itype} instance(s): {', '.join(ids)}",
        "resource": resource,
    }


def _describe_ec2_instances() -> dict:
    ec2 = get_ec2_client()
    resp = ec2.describe_instances()
    ids = []
    for res in resp.get("Reservations", []):
        for i in res.get("Instances", []):
            state = i.get("State", {}).get("Name", "unknown")
            ids.append(f"`{i['InstanceId']}` ({state})")
    msg = f"Found {len(ids)} instance(s): {', '.join(ids)}" if ids else "No instances found."
    return {"success": True, "message": msg}


def _terminate_ec2_instance(params: dict) -> dict:
    ec2 = get_ec2_client()
    iid = params.get("instance_id", "")
    if not iid:
        return {"success": False, "error": "instance_id is required."}
    ec2.terminate_instances(InstanceIds=[iid])
    delete_resource_record(iid)
    return {"success": True, "message": f"EC2 instance '{iid}' terminated."}


# ======================== IAM ========================

def _create_iam_role(params: dict, user_role: str) -> dict:
    iam = get_iam_client()
    name = params.get("role_name", f"coms-role-{int(time.time())}")
    trust_service = params.get("trust_policy_service", "ec2.amazonaws.com")
    tags = _build_tags(user_role, "create_iam_role")

    trust_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow",
                       "Principal": {"Service": trust_service},
                       "Action": "sts:AssumeRole"}],
    })

    resp = iam.create_role(
        RoleName=name,
        AssumeRolePolicyDocument=trust_policy,
        Description=params.get("description", "Created by COMS"),
        Tags=tags,
    )
    arn = resp.get("Role", {}).get("Arn", "")
    resource = {"type": "IAM Role", "name": name, "arn": arn}
    record_resource("IAM Role", name, "global", resource, user_role)
    return {"success": True, "message": f"IAM role '{name}' created.", "resource": resource}


def _list_iam_roles() -> dict:
    iam = get_iam_client()
    roles = iam.list_roles().get("Roles", [])
    display = roles[:15]
    names = ", ".join([f"`{r['RoleName']}`" for r in display])
    return {"success": True, "message": f"Found {len(roles)} role(s). Showing 15: {names}"}


def _delete_iam_role(params: dict) -> dict:
    iam = get_iam_client()
    name = params.get("role_name", "")
    if not name:
        return {"success": False, "error": "role_name is required."}
    iam.delete_role(RoleName=name)
    delete_resource_record(name)
    return {"success": True, "message": f"IAM role '{name}' deleted."}


# ======================== LAMBDA ========================

def _create_lambda_function(params: dict, user_role: str) -> dict:
    """
    Creates a Lambda function with a minimal hello-world handler.
    Free tier: 1M requests/month + 400,000 GB-seconds — forever free.
    """
    lmb = get_lambda_client()
    name = params.get("function_name", f"coms-fn-{int(time.time())}")
    runtime = params.get("runtime", "python3.12")
    handler = params.get("handler", "index.handler")
    description = params.get("description", "Created by COMS")
    role_arn = params.get("role_arn", "arn:aws:iam::000000000000:role/coms-lambda-role")

    # Build a minimal zip with a hello-world handler
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        code = (
            "import json\n\n"
            "def handler(event, context):\n"
            "    return {\n"
            "        'statusCode': 200,\n"
            "        'body': json.dumps({'message': 'Hello from COMS Lambda!', 'event': event})\n"
            "    }\n"
        )
        zf.writestr("index.py", code)
    buf.seek(0)

    tags = {t["Key"]: t["Value"] for t in _build_tags(user_role, "create_lambda_function")}

    resp = lmb.create_function(
        FunctionName=name,
        Runtime=runtime,
        Role=role_arn,
        Handler=handler,
        Code={"ZipFile": buf.read()},
        Description=description,
        Tags=tags,
    )
    arn = resp.get("FunctionArn", "")
    resource = {"type": "Lambda Function", "name": name, "runtime": runtime, "arn": arn}
    record_resource("Lambda Function", name, params.get("region", "ap-south-1"), resource, user_role)
    return {"success": True, "message": f"Lambda function '{name}' created ({runtime}).", "resource": resource}


def _list_lambda_functions() -> dict:
    lmb = get_lambda_client()
    resp = lmb.list_functions()
    fns = resp.get("Functions", [])
    names = ", ".join([f"`{f['FunctionName']}`" for f in fns]) or "none"
    return {"success": True, "message": f"Found {len(fns)} Lambda function(s): {names}"}


def _delete_lambda_function(params: dict) -> dict:
    lmb = get_lambda_client()
    name = params.get("function_name", "")
    if not name:
        return {"success": False, "error": "function_name is required."}
    lmb.delete_function(FunctionName=name)
    delete_resource_record(name)
    return {"success": True, "message": f"Lambda function '{name}' deleted."}


def _invoke_lambda_function(params: dict) -> dict:
    lmb = get_lambda_client()
    name = params.get("function_name", "")
    if not name:
        return {"success": False, "error": "function_name is required."}
    payload = params.get("payload", {})
    resp = lmb.invoke(FunctionName=name, Payload=json.dumps(payload).encode())
    body = resp["Payload"].read().decode()
    return {"success": True, "message": f"Lambda '{name}' invoked. Response: {body}"}


# ======================== SNS ========================

def _create_sns_topic(params: dict, user_role: str) -> dict:
    sns = get_sns_client()
    name = params.get("topic_name", f"coms-topic-{int(time.time())}")
    tags = _build_tags(user_role, "create_sns_topic")

    resp = sns.create_topic(Name=name, Tags=tags)
    arn = resp.get("TopicArn", "")
    resource = {"type": "SNS Topic", "name": name, "arn": arn}
    record_resource("SNS Topic", name, params.get("region", "ap-south-1"), resource, user_role)
    return {"success": True, "message": f"SNS topic '{name}' created.", "resource": resource}


def _list_sns_topics() -> dict:
    sns = get_sns_client()
    topics = sns.list_topics().get("Topics", [])
    arns = ", ".join([f"`{t['TopicArn'].split(':')[-1]}`" for t in topics]) or "none"
    return {"success": True, "message": f"Found {len(topics)} SNS topic(s): {arns}"}


def _delete_sns_topic(params: dict) -> dict:
    sns = get_sns_client()
    arn = params.get("topic_arn", "")
    name = params.get("topic_name", "")
    if not arn and not name:
        return {"success": False, "error": "topic_arn or topic_name is required."}
    # If only name given, try to find ARN
    if not arn:
        topics = sns.list_topics().get("Topics", [])
        for t in topics:
            if t["TopicArn"].endswith(f":{name}"):
                arn = t["TopicArn"]
                break
    if not arn:
        return {"success": False, "error": f"Topic '{name}' not found."}
    sns.delete_topic(TopicArn=arn)
    delete_resource_record(name or arn)
    return {"success": True, "message": f"SNS topic deleted."}


# ======================== CLOUDWATCH LOGS ========================

def _create_log_group(params: dict, user_role: str) -> dict:
    logs = get_logs_client()
    name = params.get("log_group_name", f"/coms/{int(time.time())}")
    tags = {t["Key"]: t["Value"] for t in _build_tags(user_role, "create_log_group")}
    logs.create_log_group(logGroupName=name, tags=tags)
    resource = {"type": "CloudWatch Log Group", "name": name}
    record_resource("CloudWatch Log Group", name, params.get("region", "ap-south-1"), resource, user_role)
    return {"success": True, "message": f"CloudWatch Log Group '{name}' created.", "resource": resource}


def _list_log_groups() -> dict:
    logs = get_logs_client()
    groups = logs.describe_log_groups().get("logGroups", [])
    names = ", ".join([f"`{g['logGroupName']}`" for g in groups]) or "none"
    return {"success": True, "message": f"Found {len(groups)} log group(s): {names}"}

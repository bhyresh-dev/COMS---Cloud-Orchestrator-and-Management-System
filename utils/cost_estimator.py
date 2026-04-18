"""
AWS cost estimates (USD/month) based on Free Tier and on-demand pricing.
These are approximate figures for user awareness — not billing data.
"""

# On-demand hourly rates (USD) × 730 hrs/month
_EC2_HOURLY = {
    "t2.micro":   0.0116,
    "t2.small":   0.023,
    "t2.medium":  0.0464,
    "t3.micro":   0.0104,
    "t3.small":   0.0208,
    "t3.medium":  0.0416,
    "t3.large":   0.0832,
    "t2.large":   0.0928,
}

_ESTIMATES = {
    "create_s3_bucket": {
        "monthly_usd": 0.023,
        "basis": "per GB stored (first 5 GB free on Free Tier)",
        "free_tier": "5 GB storage, 20k GET, 2k PUT requests/month",
    },
    "create_iam_role": {
        "monthly_usd": 0.0,
        "basis": "IAM roles are always free",
        "free_tier": "Always free — no cost",
    },
    "launch_ec2_instance": {
        "monthly_usd": None,  # computed dynamically from instance_type
        "basis": "per hour running (750 hrs/month free on t2.micro for 12 months)",
        "free_tier": "750 hrs/month t2.micro for 12 months",
    },
    "create_lambda_function": {
        "monthly_usd": 0.0,
        "basis": "first 1M requests/month always free",
        "free_tier": "1M requests + 400k GB-seconds compute/month forever",
    },
    "create_sns_topic": {
        "monthly_usd": 0.0,
        "basis": "first 1M publishes/month free",
        "free_tier": "1M publishes/month",
    },
    "create_log_group": {
        "monthly_usd": 0.0,
        "basis": "first 5 GB ingestion/month free",
        "free_tier": "5 GB ingestion + 5 GB storage/month",
    },
}


def estimate_cost(intent: str, parameters: dict) -> dict:
    info = _ESTIMATES.get(intent)
    if not info:
        return None

    result = dict(info)

    if intent == "launch_ec2_instance":
        itype = parameters.get("instance_type", "t2.micro")
        hourly = _EC2_HOURLY.get(itype, 0.0116)
        monthly = round(hourly * 730, 2)
        result["monthly_usd"] = monthly
        result["hourly_usd"]  = hourly
        result["instance_type"] = itype

    return result

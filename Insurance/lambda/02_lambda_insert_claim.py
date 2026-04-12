"""
Lambda Function: lambda_insert_claim.py
Description: Inserts a new insurance claim into the InsuranceClaims DynamoDB table.

Required IAM permissions:
  - dynamodb:PutItem  on  arn:aws:dynamodb:<region>:<account>:table/InsuranceClaims

Environment Variables:
  TABLE_NAME   (default: "InsuranceClaims")
  REGION       (default: "us-east-1")

Trigger: API Gateway POST /claims  (or invoke directly with a JSON payload)

Expected event payload example:
{
    "ClaimID":          "CLM-2024-000200",
    "PolicyNumber":     "POL-11112222",
    "PolicyType":       "Home",
    "PolicyHolderName": "Alice P. Johnson",
    "ClaimType":        "Water Damage",
    "ClaimStatus":      "Submitted",
    "ClaimDate":        "2024-11-20",
    "IncidentDate":     "2024-11-19",
    "IncidentLocation": "456 Oak Ave, Dallas, TX 75201",
    "IncidentDescription": "Burst pipe in the kitchen caused flooding.",
    "ClaimedAmount":    800000,
    "Deductible":       100000,
    "Currency":         "USD",
    "Priority":         "High"
}
"""

import json
import os
import logging
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── AWS resources (initialised outside handler for Lambda warm-start reuse) ───
TABLE_NAME = os.environ.get("TABLE_NAME", "InsuranceClaims")
REGION     = os.environ.get("REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

# ── Required fields ───────────────────────────────────────────────────────────
REQUIRED_FIELDS = [
    "PolicyNumber", "PolicyType", "PolicyHolderName",
    "ClaimType", "ClaimDate", "IncidentDate", "ClaimedAmount"
]

# ── Valid enum values ─────────────────────────────────────────────────────────
VALID_STATUSES  = {"Submitted", "Under Review", "Approved", "Rejected", "Closed"}
VALID_TYPES     = {"Automobile", "Home", "Health", "Life", "Travel", "Commercial"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}


def validate_payload(payload: dict) -> list:
    """Return a list of validation error messages (empty = valid)."""
    errors = []

    for field in REQUIRED_FIELDS:
        if not payload.get(field):
            errors.append(f"Missing required field: '{field}'")

    if "ClaimStatus" in payload and payload["ClaimStatus"] not in VALID_STATUSES:
        errors.append(f"Invalid ClaimStatus. Must be one of: {VALID_STATUSES}")

    if "PolicyType" in payload and payload["PolicyType"] not in VALID_TYPES:
        errors.append(f"Invalid PolicyType. Must be one of: {VALID_TYPES}")

    if "Priority" in payload and payload["Priority"] not in VALID_PRIORITIES:
        errors.append(f"Invalid Priority. Must be one of: {VALID_PRIORITIES}")

    claimed = payload.get("ClaimedAmount")
    if claimed is not None:
        try:
            if int(claimed) <= 0:
                errors.append("ClaimedAmount must be a positive integer (cents).")
        except (TypeError, ValueError):
            errors.append("ClaimedAmount must be a numeric value.")

    return errors


def build_item(payload: dict) -> dict:
    """Merge incoming payload with server-side defaults."""
    now = datetime.utcnow().isoformat() + "Z"

    item = {
        # Auto-generate ClaimID if not provided
        "ClaimID": payload.get("ClaimID") or f"CLM-{datetime.utcnow().strftime('%Y')}-{str(uuid.uuid4())[:8].upper()}",

        # ── Defaults ──────────────────────────────────────────────────────
        "ClaimStatus":    payload.get("ClaimStatus", "Submitted"),
        "ApprovedAmount": payload.get("ApprovedAmount", 0),
        "Priority":       payload.get("Priority", "Medium"),
        "Currency":       payload.get("Currency", "USD"),
        "CreatedAt":      now,
        "UpdatedAt":      now,
        "CreatedBy":      "lambda-insert",
    }

    # Merge all other fields from the payload (overrides defaults if present)
    item.update({k: v for k, v in payload.items() if k not in ("CreatedAt", "UpdatedAt", "CreatedBy")})

    return item


def lambda_handler(event, context):
    """
    Main Lambda entry point.
    Accepts both direct invocation and API Gateway proxy events.
    """
    logger.info("Event received: %s", json.dumps(event, default=str))

    # ── Parse body (API Gateway wraps payload in event["body"]) ──────────
    if "body" in event:
        try:
            payload = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON body: %s", exc)
            return _response(400, {"error": "Invalid JSON body."})
    else:
        payload = event   # Direct Lambda invocation

    # ── Validate ──────────────────────────────────────────────────────────
    errors = validate_payload(payload)
    if errors:
        logger.warning("Validation errors: %s", errors)
        return _response(400, {"errors": errors})

    # ── Build item ────────────────────────────────────────────────────────
    item = build_item(payload)

    # ── Idempotency check — do not overwrite existing ClaimID ─────────────
    try:
        table.put_item(
            Item=item,
            ConditionExpression=Attr("ClaimID").not_exists()
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning("Duplicate ClaimID: %s", item["ClaimID"])
            return _response(409, {"error": f"ClaimID '{item['ClaimID']}' already exists."})
        logger.exception("DynamoDB error")
        return _response(500, {"error": "Internal server error. Could not save claim."})

    logger.info("Claim inserted: %s", item["ClaimID"])
    return _response(201, {
        "message": "Claim created successfully.",
        "ClaimID": item["ClaimID"],
        "ClaimStatus": item["ClaimStatus"],
        "CreatedAt": item["CreatedAt"],
    })


# ── Helpers ───────────────────────────────────────────────────────────────────
def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }

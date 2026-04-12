"""
Lambda Function: lambda_get_claims.py
Description: Retrieves insurance claims from the InsuranceClaims DynamoDB table.
             Supports full scan with pagination and optional status/type filtering.

Required IAM permissions:
  - dynamodb:Scan     on  arn:aws:dynamodb:<region>:<account>:table/InsuranceClaims
  - dynamodb:GetItem  on  arn:aws:dynamodb:<region>:<account>:table/InsuranceClaims

Environment Variables:
  TABLE_NAME      (default: "InsuranceClaims")
  REGION          (default: "us-east-1")
  MAX_PAGE_SIZE   (default: 100)

Trigger: API Gateway GET /claims  or  GET /claims/{claimId}

Query string parameters (all optional):
  claimId       - retrieve a single claim by ID
  status        - filter by ClaimStatus  (e.g. "Approved")
  policyType    - filter by PolicyType   (e.g. "Automobile")
  priority      - filter by Priority     (e.g. "High")
  lastKey       - pagination token (base64-encoded LastEvaluatedKey from previous page)
  limit         - max items per page     (default: MAX_PAGE_SIZE)
"""

import json
import os
import logging
import base64
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── AWS resources ─────────────────────────────────────────────────────────────
TABLE_NAME    = os.environ.get("TABLE_NAME", "InsuranceClaims")
REGION        = os.environ.get("REGION", "us-east-1")
MAX_PAGE_SIZE = int(os.environ.get("MAX_PAGE_SIZE", 100))

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)


# ── Helpers ───────────────────────────────────────────────────────────────────
class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns Decimal for numbers — convert to int/float for JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def encode_pagination_token(last_evaluated_key: dict) -> str:
    """Encode DynamoDB LastEvaluatedKey as a base64 string for API clients."""
    return base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_pagination_token(token: str) -> dict:
    """Decode a base64 pagination token back to a DynamoDB key."""
    return json.loads(base64.b64decode(token.encode()).decode())


# ── Get single claim ──────────────────────────────────────────────────────────
def get_claim_by_id(claim_id: str) -> dict:
    """Fetch a single item by ClaimID (uses GetItem — O(1))."""
    logger.info("GetItem for ClaimID: %s", claim_id)
    try:
        response = table.get_item(Key={"ClaimID": claim_id})
    except ClientError as exc:
        logger.exception("DynamoDB GetItem error")
        raise exc

    item = response.get("Item")
    if not item:
        return _response(404, {"error": f"Claim '{claim_id}' not found."})

    return _response(200, {"claim": item})


# ── Get all claims (scan with filters) ───────────────────────────────────────
def get_all_claims(query_params: dict) -> dict:
    """
    Scan the table with optional filters and pagination.
    NOTE: Scan reads the entire table — for large datasets consider adding a
          GSI on ClaimStatus / PolicyType and using Query instead.
    """
    # ── Parse parameters ──────────────────────────────────────────────────
    status      = query_params.get("status")
    policy_type = query_params.get("policyType")
    priority    = query_params.get("priority")
    last_key_token = query_params.get("lastKey")
    limit       = min(int(query_params.get("limit", MAX_PAGE_SIZE)), MAX_PAGE_SIZE)

    # ── Build filter expression ───────────────────────────────────────────
    filter_expr = None

    def _add_filter(expr, new_condition):
        return new_condition if expr is None else expr & new_condition

    if status:
        filter_expr = _add_filter(filter_expr, Attr("ClaimStatus").eq(status))
    if policy_type:
        filter_expr = _add_filter(filter_expr, Attr("PolicyType").eq(policy_type))
    if priority:
        filter_expr = _add_filter(filter_expr, Attr("Priority").eq(priority))

    # ── Build scan kwargs ─────────────────────────────────────────────────
    scan_kwargs = {"Limit": limit}

    if filter_expr is not None:
        scan_kwargs["FilterExpression"] = filter_expr

    if last_key_token:
        try:
            scan_kwargs["ExclusiveStartKey"] = decode_pagination_token(last_key_token)
        except Exception:
            return _response(400, {"error": "Invalid pagination token (lastKey)."})

    # ── Execute scan ──────────────────────────────────────────────────────
    logger.info("Scanning table '%s' with kwargs: %s", TABLE_NAME,
                {k: str(v) for k, v in scan_kwargs.items() if k != "FilterExpression"})
    try:
        response = table.scan(**scan_kwargs)
    except ClientError as exc:
        logger.exception("DynamoDB Scan error")
        return _response(500, {"error": "Could not retrieve claims."})

    items        = response.get("Items", [])
    count        = response.get("Count", 0)
    scanned      = response.get("ScannedCount", 0)
    next_key     = response.get("LastEvaluatedKey")

    result = {
        "claims":       items,
        "count":        count,
        "scannedCount": scanned,
    }

    if next_key:
        result["nextPageToken"] = encode_pagination_token(next_key)
        result["hasNextPage"]   = True
    else:
        result["hasNextPage"] = False

    logger.info("Returned %d items (scanned %d).", count, scanned)
    return _response(200, result)


# ── Lambda handler ────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Main Lambda entry point.

    Routes:
      GET /claims             → list all claims (with optional filters)
      GET /claims/{claimId}   → get a single claim by ID
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    query_params   = event.get("queryStringParameters") or {}
    path_params    = event.get("pathParameters") or {}

    # Single claim lookup via path parameter
    claim_id = path_params.get("claimId") or query_params.get("claimId")
    if claim_id:
        return get_claim_by_id(claim_id)

    # Full scan (all claims)
    return get_all_claims(query_params)

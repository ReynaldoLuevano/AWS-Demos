"""
Lambda Function: lambda_bedrock_claims.py
Description: Calls Amazon Bedrock (Claude 3 Sonnet) to analyze an insurance claim,
             detect fraud signals, suggest an outcome, and generate a summary.

Required IAM permissions:
  - bedrock:InvokeModel           on  arn:aws:bedrock:<region>::foundation-model/*
  - dynamodb:GetItem (optional)   on  arn:aws:dynamodb:<region>:<account>:table/InsuranceClaims

Environment Variables:
  REGION          (default: "us-east-1")
  MODEL_ID        (default: "anthropic.claude-3-sonnet-20240229-v1:0")
  TABLE_NAME      (default: "InsuranceClaims")   — used when fetching claim from DynamoDB
  MAX_TOKENS      (default: 1024)

Trigger: API Gateway POST /claims/{claimId}/analyze
         or direct Lambda invocation with a JSON payload.

Event payload options:

  Option A — provide claim data directly:
  {
      "claim": {
          "ClaimID": "CLM-2024-000123",
          "PolicyType": "Automobile",
          ...
      }
  }

  Option B — provide a ClaimID and fetch from DynamoDB:
  {
      "claimId": "CLM-2024-000123"
  }

Response:
  {
      "ClaimID": "CLM-2024-000123",
      "analysis": {
          "summary":          "...",
          "riskLevel":        "Medium",
          "fraudSignals":     ["..."],
          "recommendedAction":"Approve with standard review",
          "estimatedPayout":  12000.00,
          "reasoning":        "..."
      },
      "model": "anthropic.claude-3-sonnet-20240229-v1:0",
      "inputTokens": 350,
      "outputTokens": 280
  }
"""

import json
import os
import logging
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Configuration ─────────────────────────────────────────────────────────────
REGION     = os.environ.get("REGION", "us-east-1")
MODEL_ID   = os.environ.get("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
TABLE_NAME = os.environ.get("TABLE_NAME", "InsuranceClaims")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 1024))

# ── AWS clients ───────────────────────────────────────────────────────────────
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
dynamodb        = boto3.resource("dynamodb", region_name=REGION)
table           = dynamodb.Table(TABLE_NAME)


# ── Helpers ───────────────────────────────────────────────────────────────────
class DecimalEncoder(json.JSONEncoder):
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


def fetch_claim_from_dynamo(claim_id: str) -> dict | None:
    """Retrieve a claim from DynamoDB by ClaimID."""
    try:
        response = table.get_item(Key={"ClaimID": claim_id})
        return response.get("Item")
    except ClientError as exc:
        logger.error("DynamoDB GetItem failed: %s", exc)
        return None


def build_prompt(claim: dict) -> str:
    """
    Build a structured prompt for Bedrock to analyse the insurance claim.
    Returns a plain-text prompt that asks the model to respond in JSON format.
    """
    claim_json = json.dumps(claim, indent=2, cls=DecimalEncoder)

    return f"""You are an experienced insurance claims analyst. Analyse the following insurance claim and respond ONLY with a valid JSON object (no markdown, no preamble).

CLAIM DATA:
{claim_json}

Your response must be a JSON object with exactly these fields:
{{
  "summary":           "<2-3 sentence plain-English summary of the claim>",
  "riskLevel":         "<one of: Low | Medium | High | Critical>",
  "fraudSignals":      ["<signal 1>", "<signal 2>"],   // empty array if none detected
  "recommendedAction": "<one of: Approve | Approve with investigation | Request more info | Reject | Escalate>",
  "estimatedPayout":   <number in USD, e.g. 11500.00>,
  "reasoning":         "<brief explanation of your risk assessment and recommended action>"
}}

Rules:
- fraudSignals should list concrete anomalies (e.g. "Incident reported 24h after policy start").
- If no fraud signals, return an empty array [].
- estimatedPayout must be a number (not a string).
- Do not include any text outside the JSON object.
"""


def invoke_bedrock(prompt: str) -> dict:
    """
    Send the prompt to Amazon Bedrock using the Converse API (Messages format).
    Returns the parsed JSON body from the model response.
    """
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    logger.info("Invoking Bedrock model: %s", MODEL_ID)

    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response["body"].read())
    return response_body


def parse_model_response(response_body: dict) -> dict:
    """Extract text from the Bedrock response and parse as JSON."""
    content_blocks = response_body.get("content", [])
    raw_text = ""
    for block in content_blocks:
        if block.get("type") == "text":
            raw_text += block.get("text", "")

    raw_text = raw_text.strip()

    # Strip markdown code fences if the model added them
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


# ── Lambda handler ────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Main Lambda entry point.
    Accepts claim data directly or fetches from DynamoDB by ClaimID.
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    # ── Parse event body ──────────────────────────────────────────────────
    if "body" in event:
        try:
            payload = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            return _response(400, {"error": "Invalid JSON body."})
    else:
        payload = event

    # ── Resolve claim data ────────────────────────────────────────────────
    claim = payload.get("claim")
    claim_id = (
        payload.get("claimId")
        or (event.get("pathParameters") or {}).get("claimId")
    )

    if not claim and claim_id:
        logger.info("Fetching claim %s from DynamoDB", claim_id)
        claim = fetch_claim_from_dynamo(claim_id)
        if not claim:
            return _response(404, {"error": f"Claim '{claim_id}' not found in DynamoDB."})

    if not claim:
        return _response(400, {"error": "Provide either 'claim' object or 'claimId' in the request body."})

    # ── Build prompt & call Bedrock ───────────────────────────────────────
    prompt = build_prompt(claim)

    try:
        response_body = invoke_bedrock(prompt)
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        logger.error("Bedrock invocation error [%s]: %s", error_code, exc)

        if error_code == "AccessDeniedException":
            return _response(403, {"error": "Bedrock access denied. Check IAM permissions and model access."})
        if error_code == "ValidationException":
            return _response(400, {"error": f"Bedrock validation error: {str(exc)}"})
        return _response(500, {"error": "Failed to invoke Bedrock model."})

    # ── Parse model response ──────────────────────────────────────────────
    try:
        analysis = parse_model_response(response_body)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.error("Failed to parse model response: %s", exc)
        return _response(502, {
            "error": "Model returned an unexpected format.",
            "rawResponse": str(response_body)
        })

    # ── Usage stats ───────────────────────────────────────────────────────
    usage = response_body.get("usage", {})

    logger.info("Analysis complete for ClaimID: %s | Risk: %s | Action: %s",
                claim.get("ClaimID", "N/A"),
                analysis.get("riskLevel"),
                analysis.get("recommendedAction"))

    return _response(200, {
        "ClaimID":      claim.get("ClaimID", "N/A"),
        "analysis":     analysis,
        "model":        MODEL_ID,
        "inputTokens":  usage.get("input_tokens", 0),
        "outputTokens": usage.get("output_tokens", 0),
    })

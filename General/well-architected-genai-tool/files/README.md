# Well-Architected Automated Review Platform — CDK Python

Automated platform that combines **AWS Config**, **Well-Architected Tool**, and **Bedrock Multi-Agent Collaboration** to perform Well-Architected reviews based on resource tags.

## Project Structure

```
war_platform/
├── app.py                          # CDK App entrypoint
├── war_stack.py                    # Main stack — composes all constructs
├── cdk.json                        # CDK configuration
├── requirements.txt
│
├── constructs/                     # One file per AWS service
│   ├── __init__.py
│   ├── cognito_construct.py        # Cognito User Pool & Client
│   ├── s3_construct.py             # S3 Buckets (web, reports, knowledge base)
│   ├── cloudfront_construct.py     # CloudFront Distribution + OAI
│   ├── dynamodb_construct.py       # DynamoDB Tables (reviews, inventory)
│   ├── sqs_construct.py            # SQS Queues (review, inventory, DLQ)
│   ├── sns_construct.py            # SNS Notification Topic
│   ├── iam_construct.py            # IAM Roles (Lambda, Bedrock Agent)
│   ├── lambda_construct.py         # All Lambda Functions (5 functions)
│   ├── opensearch_construct.py     # OpenSearch Serverless Collection
│   ├── bedrock_construct.py        # Bedrock KB + Agent 1 + Agent 2 + Supervisor
│   └── apigateway_construct.py     # API Gateway REST API
│
└── lambdas/                        # Lambda function source code
    ├── orchestrator/
    ├── inventory-scanner/
    ├── wat-integration/
    ├── bedrock-orchestrator/
    └── drawio-generator/
```

## Architecture Flow

```
User → CloudFront → S3 (UI)
            ↓
       API Gateway  ←── Cognito Auth
            ↓
    Lambda Orchestrator
       ↙           ↘
  SQS Inventory   SQS Review
       ↓               ↓
  Lambda Scanner  Lambda Bedrock Orch
  (AWS Config +        ↓
   Resource Groups)  Bedrock Supervisor Agent
                     ↙            ↘
             Agent 1               Agent 2
           (Evaluator)         (Diagram Gen)
           + KB (OSS)          + Lambda DrawIO
                ↓                    ↓
           S3 Reports         S3 DrawIO Files
```

## Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Deployment

```bash
# Bootstrap (first time only)
cdk bootstrap aws://ACCOUNT_ID/us-east-1

# Deploy
cdk deploy --context account=ACCOUNT_ID --context region=us-east-1

# Preview changes
cdk diff
```

## Populating the Knowledge Base

Upload documents to the Knowledge Base S3 bucket (output: `KnowledgeBaseBucketName`):

```
s3://war-platform-kb-{ACCOUNT_ID}/
    whitepapers/          ← AWS Well-Architected whitepapers (PDF)
    best-practices/       ← Service-specific best practices
    service-guides/       ← AWS service documentation
```

Then trigger a sync from the Bedrock console or via CLI:

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>
```

## Running a Review

```bash
# POST to /reviews with:
{
  "appTag": "my-application",
  "lensAlias": "wellarchitected",   # or custom lens ARN
  "notificationEmail": "team@example.com"
}
```

The platform will:
1. Discover all resources tagged `app=my-application`
2. Pull WAT questions for the requested lens
3. Delegate evaluation to **Agent 1** (returns scored findings)
4. Delegate diagram generation to **Agent 2** (returns draw.io XML → S3)
5. Return a combined JSON report with `evaluation_report` + `diagram_s3_url`

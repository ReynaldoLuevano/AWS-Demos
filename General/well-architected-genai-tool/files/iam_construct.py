"""
iam_construct.py
AWS IAM — Roles and policies for Lambda functions and Bedrock Agents.

Requires:
    kb_bucket_arn (str) — ARN of the Knowledge Base S3 bucket (Bedrock needs read access)

Exposes:
    lambda_base_role   (iam.Role) — Execution role for Lambda functions
    bedrock_agent_role (iam.Role) — Execution role assumed by Bedrock Agents
"""

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
from constructs import Construct


class IAMConstruct(Construct):
    """Creates IAM roles for Lambda and Bedrock services."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        kb_bucket_arn: str,
    ) -> None:
        super().__init__(scope, construct_id)

        stack = cdk.Stack.of(self)

        # ── Lambda base execution role ─────────────────────────────────────
        self.lambda_base_role = iam.Role(
            self,
            "LambdaBaseRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # ── Bedrock agent execution role ───────────────────────────────────
        self.bedrock_agent_role = iam.Role(
            self,
            "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "BedrockInvokePolicy": iam.PolicyDocument(
                    statements=[
                        # Foundation model invocation
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=["*"],
                        ),
                        # Knowledge Base S3 read access
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket",
                            ],
                            resources=[
                                kb_bucket_arn,
                                f"{kb_bucket_arn}/*",
                            ],
                        ),
                        # OpenSearch Serverless access
                        iam.PolicyStatement(
                            actions=["aoss:APIAccessAll"],
                            resources=[
                                f"arn:aws:aoss:{stack.region}:{stack.account}:collection/*"
                            ],
                        ),
                    ]
                )
            },
        )

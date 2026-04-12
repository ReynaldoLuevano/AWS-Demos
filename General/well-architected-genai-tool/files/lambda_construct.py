"""
lambda_construct.py
AWS Lambda — All function definitions for the WAR platform.

Functions:
    orchestrator_fn      — Handles API Gateway requests, dispatches to SQS
    inventory_scanner_fn — Discovers resources via AWS Config + Resource Groups Tagging API
    wat_integration_fn   — Integrates with the Well-Architected Tool API
    bedrock_orch_fn      — Invokes the Bedrock Supervisor Agent (triggered by SQS)
    drawio_generator_fn  — Generates draw.io XML files and saves to S3 (Bedrock Action Group)
"""

import os
import aws_cdk as cdk
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_sns as sns
import aws_cdk.aws_sqs as sqs
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct


LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "lambdas")


class LambdaConstruct(Construct):
    """Creates all Lambda functions and wires their environment variables and permissions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        reviews_table: dynamodb.Table,
        inventory_table: dynamodb.Table,
        reports_bucket: s3.Bucket,
        notification_topic: sns.Topic,
        review_queue: sqs.Queue,
        inventory_queue: sqs.Queue,
    ) -> None:
        super().__init__(scope, construct_id)

        stack = cdk.Stack.of(self)

        # Shared environment variables injected into every function
        common_env = {
            "REVIEWS_TABLE": reviews_table.table_name,
            "INVENTORY_TABLE": inventory_table.table_name,
            "REPORTS_BUCKET": reports_bucket.bucket_name,
            "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn,
            "REGION": stack.region,
            "ACCOUNT_ID": stack.account,
        }

        # ── 1. Orchestrator ────────────────────────────────────────────────
        self.orchestrator_fn = _lambda.Function(
            self,
            "OrchestratorFn",
            function_name="war-orchestrator",
            runtime=_lambda.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(os.path.join(LAMBDA_DIR, "orchestrator")),
            timeout=cdk.Duration.minutes(5),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment={
                **common_env,
                "REVIEW_QUEUE_URL": review_queue.queue_url,
                "INVENTORY_QUEUE_URL": inventory_queue.queue_url,
            },
        )

        review_queue.grant_send_messages(self.orchestrator_fn)
        inventory_queue.grant_send_messages(self.orchestrator_fn)
        reviews_table.grant_read_write_data(self.orchestrator_fn)

        # ── 2. Inventory Scanner ───────────────────────────────────────────
        self.inventory_scanner_fn = _lambda.Function(
            self,
            "InventoryScannerFn",
            function_name="war-inventory-scanner",
            runtime=_lambda.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(os.path.join(LAMBDA_DIR, "inventory-scanner")),
            timeout=cdk.Duration.minutes(15),
            memory_size=1024,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment=common_env,
        )

        self.inventory_scanner_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "config:ListDiscoveredResources",
                    "config:GetResourceConfigHistory",
                    "config:BatchGetResourceConfig",
                    "tag:GetResources",
                    "tag:GetTagKeys",
                    "tag:GetTagValues",
                    "resourcegroupstaggingapi:GetResources",
                    "resource-groups:ListGroups",
                    "resource-groups:GetGroup",
                    "resource-groups:GetGroupQuery",
                ],
                resources=["*"],
            )
        )

        inventory_table.grant_read_write_data(self.inventory_scanner_fn)
        self.inventory_scanner_fn.add_event_source(
            SqsEventSource(inventory_queue, batch_size=10)
        )
        # Allow Bedrock Agent Action Groups to invoke this function
        self.inventory_scanner_fn.grant_invoke(
            iam.ServicePrincipal("bedrock.amazonaws.com")
        )

        # ── 3. Well-Architected Tool Integration ───────────────────────────
        self.wat_integration_fn = _lambda.Function(
            self,
            "WATIntegrationFn",
            function_name="war-wat-integration",
            runtime=_lambda.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(os.path.join(LAMBDA_DIR, "wat-integration")),
            timeout=cdk.Duration.minutes(5),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment=common_env,
        )

        self.wat_integration_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "wellarchitected:CreateWorkload",
                    "wellarchitected:GetWorkload",
                    "wellarchitected:ListWorkloads",
                    "wellarchitected:CreateMilestone",
                    "wellarchitected:GetLensReview",
                    "wellarchitected:ListLensReviewImprovements",
                    "wellarchitected:ListAnswers",
                    "wellarchitected:GetAnswer",
                    "wellarchitected:UpdateAnswer",
                    "wellarchitected:GetLensVersionDifference",
                    "wellarchitected:ListLenses",
                    "wellarchitected:AssociateLenses",
                ],
                resources=["*"],
            )
        )

        reviews_table.grant_read_write_data(self.wat_integration_fn)

        # ── 4. Bedrock Orchestrator ────────────────────────────────────────
        self.bedrock_orch_fn = _lambda.Function(
            self,
            "BedrockOrchFn",
            function_name="war-bedrock-orchestrator",
            runtime=_lambda.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(os.path.join(LAMBDA_DIR, "bedrock-orchestrator")),
            timeout=cdk.Duration.minutes(15),
            memory_size=1024,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment=common_env,
        )

        self.bedrock_orch_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                ],
                resources=["*"],
            )
        )

        self.bedrock_orch_fn.add_event_source(
            SqsEventSource(review_queue, batch_size=1)
        )
        reviews_table.grant_read_write_data(self.bedrock_orch_fn)
        reports_bucket.grant_read_write(self.bedrock_orch_fn)
        notification_topic.grant_publish(self.bedrock_orch_fn)

        # ── 5. DrawIO Generator (Bedrock Action Group) ─────────────────────
        self.drawio_generator_fn = _lambda.Function(
            self,
            "DrawioGeneratorFn",
            function_name="war-drawio-generator",
            runtime=_lambda.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(os.path.join(LAMBDA_DIR, "drawio-generator")),
            timeout=cdk.Duration.minutes(10),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment=common_env,
        )

        reports_bucket.grant_read_write(self.drawio_generator_fn)
        self.drawio_generator_fn.grant_invoke(
            iam.ServicePrincipal("bedrock.amazonaws.com")
        )

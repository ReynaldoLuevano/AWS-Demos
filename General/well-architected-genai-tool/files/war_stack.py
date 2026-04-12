"""
war_stack.py
Main CDK Stack — composes all service modules and wires their dependencies.
Each construct is defined in its own module under constructs/.
"""

import aws_cdk as cdk
from constructs import Construct

from constructs.cognito_construct import CognitoConstruct
from constructs.s3_construct import S3Construct
from constructs.cloudfront_construct import CloudFrontConstruct
from constructs.dynamodb_construct import DynamoDBConstruct
from constructs.sqs_construct import SQSConstruct
from constructs.sns_construct import SNSConstruct
from constructs.iam_construct import IAMConstruct
from constructs.lambda_construct import LambdaConstruct
from constructs.opensearch_construct import OpenSearchConstruct
from constructs.bedrock_construct import BedrockConstruct
from constructs.apigateway_construct import APIGatewayConstruct


class WellArchitectedReviewStack(cdk.Stack):
    """
    Main stack for the Well-Architected Automated Review Platform.

    Dependency order:
        Cognito → S3 → CloudFront
        DynamoDB → SQS → SNS
        IAM (depends on S3 for KB bucket ARN)
        Lambda (depends on DynamoDB, SQS, SNS, IAM)
        OpenSearch (depends on IAM)
        Bedrock (depends on OpenSearch, S3, Lambda, IAM)
        APIGateway (depends on Lambda, Cognito, CloudFront)
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. Authentication ──────────────────────────────────────────────
        cognito = CognitoConstruct(self, "Cognito")

        # ── 2. Storage buckets ─────────────────────────────────────────────
        s3 = S3Construct(self, "S3")

        # ── 3. CDN / Frontend ──────────────────────────────────────────────
        cloudfront = CloudFrontConstruct(self, "CloudFront", web_bucket=s3.web_bucket)

        # ── 4. Database ────────────────────────────────────────────────────
        dynamodb = DynamoDBConstruct(self, "DynamoDB")

        # ── 5. Async queuing ───────────────────────────────────────────────
        sqs = SQSConstruct(self, "SQS")

        # ── 6. Notifications ───────────────────────────────────────────────
        sns = SNSConstruct(self, "SNS")

        # ── 7. IAM roles & policies ────────────────────────────────────────
        iam = IAMConstruct(
            self,
            "IAM",
            kb_bucket_arn=s3.knowledge_base_bucket.bucket_arn,
        )

        # ── 8. Lambda functions ────────────────────────────────────────────
        lambdas = LambdaConstruct(
            self,
            "Lambda",
            reviews_table=dynamodb.reviews_table,
            inventory_table=dynamodb.inventory_table,
            reports_bucket=s3.reports_bucket,
            notification_topic=sns.notification_topic,
            review_queue=sqs.review_queue,
            inventory_queue=sqs.inventory_queue,
        )

        # ── 9. OpenSearch Serverless (vector store) ────────────────────────
        opensearch = OpenSearchConstruct(
            self,
            "OpenSearch",
            bedrock_agent_role_arn=iam.bedrock_agent_role.role_arn,
        )

        # ── 10. Bedrock Knowledge Base + Agents ────────────────────────────
        bedrock = BedrockConstruct(
            self,
            "Bedrock",
            bedrock_agent_role=iam.bedrock_agent_role,
            oss_collection_arn=opensearch.collection.attr_arn,
            kb_bucket=s3.knowledge_base_bucket,
            reports_bucket=s3.reports_bucket,
            reviews_table=dynamodb.reviews_table,
            inventory_scanner_fn=lambdas.inventory_scanner_fn,
            drawio_generator_fn=lambdas.drawio_generator_fn,
            bedrock_orch_fn=lambdas.bedrock_orch_fn,
            review_queue=sqs.review_queue,
        )

        # ── 11. API Gateway ────────────────────────────────────────────────
        APIGatewayConstruct(
            self,
            "APIGateway",
            orchestrator_fn=lambdas.orchestrator_fn,
            wat_integration_fn=lambdas.wat_integration_fn,
            user_pool=cognito.user_pool,
            distribution_domain=cloudfront.distribution.distribution_domain_name,
        )

        # ── Outputs ────────────────────────────────────────────────────────
        cdk.CfnOutput(self, "CloudFrontURL",
                      value=f"https://{cloudfront.distribution.distribution_domain_name}",
                      description="CloudFront Distribution URL")

        cdk.CfnOutput(self, "WebBucketName",
                      value=s3.web_bucket.bucket_name,
                      description="S3 Bucket for web assets")

        cdk.CfnOutput(self, "ReportsBucketName",
                      value=s3.reports_bucket.bucket_name,
                      description="S3 Bucket for generated reports and diagrams")

        cdk.CfnOutput(self, "KnowledgeBaseBucketName",
                      value=s3.knowledge_base_bucket.bucket_name,
                      description="Upload whitepapers and best practices docs here")

        cdk.CfnOutput(self, "UserPoolId",
                      value=cognito.user_pool.user_pool_id,
                      description="Cognito User Pool ID")

        cdk.CfnOutput(self, "UserPoolClientId",
                      value=cognito.user_pool_client.user_pool_client_id,
                      description="Cognito User Pool Client ID")

        cdk.CfnOutput(self, "SupervisorAgentId",
                      value=bedrock.supervisor_agent.attr_agent_id,
                      description="Bedrock Supervisor Agent ID")

"""
s3_construct.py
Amazon S3 — Three buckets for the WAR platform.

Exposes:
    web_bucket            — Static frontend assets served via CloudFront
    reports_bucket        — Generated review reports and draw.io diagrams
    knowledge_base_bucket — Best practices docs ingested into Bedrock KB
"""

import aws_cdk as cdk
import aws_cdk.aws_s3 as s3
from constructs import Construct


class S3Construct(Construct):
    """Creates all S3 buckets needed by the WAR platform."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        stack = cdk.Stack.of(self)

        # ── Frontend static website ────────────────────────────────────────
        self.web_bucket = s3.Bucket(
            self,
            "WebBucket",
            bucket_name=f"war-platform-web-{stack.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ── Reports & diagrams output ──────────────────────────────────────
        self.reports_bucket = s3.Bucket(
            self,
            "ReportsBucket",
            bucket_name=f"war-platform-reports-{stack.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=cdk.Duration.days(365),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=cdk.Duration.days(30),
                        )
                    ],
                )
            ],
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ── Knowledge Base documents ───────────────────────────────────────
        self.knowledge_base_bucket = s3.Bucket(
            self,
            "KnowledgeBaseBucket",
            bucket_name=f"war-platform-kb-{stack.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

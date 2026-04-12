"""
dynamodb_construct.py
Amazon DynamoDB — State management tables for the WAR platform.

Exposes:
    reviews_table   — Stores review sessions and results (PK: reviewId, SK: timestamp)
    inventory_table — Stores discovered resources by account and tag (PK: accountId, SK: resourceArn)
"""

import aws_cdk as cdk
import aws_cdk.aws_dynamodb as dynamodb
from constructs import Construct


class DynamoDBConstruct(Construct):
    """Creates DynamoDB tables for reviews state and resource inventory."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        # ── Reviews table ──────────────────────────────────────────────────
        self.reviews_table = dynamodb.Table(
            self,
            "ReviewsTable",
            table_name="war-reviews",
            partition_key=dynamodb.Attribute(
                name="reviewId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.reviews_table.add_global_secondary_index(
            index_name="appTag-index",
            partition_key=dynamodb.Attribute(
                name="appTag",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # ── Inventory table ────────────────────────────────────────────────
        self.inventory_table = dynamodb.Table(
            self,
            "InventoryTable",
            table_name="war-inventory",
            partition_key=dynamodb.Attribute(
                name="accountId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="resourceArn",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.inventory_table.add_global_secondary_index(
            index_name="appTag-index",
            partition_key=dynamodb.Attribute(
                name="appTag",
                type=dynamodb.AttributeType.STRING,
            ),
        )

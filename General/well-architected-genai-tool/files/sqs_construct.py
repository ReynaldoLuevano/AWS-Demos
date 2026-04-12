"""
sqs_construct.py
Amazon SQS — Async job queues for review and inventory workflows.

Exposes:
    dead_letter_queue — DLQ for failed messages (14-day retention)
    review_queue      — Queue for WAR review jobs (triggers Bedrock orchestrator Lambda)
    inventory_queue   — Queue for inventory scan jobs (triggers inventory scanner Lambda)
"""

import aws_cdk as cdk
import aws_cdk.aws_sqs as sqs
from constructs import Construct


class SQSConstruct(Construct):
    """Creates SQS queues for decoupled async processing."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        # ── Dead-letter queue ──────────────────────────────────────────────
        self.dead_letter_queue = sqs.Queue(
            self,
            "DLQ",
            queue_name="war-dlq",
            retention_period=cdk.Duration.days(14),
        )

        dlq_opts = sqs.DeadLetterQueue(
            queue=self.dead_letter_queue,
            max_receive_count=3,
        )

        # ── Review queue ───────────────────────────────────────────────────
        self.review_queue = sqs.Queue(
            self,
            "ReviewQueue",
            queue_name="war-review-queue",
            visibility_timeout=cdk.Duration.minutes(15),
            dead_letter_queue=dlq_opts,
            encryption=sqs.QueueEncryption.KMS_MANAGED,
        )

        # ── Inventory queue ────────────────────────────────────────────────
        self.inventory_queue = sqs.Queue(
            self,
            "InventoryQueue",
            queue_name="war-inventory-queue",
            visibility_timeout=cdk.Duration.minutes(10),
            dead_letter_queue=dlq_opts,
        )

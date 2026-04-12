"""
sns_construct.py
Amazon SNS — Notification topic for review completion events.

Exposes:
    notification_topic (sns.Topic) — Publishes review result notifications
"""

import aws_cdk.aws_sns as sns
from constructs import Construct


class SNSConstruct(Construct):
    """Creates SNS topic for review result notifications."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        self.notification_topic = sns.Topic(
            self,
            "NotificationTopic",
            topic_name="war-notifications",
            display_name="Well-Architected Review Notifications",
        )

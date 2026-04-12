#!/usr/bin/env python3
"""
Well-Architected Automated Review Platform
CDK App entrypoint — composes all modular constructs into the main stack.
"""

import aws_cdk as cdk
from war_stack import WellArchitectedReviewStack

app = cdk.App()

WellArchitectedReviewStack(
    app,
    "WellArchitectedReviewStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
    description="Well-Architected Automated Review Platform with Bedrock Agents",
    tags={
        "Project": "WellArchitectedReview",
        "Environment": "Production",
        "ManagedBy": "CDK",
    },
)

app.synth()

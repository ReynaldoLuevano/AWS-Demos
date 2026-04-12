"""
opensearch_construct.py
Amazon OpenSearch Serverless — Vector store backend for the Bedrock Knowledge Base.

Creates:
  - Encryption security policy   (AWS-owned KMS key)
  - Network security policy      (VPC-only, no public access)
  - Data access policy           (grants Bedrock Agent role full index access)
  - VECTORSEARCH collection      (war-kb-collection)

Requires:
    bedrock_agent_role_arn (str) — Role ARN that Bedrock uses to read/write vectors

Exposes:
    collection (CfnCollection) — use .attr_arn for downstream Bedrock KB config
"""

import json
import aws_cdk.aws_opensearchserverless as aoss
from constructs import Construct


class OpenSearchConstruct(Construct):
    """Creates OpenSearch Serverless collection for Bedrock vector embeddings."""

    COLLECTION_NAME = "war-kb-collection"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bedrock_agent_role_arn: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # ── Encryption policy (AWS-owned KMS) ──────────────────────────────
        encryption_policy = aoss.CfnSecurityPolicy(
            self,
            "EncryptionPolicy",
            name="war-kb-encryption",
            type="encryption",
            policy=json.dumps(
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{self.COLLECTION_NAME}"],
                        }
                    ],
                    "AWSOwnedKey": True,
                }
            ),
        )

        # ── Network policy (no public access) ──────────────────────────────
        network_policy = aoss.CfnSecurityPolicy(
            self,
            "NetworkPolicy",
            name="war-kb-network",
            type="network",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{self.COLLECTION_NAME}"],
                            },
                            {
                                "ResourceType": "dashboard",
                                "Resource": [f"collection/{self.COLLECTION_NAME}"],
                            },
                        ],
                        "AllowFromPublic": False,
                    }
                ]
            ),
        )

        # ── Data access policy (Bedrock agent role) ────────────────────────
        data_access_policy = aoss.CfnAccessPolicy(
            self,
            "DataAccessPolicy",
            name="war-kb-data-access",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{self.COLLECTION_NAME}"],
                                "Permission": [
                                    "aoss:CreateCollectionItems",
                                    "aoss:DeleteCollectionItems",
                                    "aoss:UpdateCollectionItems",
                                    "aoss:DescribeCollectionItems",
                                ],
                            },
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/{self.COLLECTION_NAME}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DeleteIndex",
                                    "aoss:UpdateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:ReadDocument",
                                    "aoss:WriteDocument",
                                ],
                            },
                        ],
                        "Principal": [bedrock_agent_role_arn],
                    }
                ]
            ),
        )

        # ── Vector search collection ───────────────────────────────────────
        self.collection = aoss.CfnCollection(
            self,
            "KBCollection",
            name=self.COLLECTION_NAME,
            type="VECTORSEARCH",
            description="Vector store for Well-Architected best practices KB",
        )

        # Policies must exist before the collection is created
        self.collection.add_dependency(encryption_policy)
        self.collection.add_dependency(network_policy)
        self.collection.add_dependency(data_access_policy)

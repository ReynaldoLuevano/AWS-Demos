"""
cloudfront_construct.py
Amazon CloudFront — CDN distribution for the WAR platform web UI.

Requires:
    web_bucket (s3.Bucket) — origin bucket with static frontend assets

Exposes:
    distribution (cloudfront.Distribution)
    oai          (cloudfront.OriginAccessIdentity)
"""

import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
import aws_cdk.aws_s3 as s3
from constructs import Construct


class CloudFrontConstruct(Construct):
    """Creates a CloudFront distribution backed by the S3 web bucket."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        web_bucket: s3.Bucket,
    ) -> None:
        super().__init__(scope, construct_id)

        self.oai = cloudfront.OriginAccessIdentity(self, "OAI")
        web_bucket.grant_read(self.oai)

        self.distribution = cloudfront.Distribution(
            self,
            "WARDistribution",
            comment="Well-Architected Review Platform",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    web_bucket,
                    origin_access_identity=self.oai,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )

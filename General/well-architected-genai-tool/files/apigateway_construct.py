"""
apigateway_construct.py
Amazon API Gateway — REST API for the WAR platform.

Endpoints:
    POST /reviews              — Start a new Well-Architected review
    GET  /reviews/{reviewId}   — Retrieve review status and results
    GET  /inventory            — List resources by appTag query parameter
    GET  /lenses               — List available Well-Architected lenses

All endpoints except GET /lenses are protected by Cognito.

Requires:
    orchestrator_fn      (lambda.Function)  — Handles /reviews and /inventory routes
    wat_integration_fn   (lambda.Function)  — Handles /lenses route
    user_pool            (cognito.UserPool)  — Cognito pool for JWT authorisation
    distribution_domain  (str)              — CloudFront domain for CORS allow-origin
"""

import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_cognito as cognito
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_logs as logs
from constructs import Construct


class APIGatewayConstruct(Construct):
    """Creates the REST API and wires Lambda integrations with Cognito authorisation."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        orchestrator_fn: _lambda.Function,
        wat_integration_fn: _lambda.Function,
        user_pool: cognito.UserPool,
        distribution_domain: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # ── Access log group ───────────────────────────────────────────────
        log_group = logs.LogGroup(
            self,
            "APIGWLogGroup",
            log_group_name="/aws/apigateway/war-platform",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # ── REST API ───────────────────────────────────────────────────────
        self.api = apigw.RestApi(
            self,
            "WARApi",
            rest_api_name="war-platform-api",
            description="Well-Architected Review Platform API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=[f"https://{distribution_domain}"],
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date"],
            ),
            deploy_options=apigw.StageOptions(
                stage_name="v1",
                access_log_destination=apigw.LogGroupLogDestination(log_group),
                access_log_format=apigw.AccessLogFormat.json_with_standard_fields(),
                tracing_enabled=True,
                logging_level=apigw.MethodLoggingLevel.INFO,
            ),
        )

        # ── Cognito authoriser (shared across protected routes) ────────────
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        auth_opts = apigw.MethodOptions(
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # ── Lambda integrations ────────────────────────────────────────────
        orchestrator_integration = apigw.LambdaIntegration(orchestrator_fn)
        wat_integration = apigw.LambdaIntegration(wat_integration_fn)

        # ── /reviews ───────────────────────────────────────────────────────
        reviews_resource = self.api.root.add_resource("reviews")
        reviews_resource.add_method("POST", orchestrator_integration, auth_opts)

        # /reviews/{reviewId}
        review_resource = reviews_resource.add_resource("{reviewId}")
        review_resource.add_method("GET", orchestrator_integration, auth_opts)

        # ── /inventory ─────────────────────────────────────────────────────
        inventory_resource = self.api.root.add_resource("inventory")
        inventory_resource.add_method("GET", orchestrator_integration, auth_opts)

        # ── /lenses (public — no auth required) ───────────────────────────
        lenses_resource = self.api.root.add_resource("lenses")
        lenses_resource.add_method("GET", wat_integration)

        # ── Output ─────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "APIEndpoint",
            value=self.api.url,
            description="API Gateway Endpoint URL",
        )

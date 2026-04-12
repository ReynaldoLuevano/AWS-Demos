"""
cognito_construct.py
Amazon Cognito — User authentication for the WAR platform portal.

Exposes:
    user_pool        (cognito.UserPool)
    user_pool_client (cognito.UserPoolClient)
"""

import aws_cdk as cdk
import aws_cdk.aws_cognito as cognito
from constructs import Construct


class CognitoConstruct(Construct):
    """Creates a Cognito User Pool with secure password policy and email sign-in."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        self.user_pool = cognito.UserPool(
            self,
            "WARUserPool",
            user_pool_name="war-platform-users",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.user_pool_client = cognito.UserPoolClient(
            self,
            "WARUserPoolClient",
            user_pool=self.user_pool,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
        )

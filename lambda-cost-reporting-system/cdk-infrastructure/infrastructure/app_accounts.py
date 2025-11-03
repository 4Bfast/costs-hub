#!/usr/bin/env python3
"""
CDK App for Accounts Table deployment
"""

import aws_cdk as cdk
from stacks.accounts_table_stack import AccountsTableStack

app = cdk.App()

# Deploy accounts table
AccountsTableStack(
    app, 
    "costhub-accounts-table-prod",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth()

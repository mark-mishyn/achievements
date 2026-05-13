import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
app = LambdaFunctionUrlResolver()

_ssm = boto3.client("ssm")
_API_KEY = _ssm.get_parameter(Name=os.environ["API_KEY_PARAM"], WithDecryption=True)["Parameter"]["Value"]


@app.get("/achievements")
@tracer.capture_method
def list_achievements():
    logger.info("Listing achievements")
    return {"achievements": []}


@app.get("/achievements/<achievement_id>")
@tracer.capture_method
def get_achievement(achievement_id: str):
    logger.info("Fetching achievement", extra={"achievement_id": achievement_id})
    return {"achievement": None}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    headers = event.get("headers") or {}
    if headers.get("x-api-key") != _API_KEY:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Unauthorized"}),
        }
    return app.resolve(event, context)

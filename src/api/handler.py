from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

# Logger emits structured JSON instead of plain text, making logs queryable in CloudWatch.
logger = Logger()

# Tracer wraps AWS X-Ray so you get flame graphs of your Lambda invocations for free.
# Set POWERTOOLS_TRACE_DISABLED=true locally if you don't have X-Ray configured.
tracer = Tracer()

# LambdaFunctionUrlResolver handles requests coming directly from a Lambda Function URL
app = LambdaFunctionUrlResolver()


# Registers this function as the handler for GET /api.
# The return value is automatically serialized to JSON and wrapped in a 200 response.
@app.get("/achievements")
# Wraps this function in an X-Ray subsegment so it shows up as a separate span in traces.
@tracer.capture_method
def list_achievements():
    logger.info("Listing api")
    return {"api": []}


# app.get can be any HTTP method: @app.post, @app.put, @app.delete, @app.patch
# The path parameter <achievement_id> is passed as a function argument automatically.
@app.get("/achievements/<achievement_id>")
@tracer.capture_method
def get_achievement(achievement_id: str):
    logger.info("Fetching achievement", extra={"achievement_id": achievement_id})
    return {"achievement": None}


# inject_lambda_context adds request ID, function name, cold start flag, etc. to every log line emitted
@logger.inject_lambda_context
# capture_lambda_handler creates the root X-Ray segment for the whole invocation and
# records the event/response (redacted by default) for debugging.
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    # Passes the incoming request to the app, which finds and calls the right endpoint
    # function based on the URL path, then returns an HTTP response
    return app.resolve(event, context)

# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.13, managed with [uv](https://docs.astral.sh/uv/)
- Dependencies declared in `pyproject.toml`; lockfile is `uv.lock`

## Commands

```bash
# Install dependencies
uv sync

# Run the project
uv run python <script.py>

# Add a dependency
uv add <package>
```

## Deployment

The project uses [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/) for infrastructure definition and deployment. The SAM template (`template.yaml`) defines:
- A Lambda function (`ApiFunction`) exposed via a Function URL (no auth)
- An S3 bucket (`AchievementsBucket`) for storage, with the ARN passed to Lambda via `BUCKET_NAME` env var
- An IAM role with S3 and X-Ray permissions

## Architecture

The API is built on AWS Lambda functions using [AWS Lambda Powertools for Python](https://docs.powertools.aws.dev/lambda/python/). Powertools provides utilities for routing (API Gateway event handling), logging, tracing, and metrics.

## Dependencies
- `boto3` — AWS SDK; the project interacts with AWS services
- `aws-lambda-powertools` — Lambda utilities for API routing, logging, tracing, and metrics

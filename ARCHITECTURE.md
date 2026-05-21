# Architecture

The project follows a simple layered structure with four main blocks.

## 1. API Handlers (`src/api/`)

Lambda functions built with [AWS Lambda Powertools for Python](https://docs.powertools.aws.dev/lambda/python/).
Powertools provides request routing (API Gateway / Function URL event handling), structured logging, X-Ray tracing, and metrics.

Entry point: `src/api/handler.py` → `handler()`

## 2. Database (`src/db/`)

DynamoDB is the primary datastore. Table definitions and access helpers live in `src/db/`.

## 3. Front-end (`src/frontend/`)

Static HTML/Vue files co-located in the repo. Served as static assets (e.g. S3 + CloudFront). Communicates with the API exclusively via HTTP from the browser — no shared Python code.

## 4. Infrastructure (`template.yaml`)

AWS SAM template defining all cloud resources:

| Resource | Type | Purpose |
|---|---|---|
| `ApiFunction` | `AWS::Serverless::Function` | Lambda handler exposed via Function URL |
| `AchievementsBucket` | `AWS::S3::Bucket` | Object storage |
| `LambdaExecutionRole` | `AWS::IAM::Role` | Permissions: S3, X-Ray, SSM (API key) |

Deploy with `sam build && sam deploy`. Config lives in `samconfig.toml` (region: `eu-central-1`).

## Dependency Rules

```
Frontend  ──HTTP──►  API Handlers  ──►  DB
                         │
                         └──────────►  Infrastructure (env vars only)
```

- **Frontend → API**: browser-side HTTP calls only (`fetch`/`axios`). `src/frontend/` contains only HTML/Vue/JS — no Python imports.
- **API → DB**: the only layer allowed to import from `src/db/`. Handlers call DB helpers; DB helpers never import from `src/api/`.
- **DB → (nothing)**: `src/db/` has no dependencies on other `src/` layers — only `boto3` and stdlib.
- **Infrastructure → (nothing)**: `template.yaml` is pure config; code reads infra values via environment variables only.

**Forbidden:**
- `src/db/` importing from `src/api/`
- Circular imports between any Python layers

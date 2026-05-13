# Achievements

## Setup

### TODO: AWS one-time setup (requires AWS account)

Before deploying, create the API key in SSM Parameter Store:

```bash
aws ssm put-parameter \
  --name /achievements/api-key \
  --value "your-secret-key-here" \
  --type SecureString
```

Then deploy with SAM:

```bash
sam build
sam deploy --guided
```

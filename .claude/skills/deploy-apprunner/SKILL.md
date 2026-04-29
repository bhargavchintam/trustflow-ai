---
name: deploy-apprunner
description: Build the container, push to ECR, deploy to App Runner, smoke-test the result. Use when the user says "deploy", "ship", or "push to prod".
---

# deploy-apprunner

End-to-end deploy from local working tree to running App Runner URL.

## Pre-flight (fail fast)

Verify required env vars are set:
- `AWS_REGION`
- `AWS_ACCOUNT_ID`
- `ECR_REPO` (default: `trustflow-ai`)
- `APPRUNNER_SERVICE_ARN`
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY` or `OPENAI_API_KEY`
- `DATABASE_URL`

Verify:
- `aws sts get-caller-identity` returns the expected account
- `docker info` returns a running daemon

If anything is missing, stop and tell the user what to set.

## Steps

1. **Build image** (must be linux/amd64 for App Runner on x86 compute).
   `NEXT_PUBLIC_*` env vars MUST be passed as build args because Next.js inlines them
   into the JS bundle at build time — App Runner runtime env vars don't reach the
   already-built static bundle.
   ```
   set -a; source .env; source frontend/.env.local; set +a
   docker build --platform linux/amd64 \
     --build-arg NEXT_PUBLIC_SUPABASE_URL="$NEXT_PUBLIC_SUPABASE_URL" \
     --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY="$NEXT_PUBLIC_SUPABASE_ANON_KEY" \
     --build-arg NEXT_PUBLIC_API_BASE="" \
     -t trustflow-ai:latest .
   ```
   `NEXT_PUBLIC_API_BASE=""` is intentional: same-origin in production, the bundle
   talks to `/api/*` on whatever URL it's served from.

2. **ECR login:**
   ```
   aws ecr get-login-password --region $AWS_REGION | \
     docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
   ```

3. **Tag and push:**
   ```
   docker tag trustflow-ai:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
   docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
   ```

4. **Trigger App Runner deploy:**
   ```
   aws apprunner start-deployment --service-arn $APPRUNNER_SERVICE_ARN
   ```

5. **Poll until status RUNNING** (every 10s, give up after 8 minutes):
   ```
   aws apprunner describe-service --service-arn $APPRUNNER_SERVICE_ARN \
     --query 'Service.Status' --output text
   ```

6. **Get the service URL:**
   ```
   aws apprunner describe-service --service-arn $APPRUNNER_SERVICE_ARN \
     --query 'Service.ServiceUrl' --output text
   ```

7. **Health check:** hit `/healthz` and verify all components healthy.

8. **Run the `smoke-test` skill** against the deployed URL.

9. **Print the final URL.**

## Failure modes

- **ECR push 401:** re-run step 2 (login token expires after 12h).
- **App Runner stuck in OPERATION_IN_PROGRESS:** another deploy is still running. Wait it out or cancel it via the console.
- **Health check fails:** check CloudWatch logs:
  ```
  aws logs tail /aws/apprunner/$SERVICE_NAME/<arn-suffix>/application --since 5m --follow
  ```
- **Smoke-test fails on deployed URL but passes locally:** likely env var mismatch (DATABASE_URL points elsewhere, secrets not loaded). Check App Runner config.

## Notes

- **Always `--platform linux/amd64`** when building on Apple Silicon. Default `arm64` images won't run on App Runner's x86 compute.
- **App Runner cold start ~30s** on first hit after a deploy. Run the smoke-test twice — first hit warms it.

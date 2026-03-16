#!/bin/bash
set -euo pipefail

VERSION="${1:-v1}"
S3_BUCKET="medicalnote-widget-cdn"
DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:?Missing CLOUDFRONT_DISTRIBUTION_ID env var}"

echo "==> Building widget..."
cd "$(dirname "$0")/.."
npm run build

echo "==> Checking bundle size..."
BUNDLE_SIZE=$(gzip -c dist/widget.js | wc -c | tr -d '[:space:]')
MAX_SIZE=51200
if [ "$BUNDLE_SIZE" -gt "$MAX_SIZE" ]; then
  echo "ERROR: Bundle size ${BUNDLE_SIZE} bytes exceeds ${MAX_SIZE} bytes (50KB gzipped)"
  exit 1
fi
echo "    Bundle size: ${BUNDLE_SIZE} bytes gzipped (limit: ${MAX_SIZE})"

echo "==> Deploying to S3: s3://${S3_BUCKET}/${VERSION}/"
aws s3 cp dist/widget.js "s3://${S3_BUCKET}/${VERSION}/widget.js" \
  --content-type "application/javascript" \
  --cache-control "public, max-age=31536000, immutable" \
  --metadata-directive REPLACE

aws s3 cp dist/widget.js.map "s3://${S3_BUCKET}/${VERSION}/widget.js.map" \
  --content-type "application/json" \
  --cache-control "public, max-age=31536000, immutable" \
  --metadata-directive REPLACE

echo "==> Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/${VERSION}/*"

echo "==> Deployed widget ${VERSION} successfully!"
echo "    URL: https://widget.medicalnote.app/${VERSION}/widget.js"

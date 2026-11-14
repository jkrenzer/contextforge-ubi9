#!/usr/bin/env bash
set -euo pipefail
context="${1:-upstream}"
image="${2:-contextforge-ubi9:local}"
test -f "$context/Containerfile"
# Fail explicitly if upstream removes the documented customization points.
for arg in UBI_BASE NODEJS_IMAGE UBI_MINIMAL; do
  grep -q "^ARG $arg=" "$context/Containerfile" || { echo "Missing upstream build arg: $arg" >&2; exit 1; }
done
revision="$(git -C "$context" rev-parse HEAD)"
docker buildx build --platform linux/amd64 --load --pull \
  --build-arg UBI_BASE=registry.access.redhat.com/ubi9/ubi:latest \
  --build-arg NODEJS_IMAGE=registry.access.redhat.com/ubi9/nodejs-24:latest \
  --build-arg UBI_MINIMAL=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --build-arg WHEELS_REF=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg MCPGATEWAY_UI_ENABLED=true \
  --build-arg ENABLE_FIPS=false \
  --label "org.opencontainers.image.source=https://github.com/jkrenzer/contextforge-ubi9" \
  --label "org.opencontainers.image.version=${RELEASE:-local}-ubi9" \
  --label "org.opencontainers.image.revision=$revision" \
  --label "io.contextforge.upstream=https://github.com/IBM/mcp-context-forge" \
  --label "io.contextforge.base=ubi9" \
  -f "$context/Containerfile" -t "$image" "$context"

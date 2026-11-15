#!/usr/bin/env bash
# Downloads a pinned MCP Toolbox for Databases binary into ./bin (gitignored).
set -euo pipefail
VERSION="${TOOLBOX_VERSION:-1.17.0}"
case "$(uname -s)/$(uname -m)" in
  Darwin/arm64) PLATFORM=darwin/arm64 ;;
  Darwin/x86_64) PLATFORM=darwin/amd64 ;;
  Linux/x86_64) PLATFORM=linux/amd64 ;;
  *) echo "Unsupported platform; see https://github.com/googleapis/mcp-toolbox" >&2; exit 1 ;;
esac
cd "$(dirname "$0")/.."
mkdir -p bin
URL="https://storage.googleapis.com/mcp-toolbox-for-databases/v${VERSION}/${PLATFORM}/toolbox"
# ~165 MB: resume on flaky connections, then verify against the MD5 that GCS publishes.
curl -fsS -C - --retry 5 --retry-all-errors -o bin/toolbox "$URL"
want="$(curl -fsSI "$URL" | tr -d '\r' | sed -n 's/^x-goog-hash: md5=//p')"
got="$(openssl md5 -binary bin/toolbox | base64)"
[[ "$want" == "$got" ]] || { echo "Checksum mismatch (want $want, got $got); delete bin/toolbox and retry." >&2; exit 1; }
chmod +x bin/toolbox
bin/toolbox --version

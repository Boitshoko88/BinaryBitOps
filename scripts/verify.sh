#!/usr/bin/env sh
# Reproducible local verification for the WBS 3.10 demonstrator (Linux/macOS/CI).
# Proves the repository state only; not HDE pipeline, registry, Argo CD or owner
# acceptance evidence.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT="$ROOT/evidence/local/local-verification.md"
RENDERED="${TMPDIR:-/tmp}/binarybitops-rendered.yaml"
PORT="${PORT:-18080}"
mkdir -p "$ROOT/evidence/local"

PASSED=0
FAILED=0
SKIPPED=0
STATUS_LINES=""

record() {
  name=$1
  state=$2
  detail=${3:-}
  STATUS_LINES="${STATUS_LINES}| ${name} | ${state} | ${detail} |
"
  case "$state" in
    PASS) PASSED=$((PASSED + 1)) ;;
    SKIP) SKIPPED=$((SKIPPED + 1)) ;;
    *) FAILED=$((FAILED + 1)) ;;
  esac
}

{
  echo "# WBS 3.10 local verification"
  echo
  echo "- Timestamp (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Host: $(hostname)"
  echo "- Branch: $(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "- Commit: $(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "- Python: $(python3 --version 2>&1)"
  echo "- kubectl: $(kubectl version --client 2>/dev/null | head -n 1)"
  echo
  echo "> Local repository evidence only. It does not prove an approved PR, Tekton"
  echo "> run, registry digest, Argo CD sync, Vault cluster injection or owner sign-off."
  echo
} > "$OUT"

echo "== Tests =="
if python3 -m unittest discover -s "$ROOT/tests" -t "$ROOT" -v 2>&1 | tee "${TMPDIR:-/tmp}/bbops-tests.txt"; then
  record "Unit, HTTP, secret and manifest tests" PASS "all tests passed"
else
  record "Unit, HTTP, secret and manifest tests" FAIL "test failure"
fi
{
  echo "## Test suite"
  echo '```text'
  cat "${TMPDIR:-/tmp}/bbops-tests.txt"
  echo '```'
  echo
} >> "$OUT"

echo "== CLI =="
if python3 "$ROOT/binarybitops.py" | tee "${TMPDIR:-/tmp}/bbops-cli.txt" | grep -q "GitHub authoritative repository"; then
  record "CLI model view" PASS ""
else
  record "CLI model view" FAIL "unexpected output"
fi
{
  echo "## CLI output"
  echo '```text'
  cat "${TMPDIR:-/tmp}/bbops-cli.txt"
  echo '```'
  echo
} >> "$OUT"

echo "== Manifests =="
if kubectl kustomize "$ROOT/deploy/overlays/nonprod" > "$RENDERED"; then
  record "Render non-production overlay" PASS ""
  if command -v kubeconform >/dev/null 2>&1; then
    if kubeconform -strict -summary -ignore-missing-schemas "$RENDERED" > "${TMPDIR:-/tmp}/bbops-schema.txt" 2>&1; then
      record "Kubernetes schema validation" PASS ""
    else
      record "Kubernetes schema validation" FAIL "see report"
    fi
  elif [ -x "$ROOT/tools/kubeconform" ]; then
    if "$ROOT/tools/kubeconform" -strict -summary -ignore-missing-schemas "$RENDERED" > "${TMPDIR:-/tmp}/bbops-schema.txt" 2>&1; then
      record "Kubernetes schema validation" PASS ""
    else
      record "Kubernetes schema validation" FAIL "see report"
    fi
  else
    record "Kubernetes schema validation" SKIP "kubeconform not installed"
  fi
  if grep -q 'readOnlyRootFilesystem: true' "$RENDERED" && grep -q 'runAsNonRoot: true' "$RENDERED"; then
    record "Hardened security context rendered" PASS ""
  else
    record "Hardened security context rendered" FAIL ""
  fi
  if grep -Eq 'binarybitops-demo@sha256:[0-9a-f]{64}' "$RENDERED"; then
    record "Digest-pinned image" PASS ""
  else
    record "Digest-pinned image" SKIP "pre-release tag; pipeline pin required"
  fi
  {
    echo "## Rendered overlay (first 120 lines)"
    echo '```yaml'
    head -n 120 "$RENDERED"
    echo '```'
    echo
    if [ -f "${TMPDIR:-/tmp}/bbops-schema.txt" ]; then
      echo "## Kubernetes schema validation"
      echo '```text'
      cat "${TMPDIR:-/tmp}/bbops-schema.txt"
      echo '```'
      echo
    fi
  } >> "$OUT"
else
  record "Render non-production overlay" FAIL "kustomize error"
fi

echo "== HTTP smoke test =="
PORT="$PORT" GIT_SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)" \
  DEMO_ENV=local-verify DEMO_RELEASE=wbs-3.10 PYTHONPATH="$ROOT" \
  python3 -m binarybitops.server > "${TMPDIR:-/tmp}/bbops-server.log" 2>&1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

READY=0
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.25
done

if [ "$READY" -eq 1 ]; then
  record "Server answers /healthz" PASS ""
  BITOPS=$(curl -fsS "http://127.0.0.1:${PORT}/api/bitops?left=12&right=10")
  VERSION=$(curl -fsS "http://127.0.0.1:${PORT}/version")
  STATUS=$(curl -fsS "http://127.0.0.1:${PORT}/api/status")
  INDEX=$(curl -fsS "http://127.0.0.1:${PORT}/")
  METRICS=$(curl -fsS "http://127.0.0.1:${PORT}/metrics")
  echo "$BITOPS" | grep -q '"and":8' && record "Bitwise API result" PASS "" || record "Bitwise API result" FAIL "$BITOPS"
  echo "$VERSION" | grep -q "$(git -C "$ROOT" rev-parse --short HEAD)" && record "Version reports commit" PASS "" || record "Version reports commit" FAIL ""
  echo "$STATUS" | grep -q "not the Binary Bit Ops/Nexus application" && record "Scope boundary in status" PASS "" || record "Scope boundary in status" FAIL ""
  echo "$INDEX" | grep -q "DEMONSTRATOR ONLY" && record "HTML banner" PASS "" || record "HTML banner" FAIL ""
  echo "$METRICS" | grep -q "binarybitops_build_info" && record "Prometheus metrics" PASS "" || record "Prometheus metrics" FAIL ""
  {
    echo "## HTTP smoke test"
    echo '```text'
    echo "GET /healthz -> $(curl -fsS "http://127.0.0.1:${PORT}/healthz")"
    echo "GET /readyz  -> $(curl -fsS "http://127.0.0.1:${PORT}/readyz")"
    echo "GET /version -> $VERSION"
    echo "GET /api/bitops?left=12&right=10 -> $BITOPS"
    echo "GET /api/status -> $STATUS"
    echo "GET /metrics (first lines):"
    echo "$METRICS" | head -n 12
    echo '```'
    echo
  } >> "$OUT"
else
  record "Server answers /healthz" FAIL "server did not start"
fi
cleanup
trap - EXIT INT TERM

echo "== Trivy =="
if command -v trivy >/dev/null 2>&1; then
  if trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 0 --no-progress \
      --ignorefile "$ROOT/.trivyignore.yaml" --skip-dirs .git --skip-dirs evidence --skip-dirs tools "$ROOT" > "${TMPDIR:-/tmp}/bbops-trivy.txt" 2>&1; then
    record "Trivy local scan" PASS "report captured"
  else
    record "Trivy local scan" FAIL "scan error"
  fi
  { echo "## Trivy filesystem scan"; echo '```text'; cat "${TMPDIR:-/tmp}/bbops-trivy.txt"; echo '```'; echo; } >> "$OUT"
else
  record "Trivy local scan" SKIP "trivy not installed"
fi

echo "== Container =="
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if docker build -t binarybitops-demo:verify --build-arg "GIT_SHA=$(git -C "$ROOT" rev-parse --short HEAD)" "$ROOT" > "${TMPDIR:-/tmp}/bbops-build.txt" 2>&1; then
    record "Container image build" PASS ""
  else
    record "Container image build" FAIL "build error"
  fi
  { echo "## Docker build"; echo '```text'; tail -n 40 "${TMPDIR:-/tmp}/bbops-build.txt"; echo '```'; echo; } >> "$OUT"
else
  record "Container image build" SKIP "Docker daemon not reachable"
fi

{
  echo "## Summary"
  echo
  echo "| Check | State | Detail |"
  echo "| --- | --- | --- |"
  printf '%s' "$STATUS_LINES"
  echo
  echo "- Passed: $PASSED"
  echo "- Failed: $FAILED"
  echo "- Skipped: $SKIPPED"
  echo
  echo "Local verification is not HDE acceptance evidence."
} >> "$OUT"

echo "Wrote $OUT"
echo "Passed: $PASSED; failed: $FAILED; skipped: $SKIPPED"
[ "$FAILED" -eq 0 ]

#!/usr/bin/env bash
# Run inside the disposable VM after FILL. Idempotent; it never receives the
# host provisioning key. The only model credential is app/.env's capped runtime key.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

say() { printf '[provision] %s\n' "$*"; }
for command in git uv pi; do
  command -v "$command" >/dev/null || { say "missing required command: $command"; exit 1; }
done

if ! command -v bun >/dev/null; then
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
  sudo ln -sf "$HOME/.bun/bin/bun" /usr/local/bin/bun
fi
if ! command -v just >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | sudo bash -s -- --to /usr/local/bin
fi

key="$(grep -E '^OPENROUTER_API_KEY=' .env | tail -n 1 | cut -d= -f2-)"
[ -n "$key" ] || { say 'missing runtime OPENROUTER_API_KEY in app/.env'; exit 1; }
mkdir -p "$HOME/.pi/agent"
python3 - "$ROOT/sandbox/guest/models.json.tmpl" "$HOME/.pi/agent/models.json" "$key" <<'PY'
import sys
source, destination, key = sys.argv[1:]
text = open(source).read().replace("env:OPENROUTER_API_KEY", key)
open(destination, "w").write(text)
PY
chmod 600 "$HOME/.pi/agent/models.json"

# Create observability database before the first workflow so logs/inspection have a stable location.
uv run adws/adw_prompt.py --help >/dev/null
mkdir -p sandbox
printf 'PROVISION_READY\n'

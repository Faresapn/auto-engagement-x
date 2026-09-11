#!/usr/bin/env bash
# run.sh — wrapper: activate venv + load env + dispatch commands.
#
# Usage:
#   ./run.sh login <handle>          # Interactive login (headed browser)
#   ./run.sh import <handle>         # Import cookies dari import/<handle>.json
#   ./run.sh dry <handle>            # Dry-run 1 aksi (ga post)
#   ./run.sh test <handle>           # Live 1-shot (beneran post 1x)
#   ./run.sh loop <handle>           # Production loop
#   ./run.sh read <handle> <target>  # Test scrape timeline
#   ./run.sh status <handle>         # Cek post count hari ini
#
# ENV vars yang dibutuhkan (set di ~/.zshrc, ~/.bashrc, atau .env file):
#   LLM_API_KEY       - API key Claude (Anthropic direct atau via proxy)
#   LLM_MODEL         - Model name (default: claude-sonnet-4-5)
#   LLM_BASE_URL      - Base URL (default: https://api.anthropic.com/v1)
set -euo pipefail
cd "$(dirname "$0")"

# Load .env kalau ada (biar ga perlu export manual tiap kali)
if [[ -f ".env" ]]; then
  set -a
  . .env
  set +a
fi

# Sanity check env
if [[ -z "${LLM_API_KEY:-}" ]]; then
  echo "❌ LLM_API_KEY not set. Set via ~/.zshrc, ~/.bashrc, atau .env file."
  echo "   Example:"
  echo "     export LLM_API_KEY='sk-ant-xxx'"
  echo "     export LLM_MODEL='claude-sonnet-4-5-20250929'"
  echo "     export LLM_BASE_URL='https://api.anthropic.com/v1'"
  exit 1
fi

# Defaults kalau ga di-set
export LLM_MODEL="${LLM_MODEL:-claude-sonnet-4-5-20250929}"
export LLM_BASE_URL="${LLM_BASE_URL:-https://api.anthropic.com/v1}"

# Activate venv
if [[ ! -d "venv" ]]; then
  echo "❌ venv not found. Run setup first:"
  echo "   python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
source venv/bin/activate

cmd="${1:-help}"
handle="${2:-}"

case "$cmd" in
  login)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python browser_poster.py login "$handle"
    ;;
  import)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python import_cookies.py "$handle"
    ;;
  refresh)
    # Refresh cookie dari clipboard (pbpaste macOS / xclip Linux) → import
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    mkdir -p import
    if command -v pbpaste >/dev/null 2>&1; then
      pbpaste > "import/${handle}.json"
    elif command -v xclip >/dev/null 2>&1; then
      xclip -selection clipboard -o > "import/${handle}.json"
    else
      echo "❌ Neither pbpaste (macOS) nor xclip (Linux) found."
      echo "   Manually save cookie JSON to: import/${handle}.json"
      exit 1
    fi
    # Validate JSON
    if ! python3 -c "import json; json.load(open('import/${handle}.json'))" 2>/dev/null; then
      echo "❌ Clipboard is not valid JSON. Copy cookie JSON from Cookie-Editor first."
      exit 1
    fi
    echo "✅ Cookie pasted from clipboard → import/${handle}.json"
    python import_cookies.py "$handle"
    ;;
  dry)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python main.py "$handle" --dry-run --one-shot
    ;;
  test)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python main.py "$handle" --one-shot
    ;;
  loop)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python main.py "$handle"
    ;;
  read)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    target="${3:-sama}"
    python browser_poster.py read "$handle" "$target" --limit 5
    ;;
  status)
    [[ -z "$handle" ]] && { echo "handle required"; exit 1; }
    python -c "
import sys; sys.path.insert(0, '.')
from main import today_count, load_config
c=load_config('$handle')
n=today_count('$handle')
print(f'@$handle: {n}/{c[\"daily_max\"]} posted today (UTC)')
"
    ;;
  help|*)
    echo "Usage: $0 {login|import|dry|test|loop|read|status} <handle> [target-for-read]"
    exit 1
    ;;
esac

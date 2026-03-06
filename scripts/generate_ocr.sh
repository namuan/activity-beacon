#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-$HOME/Documents/Screenshots}"
DATE=""
FORCE=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [options] [-- <extra vision-ocr args>]

Run Vision OCR over video files under BASE_DIR recursively.
By default this script writes JSON outputs and skips files that already
have a matching .ocr.json file.

Options:
  --base-dir PATH       Base screenshots directory (default: $BASE_DIR)
  --date YYYY-MM-DD     Process a single day directory under BASE_DIR (YYYY/MM/DD)
  --force               Re-process files even when .ocr.json already exists
  -h, --help            Show this help

Examples:
  $(basename "$0")
  $(basename "$0") --date 2025-10-21
  $(basename "$0") --base-dir "$HOME/Documents/Screenshots" --date 2025-10-21
  $(basename "$0") -- --dynamic --change-threshold 0.02
EOF
}

EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-dir)
      BASE_DIR="$2"; shift 2;;
    --date)
      DATE="$2"; shift 2;;
    --force)
      FORCE=true; shift;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OCR_SCRIPT="$REPO_DIR/vision-ocr.py"

if [[ ! -f "$OCR_SCRIPT" ]]; then
  echo "vision-ocr.py not found at $OCR_SCRIPT" >&2
  exit 1
fi

cmd=(uv run "$OCR_SCRIPT" --base-dir "$BASE_DIR" --json)
if [[ -n "$DATE" ]]; then
  cmd+=(--date "$DATE")
fi
if [[ "$FORCE" != true ]]; then
  cmd+=(--skip-existing)
fi
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
fi

"${cmd[@]}"

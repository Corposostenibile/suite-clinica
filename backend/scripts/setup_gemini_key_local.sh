#!/usr/bin/env bash
# Configura la Gemini API key in modo sicuro (solo locale) usando ~/.bashrc_env
# - Non scrive la chiave nel repository
# - Rende la variabile disponibile anche in shell non-interattive (PM2/script)
#
# Uso:
#   backend/scripts/setup_gemini_key_local.sh --key "<API_KEY>"
#   backend/scripts/setup_gemini_key_local.sh --key-stdin
#
# Poi:
#   source ~/.bashrc
#   (riavvia backend/PM2 se necessario)

set -euo pipefail

KEY=""
KEY_STDIN=0
MODEL="gemini-flash-latest"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --key)
      KEY="$2"; shift 2 ;;
    --key-stdin)
      KEY_STDIN=1; shift ;;
    --model)
      MODEL="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,80p' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ $KEY_STDIN -eq 1 ]]; then
  read -r KEY
fi

if [[ -z "${KEY}" ]]; then
  echo "Missing API key. Use --key or --key-stdin" >&2
  exit 1
fi

BASHRC="$HOME/.bashrc"
ENVFILE="$HOME/.bashrc_env"

# 1) Assicura che ~/.bashrc sorgenti ~/.bashrc_env prima del guard interattivo
if ! grep -q "\.bashrc_env" "$BASHRC"; then
  tmpfile="$(mktemp)"
  awk '
    NR==1 {print}
    NR==2 {print}
    NR==3 {print}
    NR==4 {
      print ""
      print "# Load env vars (API keys, local overrides) also for non-interactive shells.";
      print "# File is NOT versioned; safe place for secrets.";
      print "[ -f \"$HOME/.bashrc_env\" ] && . \"$HOME/.bashrc_env\"";
      print ""
    }
    NR>4 {print}
  ' "$BASHRC" > "$tmpfile"
  mv "$tmpfile" "$BASHRC"
fi

# 2) Scrive ~/.bashrc_env (sovrascrive solo le due variabili target)
mkdir -p "$(dirname "$ENVFILE")"

# preserva altre righe se file esiste
if [[ -f "$ENVFILE" ]]; then
  cp "$ENVFILE" "${ENVFILE}.bak.$(date +%Y%m%d%H%M%S)"
fi

# rimuovi eventuali export precedenti
( [[ -f "$ENVFILE" ]] && grep -vE '^export (GOOGLE_API_KEY|GEMINI_LEAD_CRITERIA_MODEL)=' "$ENVFILE" || true ) > "${ENVFILE}.tmp"
cat >> "${ENVFILE}.tmp" <<EOF
export GOOGLE_API_KEY="${KEY}"
export GEMINI_LEAD_CRITERIA_MODEL="${MODEL}"
EOF
mv "${ENVFILE}.tmp" "$ENVFILE"
chmod 600 "$ENVFILE" || true

echo "OK: variabili scritte in $ENVFILE"
echo "Esegui: source ~/.bashrc"

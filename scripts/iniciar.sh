#!/bin/sh
# Arranque del contenedor: deduce la URL pública (Render la da en RENDER_EXTERNAL_URL),
# prepara OmniAgent y lanza n8n.
set -e
if [ -n "$RENDER_EXTERNAL_URL" ]; then
  export WEBHOOK_URL="${WEBHOOK_URL:-$RENDER_EXTERNAL_URL/}"
  export N8N_EDITOR_BASE_URL="${N8N_EDITOR_BASE_URL:-$RENDER_EXTERNAL_URL/}"
  export N8N_HOST="${N8N_HOST:-$RENDER_EXTERNAL_HOSTNAME}"
  export N8N_PROTOCOL="${N8N_PROTOCOL:-https}"
fi
node /opt/omni/arranque.mjs
exec n8n start

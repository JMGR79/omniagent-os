#!/bin/sh
# OmniAgent Control - crea un lanzador en el Escritorio que abre el panel como app.
URL_DEF="https://omniagent-control.onrender.com"
printf "URL del panel [%s]: " "$URL_DEF"; read -r URL; URL="${URL:-$URL_DEF}"
NAV=$(command -v google-chrome || command -v chromium || command -v chromium-browser || command -v microsoft-edge || true)
if [ -n "$NAV" ]; then EXEC="$NAV --app=$URL"; else EXEC="xdg-open $URL"; fi
ESC=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop"); mkdir -p "$ESC"
F="$ESC/omniagent-control.desktop"
printf '[Desktop Entry]\nType=Application\nName=OmniAgent Control\nComment=Centro de mando de EstrategIA Digital 3.0\nExec=%s\nIcon=applications-internet\nTerminal=false\n' "$EXEC" > "$F"
chmod +x "$F"; gio set "$F" metadata::trusted true 2>/dev/null || true
echo "Listo: $F"

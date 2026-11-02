#!/bin/bash
# OmniAgent Control - crea una app en el Escritorio que abre el panel en su propia ventana.
URL_DEF="https://omniagent-control.onrender.com"
read -r -p "URL del panel [$URL_DEF]: " URL; URL="${URL:-$URL_DEF}"
APP="$HOME/Desktop/OmniAgent Control.app"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/MacOS/OmniAgent" <<SH
#!/bin/bash
if [ -d "/Applications/Google Chrome.app" ]; then open -na "Google Chrome" --args --app="$URL"
elif [ -d "/Applications/Microsoft Edge.app" ]; then open -na "Microsoft Edge" --args --app="$URL"
else open "$URL"; fi
SH
chmod +x "$APP/Contents/MacOS/OmniAgent"
cat > "$APP/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>OmniAgent</string><key>CFBundleName</key><string>OmniAgent Control</string>
<key>CFBundleIdentifier</key><string>com.estrategiadigital.omniagent</string><key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PL
echo "Listo: $APP"

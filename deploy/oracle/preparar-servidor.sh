#!/usr/bin/env bash
# Prepara el servidor de Oracle la primera vez (idempotente: se puede ejecutar siempre).
# Instala Docker, abre los puertos 80 y 443 en el cortafuegos de Ubuntu y crea /opt/omniagent.
set -euo pipefail
USUARIO="$(id -un)"

if ! command -v docker >/dev/null 2>&1; then
  echo "[preparar] instalando Docker…"
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USUARIO" || true
sudo systemctl enable --now docker >/dev/null

# Las imágenes Ubuntu de Oracle traen iptables que solo dejan pasar SSH
for PUERTO in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$PUERTO" -m state --state NEW -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 5 -p tcp --dport "$PUERTO" -m state --state NEW -j ACCEPT
    echo "[preparar] puerto $PUERTO abierto"
  fi
done
if command -v netfilter-persistent >/dev/null 2>&1; then sudo netfilter-persistent save >/dev/null 2>&1 || true; fi

sudo mkdir -p /opt/omniagent/src
sudo chown -R "$USUARIO":"$USUARIO" /opt/omniagent
echo "[preparar] servidor listo"

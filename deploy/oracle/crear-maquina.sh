#!/usr/bin/env bash
# OmniAgent OS · crea la máquina gratuita de Oracle desde Cloud Shell (sin usar la consola).
#
# Uso: abre Cloud Shell en la consola de Oracle (icono «>_» arriba a la derecha) y pega:
#   bash <(curl -fsSL https://raw.githubusercontent.com/JMGR79/omniagent-os/main/deploy/oracle/crear-maquina.sh)
#
# Qué hace (se puede repetir sin miedo: reutiliza lo que ya exista):
#   1. Crea la red (VCN, salida a internet, subred pública y puertos 22, 80 y 443 abiertos).
#   2. Genera la clave SSH en ~/omniagent_key (Cloud Shell la guarda entre sesiones).
#   3. Intenta crear la máquina Ampere A1 «omniagent» en todas las zonas, primero 4 núcleos/24 GB
#      y si no hay sitio 2/12 o 1/6. Si Oracle no tiene capacidad, espera y reintenta solo.
#   4. Al final muestra la IP y la clave privada para los secretos de GitHub.
set -uo pipefail

NOMBRE=omniagent
FORMA=VM.Standard.A1.Flex
ESPERA="${ESPERA:-60}"             # segundos entre rondas cuando no hay capacidad
MAX_HORAS="${MAX_HORAS:-6}"        # deja de intentarlo pasado este tiempo
TAMANOS=("4 24" "2 12" "1 6")      # núcleos y GB de RAM, en orden de preferencia
CLAVE="$HOME/omniagent_key"

di() { printf '\n\033[1;36m» %s\033[0m\n' "$*"; }
error() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null || error "No encuentro la herramienta «oci». Ejecuta esto dentro de Cloud Shell de Oracle."
command -v jq >/dev/null || error "No encuentro «jq». Ejecuta esto dentro de Cloud Shell de Oracle."

C="${OCI_TENANCY:-}"
[ -n "$C" ] || C="$(oci iam compartment list --all --include-root --query 'data[?"compartment-id"==null].id | [0]' --raw-output 2>/dev/null)"
[ -n "$C" ] && [ "$C" != "null" ] || error "No pude averiguar el tenancy. Ejecuta esto dentro de Cloud Shell de Oracle."
REGION="${OCI_REGION:-$(oci iam region-subscription list --query 'data[?"is-home-region"].["region-name"] | [0][0]' --raw-output 2>/dev/null)}"
di "Región: ${REGION:-la de Cloud Shell}"

# ¿Ya existe la máquina?
ya_existe() {
  oci compute instance list -c "$C" --display-name "$NOMBRE" --all \
    --query 'data[?"lifecycle-state"!=`TERMINATED` && "lifecycle-state"!=`TERMINATING`].id | [0]' --raw-output 2>/dev/null
}

# ---------- 1. Red ----------
di "Preparando la red"
VCN="$(oci network vcn list -c "$C" --display-name "$NOMBRE-vcn" --all --query 'data[?"lifecycle-state"==`AVAILABLE`].id | [0]' --raw-output)"
if [ -z "$VCN" ] || [ "$VCN" = "null" ]; then
  VCN="$(oci network vcn create -c "$C" --display-name "$NOMBRE-vcn" --cidr-blocks '["10.0.0.0/16"]' \
    --dns-label omniagent --wait-for-state AVAILABLE --query 'data.id' --raw-output)" || error "No pude crear la VCN"
  echo "  VCN creada"
else
  echo "  VCN ya existía"
fi

IGW="$(oci network internet-gateway list -c "$C" --vcn-id "$VCN" --all --query 'data[0].id' --raw-output)"
if [ -z "$IGW" ] || [ "$IGW" = "null" ]; then
  IGW="$(oci network internet-gateway create -c "$C" --vcn-id "$VCN" --is-enabled true \
    --display-name "$NOMBRE-igw" --wait-for-state AVAILABLE --query 'data.id' --raw-output)" || error "No pude crear la salida a internet"
  echo "  Salida a internet creada"
fi

RT="$(oci network vcn get --vcn-id "$VCN" --query 'data."default-route-table-id"' --raw-output)"
oci network route-table update --rt-id "$RT" --force \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" >/dev/null \
  || error "No pude configurar la ruta a internet"

SL="$(oci network security-list list -c "$C" --vcn-id "$VCN" --display-name "$NOMBRE-web" --all --query 'data[0].id' --raw-output)"
if [ -z "$SL" ] || [ "$SL" = "null" ]; then
  REGLAS='['
  for P in 22 80 443; do
    REGLAS+="{\"protocol\":\"6\",\"source\":\"0.0.0.0/0\",\"isStateless\":false,\"tcpOptions\":{\"destinationPortRange\":{\"min\":$P,\"max\":$P}}},"
  done
  REGLAS="${REGLAS%,}]"
  SL="$(oci network security-list create -c "$C" --vcn-id "$VCN" --display-name "$NOMBRE-web" \
    --ingress-security-rules "$REGLAS" \
    --egress-security-rules '[{"protocol":"all","destination":"0.0.0.0/0","isStateless":false}]' \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)" || error "No pude abrir los puertos"
  echo "  Puertos 22, 80 y 443 abiertos"
fi

SUB="$(oci network subnet list -c "$C" --vcn-id "$VCN" --display-name "$NOMBRE-publica" --all --query 'data[0].id' --raw-output)"
if [ -z "$SUB" ] || [ "$SUB" = "null" ]; then
  SUB="$(oci network subnet create -c "$C" --vcn-id "$VCN" --display-name "$NOMBRE-publica" \
    --cidr-block 10.0.0.0/24 --dns-label publica --route-table-id "$RT" \
    --security-list-ids "[\"$SL\"]" --prohibit-public-ip-on-vnic false \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)" || error "No pude crear la subred"
  echo "  Subred pública creada"
fi
echo "  Red lista"

# ---------- 2. Clave SSH ----------
if [ ! -f "$CLAVE" ]; then
  ssh-keygen -q -t ed25519 -N "" -C omniagent -f "$CLAVE"
  di "Clave SSH creada en $CLAVE"
fi

# ---------- 3. Máquina ----------
IMG="$(oci compute image list -c "$C" --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
  --shape "$FORMA" --sort-by TIMECREATED --sort-order DESC --all --query 'data[0].id' --raw-output)"
[ -n "$IMG" ] && [ "$IMG" != "null" ] || error "No encuentro la imagen Ubuntu 24.04 para Ampere en esta región"

mapfile -t ZONAS < <(oci iam availability-domain list -c "$C" --query 'data[].name' --raw-output | jq -r '.[]')
[ "${#ZONAS[@]}" -gt 0 ] || error "No encuentro zonas de disponibilidad"

INST="$(ya_existe)"
if [ -n "$INST" ] && [ "$INST" != "null" ]; then
  di "La máquina «$NOMBRE» ya existe: la reutilizo"
else
  di "Creando la máquina (si Oracle no tiene sitio lo reintento cada ${ESPERA}s; deja esta pestaña abierta)"
  FIN=$(( $(date +%s) + MAX_HORAS * 3600 ))
  RONDA=0
  while [ -z "$INST" ] || [ "$INST" = "null" ]; do
    RONDA=$((RONDA + 1))
    for T in "${TAMANOS[@]}"; do
      read -r CPU RAM <<<"$T"
      for AD in "${ZONAS[@]}"; do
        printf '  Ronda %d · %s núcleos/%s GB · %s … ' "$RONDA" "$CPU" "$RAM" "${AD##*:}"
        SALIDA="$(oci compute instance launch -c "$C" --availability-domain "$AD" \
          --shape "$FORMA" --shape-config "{\"ocpus\":$CPU,\"memoryInGBs\":$RAM}" \
          --image-id "$IMG" --subnet-id "$SUB" --assign-public-ip true \
          --display-name "$NOMBRE" --boot-volume-size-in-gbs 100 \
          --ssh-authorized-keys-file "$CLAVE.pub" \
          --query 'data.id' --raw-output 2>&1)"
        if [[ "$SALIDA" == ocid1.instance.* ]]; then
          INST="$SALIDA"; echo "¡conseguida!"; break 2
        fi
        if grep -qiE 'capacity|TooManyRequests|429' <<<"$SALIDA"; then
          echo "sin sitio"
        elif grep -qiE 'LimitExceeded|limit' <<<"$SALIDA"; then
          echo "límite de la cuenta"
          echo "$SALIDA" | sed -n '/"message"/p' | head -1
        else
          echo "error"
          echo "$SALIDA" | tail -15
          error "Oracle devolvió un error que no es de capacidad (arriba). Mándaselo a Claude."
        fi
        sleep 3
      done
    done
    if [ -z "$INST" ] || [ "$INST" = "null" ]; then
      [ "$(date +%s)" -lt "$FIN" ] || error "Llevo ${MAX_HORAS} h sin capacidad. Vuelve a lanzarlo más tarde o pasa la cuenta a Pay As You Go (sigue siendo gratis)."
      sleep "$ESPERA"
    fi
  done
fi

di "Esperando a que la máquina arranque"
oci compute instance get --instance-id "$INST" >/dev/null
for _ in $(seq 1 60); do
  ESTADO="$(oci compute instance get --instance-id "$INST" --query 'data."lifecycle-state"' --raw-output)"
  [ "$ESTADO" = "RUNNING" ] && break
  sleep 10
done
IP="$(oci compute instance list-vnics --instance-id "$INST" --query 'data[0]."public-ip"' --raw-output)"
[ -n "$IP" ] && [ "$IP" != "null" ] || error "La máquina está creada pero sin IP pública todavía. Vuelve a lanzar el script en un minuto."

# ---------- 4. Datos para GitHub ----------
cat <<FIN

========================================================================
  ✅  Máquina lista.  Ahora, en GitHub → Settings → Secrets → Actions:
      https://github.com/JMGR79/omniagent-os/settings/secrets/actions
========================================================================

  ORACLE_HOST  →  $IP

  ORACLE_SSH_KEY  →  copia TODO el bloque de abajo, incluidas las líneas BEGIN y END:

$(cat "$CLAVE")

  (La clave queda guardada en Cloud Shell: cat ~/omniagent_key)
========================================================================
FIN

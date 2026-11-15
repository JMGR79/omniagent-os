# OmniAgent en Oracle Cloud (gratis)

Servidor «Always Free» de Oracle (Ampere A1: 4 núcleos, 24 GB de RAM) con n8n, Postgres y HTTPS
(Caddy). GitHub lo despliega solo en cada fusión a `main`.

## 1. Crear la máquina

**Opción rápida (recomendada):** en la consola de Oracle abre **Cloud Shell** (icono `>_` arriba a la
derecha) y pega:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/JMGR79/omniagent-os/main/deploy/oracle/crear-maquina.sh)
```

Crea la red, abre los puertos, genera la clave SSH y crea la máquina. Si Oracle responde «Out of host
capacity» (muy habitual en la capa gratuita), lo reintenta solo en todas las zonas y con tamaños más
pequeños hasta conseguirla. Al final muestra la IP y la clave para los secretos del paso 2.

**Opción manual (consola de Oracle):**

1. **Compute → Instances → Create instance**, nombre `omniagent`.
2. **Image**: Canonical Ubuntu 24.04. **Shape**: Ampere → `VM.Standard.A1.Flex`, 4 OCPU y 24 GB.
3. **Networking**: VCN nueva con subred pública y **IPv4 pública** asignada.
4. **SSH keys**: «Generate a key pair for me» → **descarga la clave privada** (archivo `.key`).
5. **Create**. Anota la **IP pública**.
6. Abrir puertos: en la instancia → la subred → **Security List** → **Add Ingress Rules**:
   origen `0.0.0.0/0`, TCP, puertos de destino `80,443`.

## 2. Secretos del repositorio (GitHub → Settings → Secrets and variables → Actions)

| Secreto | Valor |
|---|---|
| `ORACLE_HOST` | IP pública de la máquina |
| `ORACLE_SSH_KEY` | Contenido completo del archivo `.key` descargado |
| `RENDER_API_KEY` | Render → Account Settings → API Keys (solo para la mudanza) |
| `ORACLE_DOMINIO` | Opcional: dominio propio apuntando a la IP. Sin él se usa `IP-con-guiones.sslip.io` |

## 3. Mudanza

GitHub → **Actions → Migrar desde Render → Run workflow**. Copia las variables y la base de datos
de Render y arranca OmniAgent en Oracle en **modo prueba** (`OMNI_MODO_PRUEBA=true`): no publica
solo ni toma los bots de Telegram/WhatsApp, para no chocar con Render mientras siga encendido.

## 4. Pasar a producción

En el servidor, cambia `OMNI_MODO_PRUEBA='false'` en `/opt/omniagent/.env` (o vuelve a ejecutar la
tarea **Desplegar en Oracle** tras cambiarlo), apunta la app y los webhooks a la dirección nueva
y suspende los servicios de pago de Render.

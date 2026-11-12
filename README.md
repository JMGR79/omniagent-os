# OmniAgent OS · Estrateg IA Digital 3.0

Sistema de agentes de IA sobre n8n que gestiona en automático las redes sociales, el email, WhatsApp y los leads, y que crea imágenes, vídeos, webs, negocios y canales.

- **Guía completa de puesta en marcha:** [LEEME.md](LEEME.md)
- **Despliegue:** Blueprint de Render en [`render.yaml`](render.yaml) (n8n + Postgres + app de control).
- **App de control (PWA):** carpeta [`app/`](app/).
- **Web pública (landing):** carpeta [`web/`](web/), guía en [`web/LEEME.md`](web/LEEME.md).
- **Flujos de n8n:** [`n8n/workflows/`](n8n/workflows/), generados con `python3 scripts/generar_flujos.py`.

Las claves (OpenAI, Anthropic, Gemini, Meta, WhatsApp, Telegram, Gmail) **nunca** se guardan en este repositorio: van como variables secretas en Render.

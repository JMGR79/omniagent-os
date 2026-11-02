# OmniAgent OS · EstrategIA Digital 3.0

Sistema de agentes de IA en n8n que funciona **en automático**:

- crea contenido 3 veces al día (8:00, 13:00 y 19:00);
- lo evalúa y publica en Facebook, Instagram, LinkedIn y X;
- prepara los guiones de vídeo de TikTok y YouTube;
- responde los emails de los leads;
- te envía un resumen diario por email y por Telegram;
- se repara solo cuando algo falla.

Lo diriges desde **WhatsApp**, la **app OmniAgent Control** (móvil, tablet o escritorio), **Telegram** o **Claude, ChatGPT o Gemini** (servidor MCP).

## Qué hay en este repositorio

| Ruta | Qué es |
|---|---|
| `Dockerfile`, `scripts/iniciar.sh`, `scripts/arranque.mjs` | n8n 2.45.7. En cada arranque aplica las migraciones, crea las credenciales a partir de las variables de entorno, importa los flujos que falten y activa los que ya tienen su configuración completa. |
| `render.yaml` | Blueprint de Render: base de datos Postgres 17, servicio n8n y la app de control (sitio estático gratuito). |
| `db/migrations/` | Esquema de la base de datos y los 15 agentes con su prompt inicial. |
| `n8n/workflows/` | Los 22 flujos (los genera `scripts/generar_flujos.py`). |
| `app/` | La app de control instalable (PWA). |
| `escritorio/` | Instaladores del acceso directo de escritorio para Windows, Mac y Linux. |

### Los flujos

| Flujo | Qué hace |
|---|---|
| **CNT-01** Director de contenido | Tres veces al día lee tus órdenes, crea piezas para cada canal activo y las pasa al Evaluador. Si una pieza es sensible (temas legales, de salud o de dinero), va a Aprobar. Si no, a la cola. |
| **PUB-01** Publicador | Cada 15 minutos publica lo que está en cola: Facebook, Instagram, Telegram, LinkedIn (vía PUB-02) y X (vía PUB-03). Si falla, reintenta 3 veces. |
| **AGT-00** Ejecutar agente | Motor común de los 15 agentes. Funciona con Claude, OpenAI o Gemini (variable `PROVEEDOR_IA`) y lleva el control del coste y del presupuesto diario. |
| **MSG-01** Emails de leads | Lee la etiqueta de Gmail `OmniAgent-Leads`. Responde como asistente de IA (lo indica en cada mensaje, como exige el Reglamento europeo de IA) y te pasa los emails con intención de compra o las quejas. |
| **TEL-01** Telegram | Botones ✅/🗑 para aprobar piezas. Cualquier mensaje que le escribas al bot se registra como orden para el Director. |
| **GEN-01** Imagen | Imágenes con IA (OpenAI o Google): posts, portadas y miniaturas. Los posts de Instagram llevan imagen generada automáticamente. |
| **VID-01 / GEN-02** Vídeo | Convierte los guiones de shorts y reels en vídeo con Veo 3.1 (Google). Los de YouTube y los Reels se publican solos; los de TikTok te llegan para subirlos. |
| **GEN-03 / WEB-01** Webs | Crea landing pages con formulario. Las publica en tu servidor, cuenta las visitas y convierte los formularios en leads con aviso. |
| **NEG-01** Negocios y canales | De una idea a un proyecto completo: plan, oferta, portada, web y la primera semana de contenido. |
| **PUB-03 / PUB-04** X y YouTube | Tuits e **hilos** en X; Shorts en YouTube. |
| **WA-01 / WA-02** WhatsApp | Control total desde tu WhatsApp y atención a clientes con IA (ver abajo). Todos los avisos te llegan también por WhatsApp. |
| **RPT-01** Resumen diario | A las 20:30, por email (a `EMAIL_DUENO`), por WhatsApp y por Telegram. |
| **SYS-00 / SYS-01** | Registran los errores y reintentan solos las ejecuciones fallidas. |
| **SYS-20** | API de la app de control. Solo ejecuta consultas de una lista blanca: la app nunca envía SQL. |
| **SYS-21 / MCP-01** | Las 11 herramientas para Claude, ChatGPT o Gemini, publicadas como servidor MCP con el login de n8n (OAuth). |

## Puesta en marcha (unos 30 minutos)

### 1. Desplegar en Render
1. Sube este repositorio a GitHub.
2. Abre `https://dashboard.render.com/blueprint/new` y elige el repositorio.
3. Render te pedirá las claves. Rellena las que tengas; el resto puedes añadirlas después en *Environment*:
   - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` o `GEMINI_API_KEY`: basta con la del proveedor que indiques en `PROVEEDOR_IA` (`anthropic`, `openai` o `gemini`).
   - `GMAIL_APP_PASSWORD`: una *contraseña de aplicación* de Google. Necesitas tener activada la verificación en 2 pasos; se crea en https://myaccount.google.com/apppasswords.
   - `TELEGRAM_BOT_TOKEN`: crea el bot con @BotFather. Para saber tu `TELEGRAM_CHAT_ID`, escribe `/id` a tu bot.
   - `META_PAGE_ID`, `META_PAGE_TOKEN` (token de página de larga duración) e `IG_USER_ID` (cuenta de Instagram Business vinculada a la página). Se sacan con una app de Meta for Developers y los permisos `pages_manage_posts`, `instagram_basic` e `instagram_content_publish`.
4. Rellena también `EMAIL_DUENO` y `GMAIL_USUARIO` (tu Gmail) y `WHATSAPP_NUMERO_DUENO` (tu móvil con prefijo y sin «+»). No están en el repositorio porque es público.
5. Pulsa **Apply**. Coste aproximado: servicio Starter 7 $/mes + Postgres Basic 6 $/mes. La app de control es gratis.

Cada vez que añadas o cambies una clave, Render reinicia el servicio y el arranque activa los flujos que ya tengan lo necesario.

### 2. Primer acceso a n8n
1. Abre la URL del servicio `omniagent-n8n` y crea tu usuario propietario.
2. En *Settings → n8n API* crea una API key y guárdala en Render como `N8N_API_KEY`. Hace falta para la sección Flujos de la app y para la autorreparación.

### 3. Conectar LinkedIn y X (necesitan tu login)
- **LinkedIn:** abre **PUB-02**, crea la credencial «LinkedIn OAuth2», elige tu perfil en *Person* y pulsa **Publish**.
- **X (@2279Jmgarcia):** abre **PUB-03**, crea la credencial «X OAuth2» con los datos de tu app de developer.x.com y pulsa **Publish**. Ojo: X puede cobrar por publicar mediante su API, según el plan que tengas.

Hasta que lo hagas, esas piezas quedan con el aviso «cuenta sin conectar» y el resto de canales siguen publicando con normalidad.

### 4. Gmail
Crea un filtro que mande a la etiqueta `OmniAgent-Leads` los emails de leads, por ejemplo los dirigidos a `tucorreo+leads@gmail.com` (pon esa dirección en tu web y en los formularios). El agente **solo** lee esa etiqueta, nunca el resto de tu bandeja.

### 5. La app en el móvil y en el escritorio
1. Abre la URL del servicio `omniagent-control`. En **Ajustes**, pega:
   - la URL `https://<tu-n8n>/webhook/omniagent-control`;
   - el token (`OMNIAGENT_CONTROL_TOKEN`, que está en Render → omniagent-n8n → Environment).
2. Pulsa **Copiar enlace de conexión** y ábrelo en el móvil: el móvil queda conectado sin escribir nada.
3. Para instalarla:
   - **Android:** menú ⋮ → *Instalar aplicación*.
   - **iPhone:** Compartir → *Añadir a pantalla de inicio*.
   - **Escritorio:** ejecuta el instalador de la carpeta `escritorio/` que corresponda a tu sistema, o en Chrome o Edge usa el icono *Instalar* de la barra de direcciones.

### 6. WhatsApp: control total y atención a clientes
Usa la **API oficial de WhatsApp Cloud** de Meta (no se usan apps no oficiales, que pueden acabar en bloqueo del número).
1. En https://developers.facebook.com crea una app de tipo *Business* y añade el producto **WhatsApp**. El número que conectes queda dedicado a la API: no podrás usarlo a la vez en la app normal de WhatsApp (salvo que Meta te ofrezca el modo «coexistencia» para WhatsApp Business). Para probar, Meta te da un número de prueba gratuito.
2. Pon en Render:
   - `WHATSAPP_TOKEN`: token permanente de un *usuario del sistema* de Business Manager con el permiso `whatsapp_business_messaging`.
   - `WHATSAPP_PHONE_ID`: el *Phone number ID*.
   - `WHATSAPP_APP_SECRET`: el *App Secret* (Configuración → Básica). Con él se comprueba que cada mensaje viene de verdad de Meta.
   - `WHATSAPP_NUMERO_DUENO`: tu número personal con prefijo y sin «+», por ejemplo `34600111222`. **Solo ese número tiene control total.**
3. En WhatsApp → Configuración → Webhook:
   - URL de devolución: `https://<tu-n8n>/webhook/whatsapp`.
   - Token de verificación: el valor de `WHATSAPP_VERIFY_TOKEN`, que Render genera solo.
   - Suscríbete al campo `messages`.
4. **Avisos aunque lleves más de 24 h sin escribir:** Meta solo deja escribirte libremente durante las 24 h siguientes a tu último mensaje. Para recibir avisos fuera de ese plazo, crea una plantilla de tipo *Utilidad* llamada `omniagent_aviso`, en español y con el cuerpo `Aviso de OmniAgent: {{1}}`. Pon su nombre en `WHATSAPP_PLANTILLA_AVISO`.

**Desde tu WhatsApp** puedes escribir:
- `resumen`
- `pendientes` (te llegan con botones ✅ Aprobar / 🗑 Descartar)
- `leads`, `incidentes`, `agentes`
- `ciclo`, `publicar`
- `pausar` / `reanudar`
- `agente 2: …`
- `orden: …`

O simplemente escribe con normalidad, por ejemplo «prepara 3 posts para mañana sobre automatizar WhatsApp» o «¿cómo vamos?»: la IA lo entiende.

**Tus clientes** que escriban a ese número reciben respuesta del asistente de IA (en el primer mensaje avisa de que es una IA). Si quieren comprar, piden precio, se quejan o escriben «persona», te llega un aviso con el enlace `wa.me` para contestarles tú.

### 7. Fábrica de contenido: imágenes, vídeos, webs y negocios
Variables en Render:
- **Imágenes:** `PROVEEDOR_IMAGEN=openai` (con `OPENAI_API_KEY`; modelo por defecto `gpt-image-2`) o `PROVEEDOR_IMAGEN=gemini` (con `GEMINI_API_KEY`; modelo por defecto `imagen-4.0-generate-001`). Puedes cambiar el modelo con `MODELO_IMAGEN`.
- **Vídeo:** `PROVEEDOR_VIDEO=gemini` (Veo 3.1, con `GEMINI_API_KEY`; modelo `veo-3.1-generate-preview`, ajustable con `MODELO_VIDEO`). Cada vídeo dura unos 8 s, con audio. **Veo se paga por segundo de vídeo**, así que `VIDEOS_POR_DIA` (1 por defecto) limita el gasto.
- **Alternativa con OpenAI:** `PROVEEDOR_VIDEO=openai` usa Sora (`sora-2`, ajustable con `MODELO_VIDEO`; duración con `SEGUNDOS_VIDEO`, 8 por defecto) con tu `OPENAI_API_KEY`. Ojo: OpenAI anunció la retirada de esta API para el 24 de septiembre de 2026. Si tu cuenta ya no tiene acceso, el aviso de error lo dirá y bastará con poner `PROVEEDOR_VIDEO=gemini`.
- **Con una sola clave de OpenAI puedes moverlo todo:** `PROVEEDOR_IA=openai` (texto), `PROVEEDOR_IMAGEN=openai` (imágenes) y `PROVEEDOR_VIDEO=openai` (vídeo).

Cómo pedirlo:
- **WhatsApp:**
  - `imagen: …`, `portada: …`, `miniatura: …`
  - `video: …`
  - `videos` (convierte ya los guiones pendientes)
  - `web: …`
  - `negocio: …`, `canal: …`
- **La app:** sección **Crear**, con la galería de todo lo creado.
- **Claude, ChatGPT o Gemini:** las herramientas `generar_imagen`, `generar_video`, `crear_web` y `crear_negocio`.

**Dónde se publica cada cosa:**
- **Imágenes y vídeos:** los sirve tu propio n8n en `https://<tu-n8n>/webhook/medio?id=…`.
- **Webs:** en `https://<tu-n8n>/webhook/web?s=…`. Más adelante puedes apuntar un dominio propio.

**YouTube:** abre **PUB-04**, crea la credencial «YouTube OAuth2» (con un proyecto de Google Cloud que tenga la *YouTube Data API v3* activada) y pulsa **Publish**.

**TikTok:** su API de publicación exige que TikTok audite la app. Hasta entonces, el vídeo te llega por WhatsApp para subirlo con un toque.

### 8. Dirigir el negocio desde Claude, ChatGPT o Gemini
La URL del servidor MCP es `https://<tu-n8n>/mcp/omniagent`. Al conectarlo, te pedirá entrar con tu usuario de n8n.
- **Claude** (web, escritorio o móvil): Ajustes → Conectores → *Añadir conector personalizado* → pega la URL.
- **ChatGPT:** Ajustes → Aplicaciones y conectores → modo desarrollador → *Crear* → pega la URL.
- **Gemini CLI:** en `~/.gemini/settings.json` añade `"mcpServers": {"omniagent": {"httpUrl": "https://<tu-n8n>/mcp/omniagent"}}`.

Después puedes pedir cosas como «¿cómo va el negocio hoy?», «enséñame lo que está pendiente de aprobar», «dile al Director que prepare 3 posts sobre automatizar WhatsApp para mañana» o «lanza un ciclo de contenido ahora».

## Ajustes útiles (variables en Render)

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `MODO_AUTOMATICO` | `true` | Con `false`, todas las piezas y respuestas pasan por tu aprobación. Para una pausa temporal, escribe `pausar` por WhatsApp. |
| `CANALES_ACTIVOS` | `facebook,instagram,linkedin,x,tiktok,youtube` | Quita los canales que no uses. |
| `PIEZAS_POR_CICLO` | `3` | Piezas nuevas en cada ciclo (3 ciclos al día). |
| `PRESUPUESTO_TOKENS_DIARIO_EUR` | `5` | Al llegar a este gasto diario, los agentes paran hasta el día siguiente. |
| `PROVEEDOR_IA` / `MODELO_IA` | `anthropic` / según proveedor | Cambia de IA sin tocar los flujos. |
| `PUNTUACION_MINIMA` | `6` | Nota mínima del Evaluador para que una pieza se publique. |
| `IMAGEN_PLANTILLA_URL` | tarjeta de placehold.co | Imagen de Instagram. Usa `{texto}` como hueco. Conviene cambiarla por tu propio generador de imágenes o plantilla de marca. |

## Límites conocidos
- **Vídeo:** sin `PROVEEDOR_VIDEO`, los guiones de TikTok, YouTube y Reels quedan esperando. Con Veo se generan solos (hasta `VIDEOS_POR_DIA`); TikTok sigue siendo de subida manual.
- **Instagram** necesita una imagen: sin `PROVEEDOR_IMAGEN` se usa una tarjeta de texto genérica.
- **Mensajes directos** de Instagram y Facebook: responderlos requiere la revisión de la app por parte de Meta. No están incluidos.
- Los precios por token que se usan para calcular el coste de la IA son orientativos. Ajústalos con `PRECIO_ENTRADA_EUR_MTOK` y `PRECIO_SALIDA_EUR_MTOK`.

## Desarrollo
Edita `scripts/generar_flujos.py` y ejecuta `python3 scripts/generar_flujos.py`. Ten en cuenta que el arranque **no pisa** flujos que ya existan en n8n: para reimportar uno, bórralo en n8n y reinicia el servicio.

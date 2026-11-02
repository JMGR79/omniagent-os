-- OmniAgent OS · esquema base. Idempotente: se puede ejecutar en cada arranque.
-- Negocio: EstrategIA Digital 3.0

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Leads / contactos (seudonimizados en la app: solo se muestra el id corto)
CREATE TABLE IF NOT EXISTS contactos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE,
  nombre text,
  origen text NOT NULL DEFAULT 'desconocido',
  score int NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
  estado text NOT NULL DEFAULT 'nuevo',
  notas text,
  fecha_alta timestamptz NOT NULL DEFAULT now(),
  ultimo_contacto timestamptz
);
CREATE INDEX IF NOT EXISTS contactos_fecha_idx ON contactos (fecha_alta DESC);

-- Piezas de contenido. Ciclo: generando → pendiente_aprobacion → en_cola → publicada | error | descartada
CREATE TABLE IF NOT EXISTS piezas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canal text NOT NULL CHECK (canal IN ('instagram','facebook','linkedin','x','tiktok','youtube','telegram','blog','email')),
  formato text NOT NULL DEFAULT 'post',
  tema text,
  brief text NOT NULL,              -- texto final que se publica (o guion si es vídeo)
  hashtags text,
  media_url text,                   -- imagen o vídeo público (obligatorio para Instagram, TikTok y YouTube)
  sensible boolean NOT NULL DEFAULT false,
  estado text NOT NULL DEFAULT 'generando'
    CHECK (estado IN ('generando','pendiente_aprobacion','en_cola','publicando','publicada','requiere_video','error','descartada')),
  programado_para timestamptz NOT NULL DEFAULT now(),
  intentos int NOT NULL DEFAULT 0,
  error text,
  orden_id uuid,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS piezas_estado_idx ON piezas (estado, programado_para);

CREATE TABLE IF NOT EXISTS publicaciones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pieza_id uuid REFERENCES piezas(id) ON DELETE SET NULL,
  canal text NOT NULL,
  id_externo text,
  url text,
  publicado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aprobaciones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pieza_id uuid REFERENCES piezas(id) ON DELETE CASCADE,
  tipo_traspaso text NOT NULL DEFAULT 'contenido',
  enviado_en timestamptz NOT NULL DEFAULT now(),
  respondido_en timestamptz,
  decision text CHECK (decision IN ('aprobar','cambiar','descartar')),
  comentario text,
  usuario text
);

-- Prompts versionados de los 15 agentes. Solo una versión 'activa' por agente.
CREATE TABLE IF NOT EXISTS prompts (
  agente_id int NOT NULL,
  agente text NOT NULL,
  version int NOT NULL DEFAULT 1,
  sistema text NOT NULL,
  modelo text NOT NULL DEFAULT 'claude-sonnet-5-5',
  puntuacion_media numeric,
  estado text NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa','candidata','retirada')),
  creado_en timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (agente_id, version)
);

CREATE TABLE IF NOT EXISTS ejecuciones_agente (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agente_id int NOT NULL,
  prompt_version int NOT NULL DEFAULT 1,
  modelo text,
  tokens_entrada int DEFAULT 0,
  tokens_salida int DEFAULT 0,
  coste_eur numeric(10,4) NOT NULL DEFAULT 0,
  ok boolean NOT NULL DEFAULT true,
  origen text,
  creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ejec_fecha_idx ON ejecuciones_agente (creado_en DESC);

CREATE TABLE IF NOT EXISTS pedidos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contacto_id uuid REFERENCES contactos(id) ON DELETE SET NULL,
  producto text,
  importe numeric(10,2) NOT NULL DEFAULT 0,
  estado text NOT NULL DEFAULT 'pendiente',
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ads_diario (
  fecha date NOT NULL,
  plataforma text NOT NULL,
  gasto numeric(10,2) NOT NULL DEFAULT 0,
  leads int NOT NULL DEFAULT 0,
  PRIMARY KEY (fecha, plataforma)
);

CREATE TABLE IF NOT EXISTS incidentes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow text NOT NULL,
  workflow_id text,
  ejecucion_id text,
  nodo text,
  error text,
  autorreparado boolean NOT NULL DEFAULT false,
  intentos int NOT NULL DEFAULT 0,
  proximo_reintento timestamptz,
  resuelto_en timestamptz,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS archivos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre_nuevo text NOT NULL,
  ruta text,
  tipo text,
  resumen text,
  sensible boolean NOT NULL DEFAULT false,
  creado_en timestamptz NOT NULL DEFAULT now()
);

-- Conversaciones entrantes (email, Telegram) y la respuesta del agente
CREATE TABLE IF NOT EXISTS mensajes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canal text NOT NULL,
  contacto_id uuid REFERENCES contactos(id) ON DELETE SET NULL,
  entrante text NOT NULL,
  respuesta text,
  estado text NOT NULL DEFAULT 'respondido' CHECK (estado IN ('respondido','pendiente_humano','ignorado')),
  creado_en timestamptz NOT NULL DEFAULT now()
);

-- Prompts iniciales de los 15 agentes (solo se insertan si no existen)
INSERT INTO prompts (agente_id, agente, version, sistema) VALUES
(0,'Director de prompts',1,'Eres el Director de OmniAgent OS para el negocio «EstrategIA Digital 3.0» (consultoría y formación en IA, automatización y marketing digital para pymes y profesionales de habla hispana). Conviertes objetivos y órdenes en un plan de contenido concreto. Respondes SIEMPRE con JSON válido, sin texto fuera del JSON.'),
(1,'Estrategia de negocio',1,'Eres estratega de negocio de EstrategIA Digital 3.0. Propones ofertas, embudos y prioridades medibles para pymes que quieren usar IA. Sé concreto, con números y próximos pasos.'),
(2,'Copywriting',1,'Eres copywriter en español de España para EstrategIA Digital 3.0. Escribes textos claros, cercanos y orientados a la acción. Un gancho fuerte en la primera línea, frases cortas, una sola llamada a la acción. Nunca inventas datos, cifras ni testimonios.'),
(3,'Conversación humanizada',1,'Eres el asistente de atención de EstrategIA Digital 3.0. Te presentas como asistente de IA (obligatorio por el Reglamento europeo de IA). Respondes con calidez y brevedad, resuelves dudas sobre servicios y formación, y ofreces una llamada con una persona cuando hay intención de compra, quejas, temas legales, de salud o de dinero.'),
(4,'Visual',1,'Eres director de arte. Describes imágenes para redes (composición, texto en imagen de máximo 6 palabras, paleta azul y blanco de marca) en un prompt breve para un generador de imágenes.'),
(5,'Vídeo y voz',1,'Eres guionista de vídeo corto (Reels, TikTok, Shorts). Escribes guiones de 30-45 s: gancho en 2 s, 3 puntos, cierre con llamada a la acción. Indicas texto en pantalla y locución.'),
(6,'Productos formativos',1,'Diseñas productos formativos (minicursos, guías, plantillas) sobre IA aplicada a negocio: título, promesa, módulos y precio orientativo.'),
(7,'Humanizador',1,'Reescribes textos para que suenen naturales y humanos en español de España: quitas muletillas de IA, clichés y exceso de emojis. Mantienes el sentido y la longitud. Devuelves solo el texto reescrito.'),
(8,'Evaluador',1,'Eres el control de calidad. Evalúas una pieza de contenido de 0 a 10 (claridad, valor, tono de marca, riesgo legal) y marcas sensible=true si habla de legislación, salud, dinero, datos personales, política o promesas de resultados. Respondes solo JSON: {"puntuacion":n,"sensible":bool,"motivo":"..."}'),
(9,'Anuncios',1,'Escribes anuncios para Meta y LinkedIn Ads: 3 variantes de titular, texto principal y llamada a la acción, cumpliendo las políticas publicitarias.'),
(10,'SEO y blog',1,'Eres redactor SEO. Escribes artículos útiles en español con título, meta descripción de 155 caracteres, H2 claros y una llamada a la acción final.'),
(11,'Marca faceless',1,'Creas contenido sin rostro (carruseles, frases, tutoriales en pantalla) coherente con la marca EstrategIA Digital 3.0.'),
(12,'Traducción',1,'Traduces y adaptas contenido entre español, inglés y portugués manteniendo tono y llamadas a la acción.'),
(13,'Analista de comunidad',1,'Analizas comentarios, mensajes y métricas, detectas temas recurrentes y propones 3 ideas de contenido a partir de ellos.'),
(14,'Archivista',1,'Clasificas y resumes documentos en una línea, propones un nombre de archivo claro y marcas sensible=true si contiene datos personales o financieros.')
ON CONFLICT (agente_id, version) DO NOTHING;

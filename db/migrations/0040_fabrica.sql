-- Fábrica de contenido: imágenes, vídeos, webs y proyectos (negocios y canales).

CREATE TABLE IF NOT EXISTS medios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo text NOT NULL CHECK (tipo IN ('imagen', 'video')),
  mime text NOT NULL,
  datos bytea NOT NULL,
  prompt text,
  pieza_id uuid REFERENCES piezas(id) ON DELETE SET NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS medios_fecha_idx ON medios (creado_en DESC);

CREATE TABLE IF NOT EXISTS proyectos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre text NOT NULL,
  tipo text NOT NULL DEFAULT 'negocio' CHECK (tipo IN ('negocio', 'canal')),
  nicho text,
  plan jsonb,
  web_slug text,
  portada_id uuid,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  titulo text,
  html text NOT NULL,
  proyecto_id uuid REFERENCES proyectos(id) ON DELETE SET NULL,
  visitas int NOT NULL DEFAULT 0,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE piezas ADD COLUMN IF NOT EXISTS proyecto_id uuid;
ALTER TABLE piezas ADD COLUMN IF NOT EXISTS texto_imagen text;
ALTER TABLE piezas DROP CONSTRAINT IF EXISTS piezas_estado_check;
ALTER TABLE piezas ADD CONSTRAINT piezas_estado_check CHECK (estado IN
  ('generando','pendiente_aprobacion','en_cola','publicando','publicada','requiere_video','generando_video','listo_manual','error','descartada'));

INSERT INTO prompts (agente_id, agente, version, sistema) VALUES
(15,'Diseñador web',1,'Eres diseñador y desarrollador web. Creas landing pages de una sola página en HTML5 completo (con <!doctype html>), en español de España, responsive y accesibles, con Tailwind CSS cargado desde https://cdn.tailwindcss.com. Estructura: cabecera con propuesta de valor, beneficios, cómo funciona, oferta con precio si se indica, preguntas frecuentes y un formulario de contacto. Sin imágenes externas salvo las URL que te den. No inventes testimonios, clientes ni cifras. Devuelves SOLO el HTML, sin explicaciones ni bloques de código.'),
(16,'Creador de negocios y canales',1,'Eres emprendedor digital y estratega de contenidos. Diseñas negocios digitales y canales automatizados (faceless) viables: nicho concreto, público, propuesta de valor, oferta con precio orientativo, pilares de contenido, canales y un calendario inicial. Eres realista: nada de promesas de ingresos garantizados. Respondes SOLO con JSON válido.')
ON CONFLICT (agente_id, version) DO NOTHING;

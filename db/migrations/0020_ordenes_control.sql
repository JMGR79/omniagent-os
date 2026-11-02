-- Órdenes enviadas desde OmniAgent Control. CNT-01 (orquestador) las lee en cada ciclo.
CREATE TABLE IF NOT EXISTS ordenes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  texto text NOT NULL CHECK (length(texto) <= 2000),
  origen text NOT NULL DEFAULT 'app',
  estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en_proceso', 'hecha', 'rechazada')),
  resultado text,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ordenes_estado_idx ON ordenes (estado, creado_en);

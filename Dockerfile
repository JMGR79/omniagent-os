# OmniAgent OS · n8n 2.45.7 con autoconfiguración (migraciones, credenciales y flujos)
FROM node:24-alpine AS deps
WORKDIR /opt/omni
RUN npm init -y >/dev/null && npm install pg@8.23.1 --omit=dev --no-audit --no-fund

FROM n8nio/n8n:2.45.7
COPY --chown=node:node --from=deps /opt/omni/node_modules /opt/omni/node_modules
COPY --chown=node:node db /opt/omni/db
COPY --chown=node:node n8n/workflows /opt/omni/n8n/workflows
COPY --chown=node:node --chmod=755 scripts/arranque.mjs scripts/db-env.mjs scripts/iniciar.sh /opt/omni/
ENV OMNI_DIR=/opt/omni
EXPOSE 5678
ENTRYPOINT ["tini", "--", "/opt/omni/iniciar.sh"]

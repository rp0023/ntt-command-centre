# The front-end half: Vite build served by nginx.
#
# nginx reproduces the dev topology from vite.config.ts — /api and /healthz are
# proxied to the API, so the browser only ever makes same-origin requests and
# VITE_API_BASE stays empty. The upstream is set at runtime with API_UPSTREAM.

# ---- build -------------------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /web

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Leave empty for same-origin (proxied) requests; set only to call an API on
# another origin directly, which then needs NTT_ALLOWED_ORIGINS on the API.
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# ---- serve -------------------------------------------------------------------
FROM nginx:1.27-alpine

# The official image renders /etc/nginx/templates/*.template with envsubst.
# Only our own variables are substituted, so nginx's $host etc. survive.
ENV PORT=80 \
    API_UPSTREAM=http://api:8080 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_FILTER="^(PORT|API_UPSTREAM|NGINX_LOCAL_RESOLVERS)$"
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:${PORT}/ >/dev/null || exit 1

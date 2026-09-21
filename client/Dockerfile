# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Vite inlines VITE_* variables into the bundle at build time — there is no
# runtime configuration for a static SPA. So they are build ARGs, and
# changing the API URL means rebuilding this image rather than restarting the
# container. That is a real constraint, not an oversight: the alternative is
# fetching a config.json on boot, which buys runtime flexibility at the cost
# of an extra round trip before the app can render. For a stack whose
# frontend and backend deploy together, the rebuild is the cheaper trade.
# ---------------------------------------------------------------------------

FROM node:22-alpine AS builder
WORKDIR /app

# Lockfile first: dependencies change far less often than source, so this
# layer stays cached across ordinary code edits. `npm ci` (not `install`)
# installs exactly what package-lock.json pins.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

# --- runtime ----------------------------------------------------------------
# Nothing from the build survives except dist/: no node_modules, no source,
# no toolchain. The runtime image is a static file server and its content.
FROM nginx:1.27-alpine AS client
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 5173

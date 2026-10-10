# LearnAI web client. Multi-arch (linux/amd64, linux/arm64).
# API_URL (where /api-backend/* is proxied) is read at runtime, not build time.

ARG NODE_VERSION=22

FROM node:${NODE_VERSION}-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
COPY scripts ./scripts
# postinstall copies MathJax + the pdf.js worker into public/vendor
RUN mkdir -p public && npm ci


FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# Inlined into the browser bundle at build time
ARG NEXT_PUBLIC_USER_ID=default
ENV NEXT_PUBLIC_USER_ID=${NEXT_PUBLIC_USER_ID}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
COPY --from=deps /app/public/vendor ./public/vendor
RUN npm run build


FROM node:${NODE_VERSION}-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    API_URL=http://learnai-server:8000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/home || exit 1
CMD ["node", "server.js"]

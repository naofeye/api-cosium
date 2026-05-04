FROM node:25-alpine AS builder
WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_SENTRY_DSN=

ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_SENTRY_DSN=${NEXT_PUBLIC_SENTRY_DSN}

COPY package.json package-lock.json* ./
# --legacy-peer-deps : openapi-typescript@7.13 declare peer typescript@^5
# alors qu'on est sur TS6.x. Le package fonctionne en pratique sur TS6
# (pas de breaking AST). Aligne sur les workflows .github/workflows/*.yml.
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:25-alpine
RUN adduser -D appuser
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER appuser
EXPOSE 3000
CMD ["node", "server.js"]

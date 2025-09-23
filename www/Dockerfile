#syntax=docker/dockerfile:1.4
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Install dependencies only when needed
FROM base AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY --link package.json pnpm-lock.yaml* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps --link /app/node_modules ./node_modules
COPY --link  . .

ARG SITE_URL
ARG API_URL
ARG WEBSOCKET_URL
ARG NEXTAUTH_URL
ARG NEXTAUTH_SECRET
ARG AUTHENTIK_ISSUER
ARG AUTHENTIK_CLIENT_ID
ARG AUTHENTIK_CLIENT_SECRET
ARG AUTHENTIK_REFRESH_TOKEN_URL

ENV SITE_URL=$SITE_URL
ENV API_URL=$API_URL
ENV WEBSOCKET_URL=$WEBSOCKET_URL
ENV NEXTAUTH_URL=$NEXTAUTH_URL
ENV NEXTAUTH_SECRET=$NEXTAUTH_SECRET
ENV AUTHENTIK_ISSUER=$AUTHENTIK_ISSUER
ENV AUTHENTIK_CLIENT_ID=$AUTHENTIK_CLIENT_ID
ENV AUTHENTIK_CLIENT_SECRET=$AUTHENTIK_CLIENT_SECRET
ENV AUTHENTIK_REFRESH_TOKEN_URL=$AUTHENTIK_REFRESH_TOKEN_URL

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
# Uncomment the following line in case you want to disable telemetry during the build.
ENV NEXT_TELEMETRY_DISABLED 1

# If using npm comment out above and use below instead
RUN pnpm build
# RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
# Uncomment the following line in case you want to disable telemetry during runtime.
# ENV NEXT_TELEMETRY_DISABLED 1

RUN \
    addgroup --system --gid 1001 nodejs; \
    adduser --system --uid 1001 nextjs

COPY --from=builder --link /app/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --link --chown=1001:1001 /app/.next/standalone ./
COPY --from=builder --link --chown=1001:1001 /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME 0.0.0.0

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:3000/api/health', (r) => {r.resume(); process.exit(r.statusCode === 200 ? 0 : 1)})" \
  || exit 1

CMD ["node", "server.js"]

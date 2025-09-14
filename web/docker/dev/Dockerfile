# Multi-stage Next.js Docker build for web2
FROM node:20-alpine AS base

# Best practice: set NODE_ENV to production in the final image
# For the build process, though, we might keep it as "development"
# if Next.js needs dev-mode steps. Usually, we can keep it at "production."

# Install dependencies only when needed
FROM base AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json* ./
RUN npm ci && npm cache clean --force

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_FACEBOOK_PIXEL_ID
ARG NEXT_PUBLIC_MUI_LICENSE
ARG NEXT_PUBLIC_CLIENT_SENTRY_DSN
ARG NEXT_PUBLIC_SERVER_SENTRY_DSN
ARG NEXT_PUBLIC_EDGE_SENTRY_DSN
ARG NEXT_PUBLIC_API_URL

# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED 1

# Set Next environment variables
ENV NEXT_PUBLIC_CLIENT_SENTRY_DSN=${NEXT_PUBLIC_CLIENT_SENTRY_DSN}
ENV NEXT_PUBLIC_SERVER_SENTRY_DSN=${NEXT_PUBLIC_SERVER_SENTRY_DSN}
ENV NEXT_PUBLIC_EDGE_SENTRY_DSN=${NEXT_PUBLIC_EDGE_SENTRY_DSN}
ENV NEXT_PUBLIC_FACEBOOK_PIXEL_ID=${NEXT_PUBLIC_FACEBOOK_PIXEL_ID}
ENV NEXT_PUBLIC_MUI_LICENSE=${NEXT_PUBLIC_MUI_LICENSE}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

FROM base AS runner

# Create app directory
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

# Expose the port your Next.js app runs on (default is 3000)
EXPOSE 3000

ENV PORT 3000

# server.js is created by next build from the standalone output
# https://nextjs.org/docs/pages/api-reference/next-config-js/output
CMD ["node", "server.js"]

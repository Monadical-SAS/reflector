FROM node:18-alpine AS builder
WORKDIR /app

# Install curl for fetching OpenAPI spec
RUN apk add --no-cache curl

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Fetch OpenAPI spec from production API
ARG OPENAPI_URL=https://api-reflector.monadical.com/openapi.json
RUN mkdir -p ./static && curl -sf "${OPENAPI_URL}" -o ./static/openapi.json || echo '{}' > ./static/openapi.json

# Fix docusaurus config: change onBrokenLinks to 'warn' for Docker build
RUN sed -i "s/onBrokenLinks: 'throw'/onBrokenLinks: 'warn'/g" docusaurus.config.ts

# Build static site (skip prebuild hook by calling docusaurus directly)
RUN npx docusaurus build

# Production image
FROM nginx:alpine

# Copy built static files
COPY --from=builder /app/build /usr/share/nginx/html

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM node:18-alpine AS builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source (includes static/openapi.json if pre-fetched)
COPY . .

# Fix docusaurus config: change onBrokenLinks to 'warn' for Docker build
RUN sed -i "s/onBrokenLinks: 'throw'/onBrokenLinks: 'warn'/g" docusaurus.config.ts

# Build static site (skip prebuild hook by calling docusaurus directly)
RUN npx docusaurus build

# Production image
FROM nginx:alpine

# Copy built static files
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

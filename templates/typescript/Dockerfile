# Multi-stage Docker build for MCP server
# Stage 1: Build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# Stage 2: Production
FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist/
COPY --from=builder /app/package*.json ./
ENV NODE_ENV=production
RUN npm ci --omit=dev

# {{ENV_VARS}} — AI factory adds required env vars
# ENV API_KEY=""

ENTRYPOINT ["node", "dist/index.js"]

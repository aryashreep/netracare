# --- deps ---
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
# Install dependencies first for layer caching. package.json is created by /speckit-implement.
COPY package.json pnpm-lock.yaml* ./
RUN if [ -f package.json ]; then pnpm install --frozen-lockfile || pnpm install; fi

# --- builder ---
FROM node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN if [ -f package.json ]; then pnpm build; fi

# --- runner ---
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000
CMD ["pnpm", "start"]

# --- Stage 1: build the static assets ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the built JS bundle at build time -- Vite only exposes
# import.meta.env.VITE_* vars that are present in process.env when
# `vite build` runs, so these have to be ARGs (set via --build-arg),
# not runtime environment variables.
ARG VITE_API_BASE_URL
ARG VITE_TELEMETRY_STREAM_URL
ARG VITE_DASHBOARD_ACCESS_TOKEN
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_TELEMETRY_STREAM_URL=${VITE_TELEMETRY_STREAM_URL}
ENV VITE_DASHBOARD_ACCESS_TOKEN=${VITE_DASHBOARD_ACCESS_TOKEN}

RUN npm run build

# --- Stage 2: serve the build with nginx ---
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

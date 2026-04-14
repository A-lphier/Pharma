# Dockerfile - Frontend FatturaMVP
# Node 20 + React + Vite + Nginx

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copia package files per caching
COPY package*.json ./

# Installa dipendenze
RUN npm ci --only=production=false

# Copia sorgenti
COPY . .

# Build per produzione
ENV NODE_ENV=production
RUN npm run build

# Stage 2: Nginx serving
FROM nginx:alpine

# Copia configurazione custom
COPY docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf

# Copia artefatti di build
COPY --from=builder /app/dist /usr/share/nginx/html

# Creo utente nginx custom per sicurezza
RUN adduser -D -u 1000 nginx && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Porte expose
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

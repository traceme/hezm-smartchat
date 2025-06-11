# Multi-stage build for React application
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine as production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built application from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create nginx user and set permissions
RUN addgroup -g 1001 -S smartchat \
    && adduser -S -u 1001 -G smartchat smartchat \
    && chown -R smartchat:smartchat /usr/share/nginx/html \
    && chown -R smartchat:smartchat /var/cache/nginx \
    && chown -R smartchat:smartchat /var/log/nginx \
    && chown -R smartchat:smartchat /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R smartchat:smartchat /var/run/nginx.pid

# Switch to non-root user
USER smartchat

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"] 
FROM node:18-alpine

RUN apk add --no-cache curl

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

COPY server.js ./
RUN mkdir -p public
COPY index.html ./public/index.html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --silent --show-error --fail http://127.0.0.1:3000/health > /dev/null || exit 1

CMD ["node", "server.js"]

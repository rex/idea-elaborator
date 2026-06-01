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

ARG APP_VERSION
ARG APP_GIT_SHA
ARG APP_VERSION_FULL
ARG APP_BUILD_DATE
ENV APP_VERSION=${APP_VERSION} \
    APP_GIT_SHA=${APP_GIT_SHA} \
    APP_VERSION_FULL=${APP_VERSION_FULL} \
    APP_BUILD_DATE=${APP_BUILD_DATE}

CMD ["node", "server.js"]

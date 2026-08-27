# Сборка фронтенда и образ, который его раздаёт.
# nginx получает конфигурацию из ./nginx монтированием — она зависит от
# контура (http или tls) и меняется без пересборки.

FROM node:22-alpine AS build

WORKDIR /app

# Зависимости отдельным слоем: пересобираются только при изменении package.json
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Адрес сайта нужен там, где ссылка обязана быть абсолютной: canonical,
# og:url, sitemap. Не задан — сборка просто не добавит эти теги.
ARG SITE_URL=""
ENV SITE_URL=$SITE_URL

RUN npm run build

# ─────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

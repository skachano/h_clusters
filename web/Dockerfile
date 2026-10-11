# Development: Vite dev server (source mounted, compose.yaml). Production: static build + nginx.
FROM node:22-bookworm-slim AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dev AS build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

FROM node:22-alpine3.22 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/searchem/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

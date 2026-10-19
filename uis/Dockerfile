FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY web /usr/share/nginx/html/uis/web
COPY backoffice /usr/share/nginx/html/uis/backoffice
COPY shared /usr/share/nginx/html/uis/shared

EXPOSE 3000 3001
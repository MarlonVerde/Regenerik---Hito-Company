FROM nginx:1.27-alpine

COPY uis/nginx.conf /etc/nginx/conf.d/default.conf
COPY uis/web /usr/share/nginx/html/uis/web
COPY uis/backoffice /usr/share/nginx/html/uis/backoffice
COPY uis/shared /usr/share/nginx/html/uis/shared
COPY index.html /usr/share/nginx/html/index.html
COPY application.html /usr/share/nginx/html/application.html
COPY validation.js /usr/share/nginx/html/validation.js

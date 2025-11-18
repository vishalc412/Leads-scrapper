# Frontend Dockerfile - Nginx static server
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/

# Copy frontend files
COPY frontend/index.html /usr/share/nginx/html/
COPY frontend/styles.css /usr/share/nginx/html/
COPY frontend/app.js /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

# Nginx will start automatically
CMD ["nginx", "-g", "daemon off;"]

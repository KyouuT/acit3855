# Use an official Nginx image as the base
FROM nginx:alpine

# Copy the project files to the Nginx HTML directory
COPY . /usr/share/nginx/html

# Expose port 80 to access the app
EXPOSE 80

# Start Nginx when the container runs
CMD ["nginx", "-g", "daemon off;"]

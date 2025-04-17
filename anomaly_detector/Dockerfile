# Use the official Python base image
FROM python:3

# Label for metadata
LABEL maintainer="tguicherd@bcit.ca"

# Create and set the working directory
RUN mkdir /app
WORKDIR /app

# Copy only requirements.txt first to leverage Docker's caching mechanism
COPY ./requirements.txt /app/requirements.txt

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the entire application source code
COPY . /app

# Change ownership to a non-privileged user
RUN chown -R nobody:nogroup /app

# Switch to non-privileged user
USER nobody

# Expose the application's port
EXPOSE 8130

# Set the entrypoint and default command to run the Connexion application
ENTRYPOINT ["python3"]
CMD ["app.py"]

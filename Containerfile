FROM registry.access.redhat.com/ubi9/python-311@sha256:7b6cb58d3ff034df7b300800bd89a469d9bd2f739d43250d76b9c9e805307ab5

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ .

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8080 --workers ${WEB_CONCURRENCY:-4} --timeout ${GUNICORN_TIMEOUT:-120} app_streaming:app"]

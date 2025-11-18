# Use slim Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Ensure Python prints are unbuffered
ENV PYTHONUNBUFFERED=1

RUN --mount=type=secret,id=ONEMAP_EMAIL \
    --mount=type=secret,id=ONEMAP_PASSWORD \
    export ONEMAP_EMAIL="$(cat /run/secrets/ONEMAP_EMAIL)" && \
    export ONEMAP_PASSWORD="$(cat /run/secrets/ONEMAP_PASSWORD)" && \
    echo "Email secret loaded" && \
    echo "Password secret loaded"

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port (for example, if using a web app)
EXPOSE 7860

# Run the main script
CMD ["python", "main.py"]
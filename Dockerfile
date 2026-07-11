FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies directly
COPY requirements.txt ./
RUN pip3 install --no-cache-dir flask python-dotenv openai requests flask-sqlalchemy sqlalchemy flask-limiter ibm-watsonx-ai

# Copy all code over
COPY src/ ./src/

# Expose Flask's default port or port 8501 depending on template traffic routing
EXPOSE 8501

# Run the Flask app entry point directly on the required port
ENTRYPOINT ["python3", "src/streamlit_app.py"]
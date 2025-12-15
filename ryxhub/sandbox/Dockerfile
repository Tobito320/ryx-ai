FROM python:3.11-slim

# Install Chromium for browser automation
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 ryxagent
USER ryxagent
WORKDIR /home/ryxagent

# Install Python dependencies in user space
COPY --chown=ryxagent:ryxagent requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy agent code
COPY --chown=ryxagent:ryxagent agent/ ./agent/

# Entrypoint with timeout protection (60s hard limit)
ENTRYPOINT ["timeout", "60s", "python", "-u", "agent/main.py"]

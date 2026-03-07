FROM python:3.12-slim

# System dependencies needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first so this layer is cached independently
# of application code changes.
COPY web/requirements.txt requirements.txt
RUN pip install --no-cache-dir gunicorn -r requirements.txt

# Install the scispaCy model as a separate cached layer (~700 MB).
# Version is pinned to match the scispacy package in requirements.txt.
RUN pip install --no-cache-dir \
    https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Copy application code
COPY web/ .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

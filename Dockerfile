FROM python:3.12-slim

LABEL org.opencontainers.image.title="Super Browser"
LABEL org.opencontainers.image.description="Production-grade AI browser automation"
LABEL org.opencontainers.image.source="https://github.com/user/super-browser"

# System deps for Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY dist/super_browser-*-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/super_browser-*-py3-none-any.whl[browser] \
    && rm /tmp/*.whl

# Install Chromium for Patchright
RUN python -m patchright install chromium

# Copy source for development (optional)
COPY . /app/src/

ENV PYTHONUNBUFFERED=1
ENV SB_HEADLESS=true

ENTRYPOINT ["python", "-m", "super_browser.cli"]
CMD ["version"]

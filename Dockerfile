FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/harish-ai-engineer/disktidy"
LABEL org.opencontainers.image.description="Analyze disk usage and safely reclaim space from Docker, package-manager caches, and other space hogs."
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

# Run disktidy directly; default to the report command.
ENTRYPOINT ["disktidy"]
CMD ["report"]

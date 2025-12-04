# Lightweight worker container for code statistics
FROM alpine:3.19

# Install dependencies
RUN apk add --no-cache \
    git \
    cloc \
    bash \
    jq

# Create workspace
WORKDIR /workspace

# Copy worker script
COPY worker.sh /usr/local/bin/worker.sh
RUN chmod +x /usr/local/bin/worker.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/worker.sh"]

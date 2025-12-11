# Dockerfile for reproducible build environment
# Base: Ubuntu 24.04

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    meson \
    ninja-build \
    libgtk-4-dev \
    libwebkitgtk-6.0-dev \
    libsqlite3-dev \
    libsecret-1-dev \
    libsodium-dev \
    pkg-config \
    clang \
    clang-format \
    clang-tidy \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy source
COPY . .

# Build
RUN meson setup build && meson compile -C build

# Default command: run tests or build
CMD ["meson", "test", "-C", "build"]

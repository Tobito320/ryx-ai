# Build Instructions

## Quick Start

```bash
cd ryxsurf-cpp
meson setup build
meson compile -C build
./build/ryxsurf
```

## Detailed Build Steps

### 1. Install Dependencies

#### Ubuntu 24.04 / Debian 12

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    meson \
    ninja-build \
    libgtk-4-dev \
    libwebkitgtk-6.0-dev \
    libsqlite3-dev \
    libsecret-1-dev \
    libsodium-dev \
    pkg-config
```

#### Arch Linux

```bash
sudo pacman -S \
    base-devel \
    meson \
    ninja \
    gtk4 \
    webkitgtk \
    sqlite \
    libsecret \
    libsodium \
    pkgconf
```

### 2. Configure Build

#### Release Build (Optimized)

```bash
meson setup build --buildtype=release
```

#### Debug Build

```bash
meson setup build --buildtype=debug
```

#### Debug with Sanitizers

```bash
# Address sanitizer
meson setup build --buildtype=debug -Dsanitize=address

# Thread sanitizer
meson setup build --buildtype=debug -Dsanitize=thread

# Undefined behavior sanitizer
meson setup build --buildtype=debug -Dsanitize=undefined
```

### 3. Compile

```bash
meson compile -C build
```

Or using ninja directly:

```bash
cd build
ninja
```

### 4. Run Tests

```bash
meson test -C build
```

### 5. Run Performance Tests

```bash
./perf/run_perf.sh
```

## Troubleshooting

### Missing Dependencies

If Meson reports missing dependencies:

```bash
pkg-config --modversion gtk4
pkg-config --modversion webkitgtk-6.0
```

### WebKitGTK Version

Ensure WebKitGTK 6.0 (not 4.0) is installed:

```bash
pkg-config --modversion webkitgtk-6.0
```

Should show version >= 2.40.

### Compiler Issues

Ensure your compiler supports C++17:

```bash
g++ --version  # Should be GCC 8+ or Clang 8+
```

## Build Options

Configure build options:

```bash
meson configure build
```

Available options:
- `buildtype`: release, debug, debugoptimized
- `sanitize`: none, address, thread, undefined
- `tests`: true/false (enable test build)

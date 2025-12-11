# Build Instructions

## Quick Start

```bash
# Clone or navigate to project directory
cd minimal-browser

# Setup build directory
meson setup build

# Compile
meson compile -C build

# Run
./build/minimal-browser
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
    pkg-config \
    clang \
    clang-format \
    clang-tidy
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
    pkgconf \
    clang \
    clang-format \
    clang-tidy
```

#### Fedora

```bash
sudo dnf install -y \
    gcc-c++ \
    meson \
    ninja-build \
    gtk4-devel \
    webkitgtk6-devel \
    sqlite-devel \
    libsecret-devel \
    libsodium-devel \
    pkgconfig \
    clang \
    clang-tools-extra
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

### 4. Install (Optional)

```bash
meson install -C build
```

This installs to the default prefix (usually `/usr/local`). To install to a custom prefix:

```bash
meson setup build --prefix=/usr
meson install -C build
```

### 5. Run Tests (if enabled)

```bash
meson test -C build
```

## Docker Build Environment

For a reproducible build environment, use the provided Dockerfile:

```bash
# Build Docker image
docker build -t minimal-browser-build -f docker/Dockerfile .

# Run build in container
docker run --rm -v $(pwd):/workspace minimal-browser-build
```

## Troubleshooting

### Missing Dependencies

If Meson reports missing dependencies:

```bash
# Check what's missing
pkg-config --modversion gtk4
pkg-config --modversion webkitgtk-6.0

# Install missing packages (see dependency list above)
```

### WebKitGTK Version

Ensure WebKitGTK 6.0 (not 4.0) is installed:

```bash
pkg-config --modversion webkitgtk-6.0
```

Should show version >= 2.40.

### Compiler Issues

If you encounter C++17 feature errors, ensure your compiler supports C++17:

```bash
g++ --version  # Should be GCC 8+ or Clang 8+
```

### Linker Errors

If you get undefined reference errors, ensure all development packages are installed (not just runtime libraries).

## Build Options

Configure build options:

```bash
meson configure build
```

Available options:
- `buildtype`: release, debug, debugoptimized
- `sanitize`: none, address, thread, undefined
- `tests`: true/false (enable test build)

## Cross-Compilation

For cross-compilation, create a cross file:

```ini
[binaries]
c = 'x86_64-linux-gnu-gcc'
cpp = 'x86_64-linux-gnu-g++'
pkgconfig = 'x86_64-linux-gnu-pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
```

Then:

```bash
meson setup build --cross-file cross-file.ini
```

## Performance Build Flags

For maximum performance (release build):

```bash
meson setup build --buildtype=release \
    -Dcpp_args='-O3 -march=native -flto -DNDEBUG'
```

These flags are already set in `meson.build` for release builds.

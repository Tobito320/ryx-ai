project(
  'ryxsurf-cpp',
  'cpp',
  version: '0.1.0',
  license: 'MIT',
  default_options: [
    'cpp_std=c++17',
    'warning_level=3',
    'werror=false',
    'optimization=3',
    'b_lto=true',
  ],
)

# Dependencies
gtk4_dep = dependency('gtk4', version: '>=4.0')
webkitgtk_dep = dependency('webkitgtk-6.0', version: '>=2.40')
sqlite3_dep = dependency('sqlite3')
libsecret_dep = dependency('libsecret-1')
libsodium_dep = dependency('libsodium')
cairo_dep = dependency('cairo')

# Compiler flags
cpp = meson.get_compiler('cpp')
cpp_args = []

# Release flags
if get_option('buildtype') == 'release'
  cpp_args += [
    '-O3',
    '-march=native',
    '-DNDEBUG',
    '-flto',
  ]
endif

# Debug flags
if get_option('buildtype') == 'debug'
  cpp_args += [
    '-g',
    '-O0',
  ]
endif

# Sanitizers (optional)
if get_option('sanitize') != 'none'
  if get_option('sanitize') == 'address'
    cpp_args += ['-fsanitize=address', '-fno-omit-frame-pointer']
  elif get_option('sanitize') == 'thread'
    cpp_args += ['-fsanitize=thread']
  elif get_option('sanitize') == 'undefined'
    cpp_args += ['-fsanitize=undefined']
  endif
endif

# Include directories
inc_dir = include_directories('include')

# Source files
library_sources = files(
  'src/browser_window.cpp',
  'src/tab.cpp',
  'src/keyboard_handler.cpp',
  'src/session_manager.cpp',
  'src/session.cpp',
  'src/workspace.cpp',
  'src/snapshot_manager.cpp',
  'src/tab_unload_manager.cpp',
  'src/crypto.cpp',
  'src/persistence_manager.cpp',
  'src/password_manager.cpp',
  'src/theme_manager.cpp',
)

# Install CSS theme
install_data('data/theme.css', install_dir: get_option('datadir') / 'ryxsurf')

# Core library (static) reused by app and tests
ryxsurf_lib = static_library(
  'ryxsurf_core',
  library_sources,
  include_directories: inc_dir,
  dependencies: [
    gtk4_dep,
    webkitgtk_dep,
    sqlite3_dep,
    libsecret_dep,
    libsodium_dep,
    cairo_dep,
  ],
  cpp_args: cpp_args,
)

# Executable
executable(
  'ryxsurf',
  'src/main.cpp',
  link_with: ryxsurf_lib,
  dependencies: [
    gtk4_dep,
    webkitgtk_dep,
    sqlite3_dep,
    libsecret_dep,
    libsodium_dep,
    cairo_dep,
  ],
  include_directories: inc_dir,
  cpp_args: cpp_args,
  install: true,
  install_dir: get_option('bindir'),
)

# Tests
if get_option('tests')
  catch2_dep = dependency('catch2', required: false)
  catch_inc = inc_dir
  catch_deps = [gtk4_dep, webkitgtk_dep, sqlite3_dep, libsecret_dep, libsodium_dep, cairo_dep]
  if catch2_dep.found()
    catch_deps += catch2_dep
  else
    catch_inc = [inc_dir, include_directories('third_party')]
  endif

  test_sources = files(
    'tests/main.cpp',
    'tests/test_tab.cpp',
    'tests/test_session_manager.cpp',
    'tests/test_unload.cpp',
    'tests/test_persistence.cpp',
    'tests/test_password_manager.cpp',
  )

  test_exe = executable(
    'test_ryxsurf',
    test_sources,
    include_directories: catch_inc,
    dependencies: catch_deps,
    link_with: ryxsurf_lib,
    cpp_args: cpp_args,
  )
  test('ryxsurf-cpp', test_exe)
endif

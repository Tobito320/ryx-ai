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
sources = files(
  'src/main.cpp',
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
)

# Executable
executable(
  'ryxsurf',
  sources,
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
  install: true,
)

# Tests
if get_option('tests')
  catch2_dep = dependency('catch2', required: false)
  if catch2_dep.found()
    test_sources = files(
      'tests/test_tab.cpp',
      'tests/test_session_manager.cpp',
      'tests/test_unload.cpp',
      'tests/test_persistence.cpp',
    )
    test_exe = executable(
      'test_ryxsurf',
      test_sources,
      include_directories: inc_dir,
      dependencies: [catch2_dep],
      cpp_args: cpp_args,
    )
    test('Tab Tests', test_exe)
  endif
endif

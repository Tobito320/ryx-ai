"""
RyxSurf CLI

Command-line interface for browser management.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def cmd_start(args):
    """Start the browser"""
    print("🚀 Starting RyxSurf...")
    
    if args.fast:
        print("⚡ Using fast mode")
        from src.core.browser_fast import create_fast_app
        app = create_fast_app()
    else:
        # Use regular browser
        print("Using standard mode")
        # TODO: Import regular browser
        return
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Browser closed")


def cmd_health(args):
    """Run health check"""
    from src.core.health_check import run_health_check
    
    config_dir = Path.home() / ".config" / "ryxsurf"
    healthy = run_health_check(config_dir, auto_fix=args.fix)
    
    sys.exit(0 if healthy else 1)


def cmd_update(args):
    """Check for updates"""
    from src.core.auto_update import AutoUpdater
    
    config_dir = Path.home() / ".config" / "ryxsurf"
    updater = AutoUpdater(config_dir, auto_install=args.install)
    
    if args.install:
        updater.manual_update()
    else:
        updater.check_and_notify()


def cmd_benchmark(args):
    """Benchmark browser performance"""
    import time
    import subprocess
    
    print("⏱️  Benchmarking startup time...")
    
    times = []
    for i in range(args.runs):
        print(f"  Run {i+1}/{args.runs}...", end=" ", flush=True)
        
        start = time.time()
        try:
            # Start browser and immediately close
            proc = subprocess.Popen(
                [sys.executable, "-c", 
                 "from src.core.browser_fast import create_fast_app; "
                 "app = create_fast_app(); import time; time.sleep(1)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"{elapsed:.3f}s")
    
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n📊 Results:")
    print(f"  Average: {avg:.3f}s")
    print(f"  Min:     {min_time:.3f}s")
    print(f"  Max:     {max_time:.3f}s")


def cmd_clean(args):
    """Clean cache and temporary files"""
    import shutil
    
    config_dir = Path.home() / ".config" / "ryxsurf"
    
    items_to_clean = []
    
    if args.cache:
        items_to_clean.append(config_dir / "cache")
    
    if args.logs:
        items_to_clean.append(config_dir / "ryxsurf.log")
    
    if args.all:
        items_to_clean = [
            config_dir / "cache",
            config_dir / "ryxsurf.log",
        ]
    
    for item in items_to_clean:
        if item.exists():
            if item.is_dir():
                shutil.rmtree(item)
                item.mkdir()
                print(f"✓ Cleaned: {item.name}/")
            else:
                item.unlink()
                print(f"✓ Removed: {item.name}")
    
    print(f"\n🧹 Clean complete")


def cmd_info(args):
    """Show browser information"""
    from src.core.lazy_loader import create_lazy_loader
    
    print("\n" + "="*60)
    print("ℹ️  RYXSURF INFORMATION")
    print("="*60)
    
    # Version
    from src.core.auto_update import UpdateChecker
    version = UpdateChecker.CURRENT_VERSION
    print(f"Version:     {version}")
    
    # Config directory
    config_dir = Path.home() / ".config" / "ryxsurf"
    print(f"Config Dir:  {config_dir}")
    
    # Check if directories exist
    exists = config_dir.exists()
    print(f"Initialized: {'Yes' if exists else 'No'}")
    
    if exists:
        # Count files
        data_files = len(list((config_dir / "data").glob("*"))) if (config_dir / "data").exists() else 0
        cache_files = len(list((config_dir / "cache").glob("*"))) if (config_dir / "cache").exists() else 0
        
        print(f"Data Files:  {data_files}")
        print(f"Cache Files: {cache_files}")
        
        # Settings
        settings_file = config_dir / "settings.json"
        if settings_file.exists():
            size_kb = settings_file.stat().st_size / 1024
            print(f"Settings:    {size_kb:.1f} KB")
    
    # Features
    loader = create_lazy_loader()
    print(f"\nFeatures:    {len(loader.modules)} available")
    
    # Python version
    print(f"Python:      {sys.version.split()[0]}")
    
    print("="*60 + "\n")


def cmd_profile(args):
    """Profile browser startup"""
    import cProfile
    import pstats
    from io import StringIO
    
    print("📊 Profiling browser startup...")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Start browser (fast mode)
    from src.core.browser_fast import create_fast_app
    app = create_fast_app()
    
    profiler.disable()
    
    # Print stats
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(args.lines)
    
    print(stream.getvalue())


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="ryxsurf",
        description="RyxSurf - Privacy-first browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ryxsurf                    Start browser
  ryxsurf --fast             Start in fast mode
  ryxsurf health             Run health check
  ryxsurf health --fix       Run health check and auto-fix
  ryxsurf update             Check for updates
  ryxsurf benchmark          Benchmark startup time
  ryxsurf clean --cache      Clean cache
  ryxsurf info               Show browser info
        """
    )
    
    # Global options
    parser.add_argument("--fast", action="store_true", help="Use fast startup mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version="RyxSurf 0.1.0")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Run health check")
    health_parser.add_argument("--fix", action="store_true", help="Auto-fix issues")
    health_parser.set_defaults(func=cmd_health)
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Check for updates")
    update_parser.add_argument("--install", action="store_true", help="Auto-install updates")
    update_parser.set_defaults(func=cmd_update)
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark performance")
    benchmark_parser.add_argument("--runs", type=int, default=5, help="Number of runs")
    benchmark_parser.set_defaults(func=cmd_benchmark)
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean cache and logs")
    clean_parser.add_argument("--cache", action="store_true", help="Clean cache only")
    clean_parser.add_argument("--logs", action="store_true", help="Clean logs only")
    clean_parser.add_argument("--all", action="store_true", help="Clean everything")
    clean_parser.set_defaults(func=cmd_clean)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show browser information")
    info_parser.set_defaults(func=cmd_info)
    
    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Profile startup")
    profile_parser.add_argument("--lines", type=int, default=20, help="Number of lines to show")
    profile_parser.set_defaults(func=cmd_profile)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set debug logging
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Execute command
    if args.command:
        args.func(args)
    else:
        # No command - start browser
        cmd_start(args)


if __name__ == "__main__":
    main()

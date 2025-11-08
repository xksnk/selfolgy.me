#!/usr/bin/env python3
"""
Script to show project structure with line counts for each file
"""
import os
from pathlib import Path
from collections import defaultdict

def count_lines(filepath):
    """Count non-empty lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line for line in f if line.strip()]
            return len(lines)
    except:
        return 0

def get_file_type(filepath):
    """Get file extension"""
    return filepath.suffix

def should_skip(path):
    """Check if path should be skipped"""
    skip_dirs = {
        '__pycache__', '.git', 'venv', 'node_modules',
        '.pytest_cache', '.mypy_cache', 'eggs', '.eggs',
        'build', 'dist', '*.egg-info'
    }

    # Check if any part of the path contains skip directories
    parts = Path(path).parts
    return any(skip in parts for skip in skip_dirs)

def build_tree(root_path, max_depth=10):
    """Build directory tree with file statistics"""
    root = Path(root_path)
    tree_data = {}
    stats = defaultdict(lambda: {'files': 0, 'lines': 0})

    def walk_dir(path, depth=0, prefix=""):
        if depth > max_depth or should_skip(path):
            return

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            return

        dirs = [item for item in items if item.is_dir() and not should_skip(item)]
        files = [item for item in items if item.is_file() and not should_skip(item)]

        # Process directories first
        for i, dir_path in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            connector = "└── " if is_last_dir else "├── "
            print(f"{prefix}{connector}{dir_path.name}/")

            extension = "    " if is_last_dir else "│   "
            walk_dir(dir_path, depth + 1, prefix + extension)

        # Process files
        for i, file_path in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "

            lines = count_lines(file_path)
            ext = file_path.suffix

            # Update statistics
            if ext:
                stats[ext]['files'] += 1
                stats[ext]['lines'] += lines

            # Color code by file type
            if lines > 0:
                size_info = f"({lines:,} lines)"
            else:
                size_info = "(empty)"

            print(f"{prefix}{connector}{file_path.name} {size_info}")

    print(f"\n{'='*80}")
    print(f"📁 PROJECT STRUCTURE: {root.name}")
    print(f"{'='*80}\n")
    print(f"{root.name}/")
    walk_dir(root)

    return stats

def print_statistics(stats):
    """Print file type statistics"""
    print(f"\n{'='*80}")
    print(f"📊 PROJECT STATISTICS")
    print(f"{'='*80}\n")

    # Sort by total lines
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['lines'], reverse=True)

    total_files = sum(s['files'] for s in stats.values())
    total_lines = sum(s['lines'] for s in stats.values())

    print(f"{'File Type':<15} {'Files':>10} {'Lines':>15} {'Avg Lines':>12}")
    print(f"{'-'*55}")

    for ext, data in sorted_stats:
        ext_name = ext if ext else '(no ext)'
        avg_lines = data['lines'] // data['files'] if data['files'] > 0 else 0
        print(f"{ext_name:<15} {data['files']:>10} {data['lines']:>15,} {avg_lines:>12,}")

    print(f"{'-'*55}")
    print(f"{'TOTAL':<15} {total_files:>10} {total_lines:>15,}")
    print()

if __name__ == "__main__":
    project_root = "/home/user/selfolgy.me"

    # Build tree and get statistics
    stats = build_tree(project_root, max_depth=5)

    # Print summary statistics
    print_statistics(stats)

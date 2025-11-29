#!/usr/bin/env python3
"""
Test RAG documentation query
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.rag_system import RAGSystem

def main():
    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  RAG Documentation Query Test       │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()

    rag = RAGSystem()

    # Test queries related to the ingested Hyprland documentation
    test_queries = [
        "arch-wiki hyprland",
        "hyprland configuration",
        "arch linux hyprland",
        "wayland compositor hyprland"
    ]

    for query in test_queries:
        print(f"\033[1;33mQuery:\033[0m {query}")

        # Try to recall from knowledge base
        result = rag.recall_file_location(query)

        if result:
            print(f"  \033[1;32m✓ Found!\033[0m")
            print(f"  File type: {result['file_type']}")
            print(f"  Source: {result['file_path']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Preview: {result['preview'][:150]}...")
        else:
            print(f"  \033[1;31m✗ Not found\033[0m")

        print()

    # Show stats
    stats = rag.get_stats()
    print("\033[1;36mRAG Stats:\033[0m")
    print(f"  Total cache entries: {stats['total_cache_entries']}")
    print(f"  Total knowledge entries: {stats['total_knowledge_entries']}")
    print()

if __name__ == "__main__":
    main()

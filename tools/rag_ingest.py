"""
Ryx AI - RAG Ingestion System
Processes scraped documentation into RAG knowledge base
"""

import sys
from pathlib import Path
from typing import List, Dict
import shutil
from datetime import datetime
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rag_system import RAGSystem


class RAGIngestor:
    """Ingest scraped documentation into RAG knowledge base"""

    def __init__(self):
        self.scrape_dir = Path.home() / "ryx-ai" / "data" / "scrape"
        self.rag_dir = Path.home() / "ryx-ai" / "data" / "rag"
        self.rag_system = RAGSystem()

        # Ensure directories exist
        self.scrape_dir.mkdir(parents=True, exist_ok=True)
        self.rag_dir.mkdir(parents=True, exist_ok=True)

    def ingest_all(self, category: str = None) -> Dict:
        """
        Ingest all scraped documents into RAG

        Args:
            category: Optional category filter (arch-wiki, documentation, etc)

        Returns:
            Stats about ingestion
        """
        stats = {
            'total_files': 0,
            'ingested': 0,
            'failed': 0,
            'skipped': 0
        }

        # Get all text files
        if category:
            search_dir = self.scrape_dir / category
            if not search_dir.exists():
                print(f"\033[1;31m✗\033[0m Category not found: {category}")
                return stats
            files = list(search_dir.glob("*.txt"))
        else:
            files = list(self.scrape_dir.glob("**/*.txt"))

        stats['total_files'] = len(files)

        if not files:
            print("\033[1;33m○\033[0m No files found to ingest")
            return stats

        print(f"\033[1;36m▸\033[0m Found {len(files)} files to process")
        print()

        for file_path in files:
            try:
                result = self.ingest_file(file_path)
                if result:
                    stats['ingested'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                print(f"\033[1;31m✗\033[0m Failed to ingest {file_path.name}: {e}")
                stats['failed'] += 1

        # Display summary
        self._display_summary(stats)

        return stats

    def ingest_file(self, file_path: Path) -> bool:
        """
        Ingest a single file into RAG

        Returns:
            True if successfully ingested, False if skipped
        """
        print(f"\033[1;36m▸\033[0m Processing: {file_path.name}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse document
        doc = self._parse_document(content)

        if not doc:
            print(f"  \033[1;33m⚠\033[0m Skipped (could not parse)")
            return False

        # Extract knowledge chunks
        chunks = self._extract_chunks(doc['content'])

        if not chunks:
            print(f"  \033[1;33m⚠\033[0m Skipped (no extractable content)")
            return False

        # Add to RAG system
        category = file_path.parent.name
        for i, chunk in enumerate(chunks):
            # Store each chunk as a knowledge item
            self.rag_system.learn_from_documentation(
                topic=doc['title'],
                content=chunk,
                source=doc['url'],
                category=category
            )

        # Move to processed directory
        dest_category = self.rag_dir / category
        dest_category.mkdir(parents=True, exist_ok=True)
        dest_path = dest_category / file_path.name

        shutil.move(str(file_path), str(dest_path))

        print(f"  \033[1;32m✓\033[0m Ingested {len(chunks)} chunks → {category}/")

        return True

    def _parse_document(self, content: str) -> Dict:
        """Parse scraped document format"""
        try:
            # Extract title
            title_match = re.search(r'Title: (.+)', content)
            title = title_match.group(1).strip() if title_match else "Unknown"

            # Extract URL
            url_match = re.search(r'URL: (.+)', content)
            url = url_match.group(1).strip() if url_match else "Unknown"

            # Extract main content (between CONTENT markers)
            content_match = re.search(
                r'─+\nCONTENT\n─+\n(.+?)\n─+',
                content,
                re.DOTALL
            )
            main_content = content_match.group(1).strip() if content_match else ""

            return {
                'title': title,
                'url': url,
                'content': main_content
            }
        except Exception as e:
            print(f"  \033[1;31m✗\033[0m Parse error: {e}")
            return None

    def _extract_chunks(self, content: str, chunk_size: int = 500) -> List[str]:
        """
        Split content into manageable chunks for RAG

        Args:
            content: Full document content
            chunk_size: Target size for each chunk (words)

        Returns:
            List of content chunks
        """
        if not content or len(content.strip()) < 50:
            return []

        # Split by paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            word_count = len(para.split())

            if current_word_count + word_count > chunk_size and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_word_count = word_count
            else:
                current_chunk.append(para)
                current_word_count += word_count

        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _display_summary(self, stats: Dict):
        """Display ingestion summary"""
        print()
        print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  RAG Ingestion Summary              │\033[0m")
        print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()
        print(f"  Total files: {stats['total_files']}")
        print(f"  \033[1;32m✓\033[0m Ingested: {stats['ingested']}")
        print(f"  \033[1;33m○\033[0m Skipped: {stats['skipped']}")
        print(f"  \033[1;31m✗\033[0m Failed: {stats['failed']}")
        print()


def main():
    """CLI interface for RAG ingestion"""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest scraped docs into RAG')
    parser.add_argument('--category', '-c', help='Category to ingest (e.g., arch-wiki)')
    parser.add_argument('--list', '-l', action='store_true', help='List available categories')

    args = parser.parse_args()

    ingestor = RAGIngestor()

    if args.list:
        # List categories
        categories = [d.name for d in ingestor.scrape_dir.iterdir() if d.is_dir()]
        print("\033[1;36mAvailable categories:\033[0m")
        for cat in categories:
            file_count = len(list((ingestor.scrape_dir / cat).glob("*.txt")))
            print(f"  • {cat} ({file_count} files)")
        return

    # Ingest
    ingestor.ingest_all(category=args.category)


if __name__ == "__main__":
    main()

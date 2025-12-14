"""
Memory Compression

Compress inactive tab memory to reduce RAM usage.
"""

import logging
import zlib
import pickle
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import time

log = logging.getLogger("ryxsurf.compress")


@dataclass
class CompressedData:
    """Compressed data container"""
    compressed: bytes
    original_size: int
    compressed_size: int
    timestamp: float = field(default_factory=time.time)
    compression_ratio: float = 0.0
    
    def __post_init__(self):
        self.compression_ratio = self.compressed_size / self.original_size if self.original_size > 0 else 0


class MemoryCompressor:
    """Compress and decompress memory data"""
    
    def __init__(self, compression_level: int = 6):
        """
        Initialize compressor
        
        Args:
            compression_level: 1-9, higher = better compression but slower
        """
        self.compression_level = compression_level
        self.compressed_data: Dict[str, CompressedData] = {}
        
        self.stats = {
            "total_compressed": 0,
            "total_decompressed": 0,
            "bytes_saved": 0,
            "compression_time": 0.0,
            "decompression_time": 0.0,
        }
        
        log.info(f"Memory compressor initialized (level {compression_level})")
    
    def compress(self, key: str, data: Any) -> bool:
        """Compress data"""
        try:
            start = time.perf_counter()
            
            # Serialize data
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            original_size = len(serialized)
            
            # Compress
            compressed = zlib.compress(serialized, level=self.compression_level)
            compressed_size = len(compressed)
            
            elapsed = time.perf_counter() - start
            
            # Store
            self.compressed_data[key] = CompressedData(
                compressed=compressed,
                original_size=original_size,
                compressed_size=compressed_size,
            )
            
            # Update stats
            self.stats["total_compressed"] += 1
            self.stats["bytes_saved"] += (original_size - compressed_size)
            self.stats["compression_time"] += elapsed
            
            ratio = compressed_size / original_size
            log.debug(f"Compressed {key}: {original_size//1024}KB → {compressed_size//1024}KB ({ratio:.0%}) in {elapsed*1000:.1f}ms")
            
            return True
        
        except Exception as e:
            log.error(f"Failed to compress {key}: {e}")
            return False
    
    def decompress(self, key: str) -> Optional[Any]:
        """Decompress data"""
        if key not in self.compressed_data:
            return None
        
        try:
            start = time.perf_counter()
            
            compressed_data = self.compressed_data[key]
            
            # Decompress
            decompressed = zlib.decompress(compressed_data.compressed)
            
            # Deserialize
            data = pickle.loads(decompressed)
            
            elapsed = time.perf_counter() - start
            
            # Update stats
            self.stats["total_decompressed"] += 1
            self.stats["decompression_time"] += elapsed
            
            log.debug(f"Decompressed {key} in {elapsed*1000:.1f}ms")
            
            return data
        
        except Exception as e:
            log.error(f"Failed to decompress {key}: {e}")
            return None
    
    def has_compressed(self, key: str) -> bool:
        """Check if key has compressed data"""
        return key in self.compressed_data
    
    def remove(self, key: str) -> bool:
        """Remove compressed data"""
        if key in self.compressed_data:
            del self.compressed_data[key]
            return True
        return False
    
    def get_compressed_size(self, key: str) -> int:
        """Get compressed size for key"""
        if key in self.compressed_data:
            return self.compressed_data[key].compressed_size
        return 0
    
    def get_original_size(self, key: str) -> int:
        """Get original size for key"""
        if key in self.compressed_data:
            return self.compressed_data[key].original_size
        return 0
    
    def get_total_compressed_size(self) -> int:
        """Get total compressed size"""
        return sum(cd.compressed_size for cd in self.compressed_data.values())
    
    def get_total_original_size(self) -> int:
        """Get total original size"""
        return sum(cd.original_size for cd in self.compressed_data.values())
    
    def get_stats(self) -> Dict:
        """Get compression statistics"""
        total_original = self.get_total_original_size()
        total_compressed = self.get_total_compressed_size()
        
        overall_ratio = total_compressed / total_original if total_original > 0 else 0
        
        avg_compression_time = (
            self.stats["compression_time"] / self.stats["total_compressed"] 
            if self.stats["total_compressed"] > 0 else 0
        )
        
        avg_decompression_time = (
            self.stats["decompression_time"] / self.stats["total_decompressed"]
            if self.stats["total_decompressed"] > 0 else 0
        )
        
        return {
            **self.stats,
            "compressed_items": len(self.compressed_data),
            "total_compressed_mb": total_compressed / (1024 * 1024),
            "total_original_mb": total_original / (1024 * 1024),
            "overall_ratio": overall_ratio,
            "avg_compression_ms": avg_compression_time * 1000,
            "avg_decompression_ms": avg_decompression_time * 1000,
        }
    
    def clear(self):
        """Clear all compressed data"""
        self.compressed_data.clear()
        log.info("Compressed data cleared")
    
    def set_compression_level(self, level: int):
        """Set compression level (1-9)"""
        if 1 <= level <= 9:
            self.compression_level = level
            log.info(f"Compression level set to {level}")
        else:
            log.warning(f"Invalid compression level {level}, must be 1-9")


class TabMemoryCompressor:
    """Compress tab memory data"""
    
    def __init__(self, compression_level: int = 6):
        self.compressor = MemoryCompressor(compression_level)
        self.tab_data: Dict[str, Dict] = {}
        
        log.info("Tab memory compressor initialized")
    
    def compress_tab(self, tab_id: str, tab_data: Dict) -> bool:
        """Compress tab data"""
        # Store metadata
        self.tab_data[tab_id] = {
            "url": tab_data.get("url", ""),
            "title": tab_data.get("title", ""),
            "timestamp": time.time(),
        }
        
        # Compress the actual data
        return self.compressor.compress(tab_id, tab_data)
    
    def decompress_tab(self, tab_id: str) -> Optional[Dict]:
        """Decompress tab data"""
        return self.compressor.decompress(tab_id)
    
    def has_tab(self, tab_id: str) -> bool:
        """Check if tab is compressed"""
        return tab_id in self.tab_data
    
    def remove_tab(self, tab_id: str):
        """Remove compressed tab"""
        if tab_id in self.tab_data:
            del self.tab_data[tab_id]
        self.compressor.remove(tab_id)
    
    def get_tab_list(self) -> list:
        """Get list of compressed tabs"""
        return [
            {
                "tab_id": tab_id,
                "url": data["url"],
                "title": data["title"],
                "timestamp": data["timestamp"],
                "compressed_size": self.compressor.get_compressed_size(tab_id),
                "original_size": self.compressor.get_original_size(tab_id),
            }
            for tab_id, data in self.tab_data.items()
        ]
    
    def get_stats(self) -> Dict:
        """Get tab compression statistics"""
        stats = self.compressor.get_stats()
        stats["compressed_tabs"] = len(self.tab_data)
        return stats
    
    def clear(self):
        """Clear all compressed tabs"""
        self.tab_data.clear()
        self.compressor.clear()
        log.info("All compressed tabs cleared")


def create_memory_compressor(**kwargs) -> MemoryCompressor:
    """Create memory compressor"""
    return MemoryCompressor(**kwargs)


def create_tab_compressor(**kwargs) -> TabMemoryCompressor:
    """Create tab memory compressor"""
    return TabMemoryCompressor(**kwargs)

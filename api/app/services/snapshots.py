import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog

logger = structlog.get_logger()

class SnapshotService:
    def __init__(self):
        self.base_path = Path("/data/snapshots")
        self.ensure_directory()
    
    def ensure_directory(self):
        """Ensure snapshot directory exists"""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_html_snapshot(
        self,
        url: str,
        html_content: str,
        source: str,
        published_at: datetime
    ) -> str:
        """
        Save HTML snapshot to local filesystem
        Returns: relative path to snapshot file
        """
        
        # Generate filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        date_str = published_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{date_str}_{url_hash}.html"
        
        # Create source-specific subdirectory
        source_dir = self.base_path / source.lower()
        source_dir.mkdir(exist_ok=True)
        
        # Full path
        filepath = source_dir / filename
        
        try:
            # Write HTML content
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add metadata header
                f.write(f"<!-- URL: {url} -->\n")
                f.write(f"<!-- Source: {source} -->\n")
                f.write(f"<!-- Published: {published_at.isoformat()} -->\n")
                f.write(f"<!-- Saved: {datetime.now().isoformat()} -->\n")
                f.write("\n")
                f.write(html_content)
            
            # Return relative path
            relative_path = f"snapshots/{source.lower()}/{filename}"
            
            logger.info(
                "HTML snapshot saved",
                url=url,
                source=source,
                path=relative_path
            )
            
            return relative_path
            
        except Exception as e:
            logger.error(
                "Failed to save HTML snapshot",
                url=url,
                error=str(e)
            )
            raise
    
    def get_snapshot_path(self, relative_path: str) -> Optional[Path]:
        """Get full path for a snapshot"""
        if not relative_path:
            return None
        
        # Remove 'snapshots/' prefix if present
        if relative_path.startswith("snapshots/"):
            relative_path = relative_path[10:]
        
        full_path = self.base_path / relative_path
        
        if full_path.exists():
            return full_path
        
        return None
    
    def read_snapshot(self, relative_path: str) -> Optional[str]:
        """Read snapshot content"""
        full_path = self.get_snapshot_path(relative_path)
        
        if not full_path:
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(
                "Failed to read snapshot",
                path=relative_path,
                error=str(e)
            )
            return None
    
    def cleanup_old_snapshots(self, days: int = 30):
        """Clean up snapshots older than specified days"""
        # Placeholder for future implementation
        # Would iterate through snapshots and delete old ones
        pass
    
    def migrate_to_s3(self, bucket_name: str, prefix: str = "snapshots/"):
        """
        Placeholder for future S3 migration
        Would upload local snapshots to S3 with versioning/WORM
        """
        pass

# Global instance
snapshot_service = SnapshotService()
# core/backup_manager.py
import shutil
import json
from pathlib import Path
from datetime import datetime
import zipfile
from typing import Dict, List, Optional
from utils.logger import logger

class BackupManager:
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self, db_name: str) -> Optional[str]:
        """Create a backup of a database"""
        try:
            db_path = Path("db") / db_name
            if not db_path.exists():
                raise FileNotFoundError(f"Database {db_name} not found")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{db_name}_{timestamp}.zip"
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in db_path.glob("**/*"):
                    if file.is_file():
                        zipf.write(file, arcname=file.relative_to(db_path.parent))
            
            logger.log_operation(
                "BACKUP_CREATE",
                f"db:{db_name}",
                "SUCCESS",
                f"path:{backup_path}"
            )
            return str(backup_path)
        except Exception as e:
            logger.log_operation(
                "BACKUP_CREATE",
                f"db:{db_name}",
                "FAILED",
                str(e)
            )
            raise
    
    def restore_backup(self, backup_name: str, db_name: Optional[str] = None) -> str:
        try:
            # Search for a backup file starting with the provided name
            candidates = list(self.backup_dir.glob(f"{backup_name}_*.zip"))
            if not candidates:
                raise FileNotFoundError(f"No backup file found for prefix '{backup_name}'")
            
            # Choose the latest backup by modification time
            backup_path = max(candidates, key=lambda p: p.stat().st_mtime)

            if db_name is None:
                db_name = backup_name

            db_path = Path("db") / db_name

            if db_path.exists():
                shutil.rmtree(db_path)
            db_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(".")

            logger.log_operation(
                "BACKUP_RESTORE",
                f"db:{db_name}",
                "SUCCESS",
                f"path:{backup_path}"
            )
            return f"Restored database '{db_name}' from '{backup_path.name}'"
        except Exception as e:
            logger.log_operation(
                "BACKUP_RESTORE",
                f"db:{db_name or backup_name}",
                "FAILED",
                str(e)
            )
            raise

    def list_backups(self, db_name: Optional[str] = None) -> List[Dict]:
        """List available backups"""
        backups = []
        for backup_file in self.backup_dir.glob("*.zip"):
            parts = backup_file.stem.split('_')
            if len(parts) >= 2:
                backup_db = parts[0]
                timestamp = '_'.join(parts[1:])
                
                if db_name and backup_db != db_name:
                    continue
                    
                backups.append({
                    "db_name": backup_db,
                    "timestamp": timestamp,
                    "path": str(backup_file),
                    "size": backup_file.stat().st_size
                })
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
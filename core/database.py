# database.py
import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid
from core.collection import Collection
from utils.helpers import validate_db_name
from utils.logger import logger

class Database:
    def __init__(self, name: str, db_path: str = "db"):
        validate_db_name(name)
        self.name = name
        self.db_path = Path(db_path) / name
        self.collections: Dict[str, Collection] = {}
        self._transaction_log_path = self.db_path / ".transactions"
        self._active_transaction: Optional[str] = None
        self._transaction_operations: List[Dict] = []
        self._ensure_db_directory()
        self._ensure_transaction_log()

    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist"""
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.log_operation("ERROR", "DB_DIR_CREATION", self.name, f"Failed to create DB directory: {e}")
            raise

    def _ensure_transaction_log(self):
        """Initialize transaction log directory"""
        try:
            self._transaction_log_path.mkdir(exist_ok=True)
        except OSError as e:
            logger.log_operation("ERROR", "TX_LOG_DIR_CREATION", self.name, f"Failed to create transaction log directory: {e}")
            raise

    def begin_transaction(self) -> str:
        """Start a new transaction"""
        if self._active_transaction:
            raise RuntimeError("Transaction already in progress")
        
        transaction_id = str(uuid.uuid4())
        self._active_transaction = transaction_id
        self._transaction_operations = []
        
        # Create transaction log file
        try:
            log_file = self._transaction_log_path / f"{transaction_id}.log"
            log_file.touch()
        except OSError as e:
            logger.log_operation("ERROR", "TX_LOG_CREATION", self.name, f"Failed to create transaction log: {e}")
            raise
        
        logger.log_operation("TRANSACTION", "BEGIN", self.name, f"Transaction {transaction_id} started")
        return transaction_id

    def commit(self) -> bool:
        """Commit the current transaction"""
        if not self._active_transaction:
            raise RuntimeError("No active transaction to commit")
        
        try:
            # Apply all operations permanently
            for op in self._transaction_operations:
                collection = self.get_collection(op['collection'])
                if collection:
                    collection.apply_operation(op)
                else:
                    raise ValueError(f"Collection {op['collection']} not found during commit")
            
            # Clean up transaction log
            log_file = self._transaction_log_path / f"{self._active_transaction}.log"
            if log_file.exists():
                try:
                    log_file.unlink()
                except OSError as e:
                    logger.log_operation("ERROR", "TX_LOG_CLEANUP", self.name, f"Failed to delete transaction log: {e}")
                    raise
            
            logger.log_operation("TRANSACTION", "COMMIT", self.name, 
                               f"Transaction {self._active_transaction} committed")
            return True
        except Exception as e:
            logger.log_operation("TRANSACTION", "COMMIT_FAILED", self.name, str(e))
            raise
        finally:
            self._active_transaction = None
            self._transaction_operations = []

    def rollback(self) -> bool:
        """Roll back the current transaction"""
        if not self._active_transaction:
            raise RuntimeError("No active transaction to rollback")
        
        try:
            # Undo all operations in reverse order
            for op in reversed(self._transaction_operations):
                collection = self.get_collection(op['collection'])
                if collection:
                    collection.undo_operation(op)
                else:
                    logger.log_operation("WARNING", "TX_ROLLBACK", self.name, 
                                       f"Collection {op['collection']} not found during rollback")
            
            # Clean up transaction log
            log_file = self._transaction_log_path / f"{self._active_transaction}.log"
            if log_file.exists():
                try:
                    log_file.unlink()
                except OSError as e:
                    logger.log_operation("ERROR", "TX_LOG_CLEANUP", self.name, f"Failed to delete transaction log: {e}")
                    raise
            
            logger.log_operation("TRANSACTION", "ROLLBACK", self.name, 
                               f"Transaction {self._active_transaction} rolled back")
            return True
        except Exception as e:
            logger.log_operation("TRANSACTION", "ROLLBACK_FAILED", self.name, str(e))
            raise
        finally:
            self._active_transaction = None
            self._transaction_operations = []

    def _log_operation(self, operation: Dict):
        """Record an operation in the transaction log"""
        if not self._active_transaction:
            return  # No transaction, apply directly
        
        # Validate operation
        if 'type' not in operation or 'collection' not in operation:
            raise ValueError("Operation must include 'type' and 'collection'")
        
        valid_op_types = ['create_collection', 'drop_collection', 'insert', 'update', 'delete']
        if operation['type'] not in valid_op_types:
            raise ValueError(f"Invalid operation type: {operation['type']}")
        
        self._transaction_operations.append(operation)
        
        # Append to physical log file
        log_file = self._transaction_log_path / f"{self._active_transaction}.log"
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(operation) + '\n')
        except OSError as e:
            logger.log_operation("ERROR", "TX_LOG_WRITE", self.name, f"Failed to write to transaction log: {e}")
            raise

    def create_collection(self, name: str, indexes: Optional[List[str]] = None) -> Collection:
        """Create a new collection in the database with optional indexes"""
        if self._active_transaction:
            operation = {
                'type': 'create_collection',
                'collection': name,
                'indexes': indexes,
                'timestamp': datetime.now().isoformat()
            }
            self._log_operation(operation)
        
        if name in self.collections:
            raise ValueError(f"Collection '{name}' already exists")
        
        collection_path = self.db_path / f"{name}.json"
        if collection_path.exists():
            raise FileExistsError(f"Collection file '{name}.json' already exists")
        
        # Create empty collection file
        try:
            with open(collection_path, 'w') as f:
                json.dump([], f)
        except OSError as e:
            logger.log_operation("ERROR", "COLLECTION_CREATION", self.name, f"Failed to create collection file: {e}")
            raise
        
        collection = Collection(name, collection_path, indexes)
        self.collections[name] = collection
        return collection

    def drop_collection(self, name: str) -> bool:
        """Remove a collection from the database"""
        if self._active_transaction:
            # Save current state for possible rollback
            collection = self.get_collection(name)
            if collection:
                documents = collection.find({})
                operation = {
                    'type': 'drop_collection',
                    'collection': name,
                    'documents': documents,
                    'timestamp': datetime.now().isoformat()
                }
                self._log_operation(operation)
        
        if name not in self.collections:
            collection_path = self.db_path / f"{name}.json"
            if not collection_path.exists():
                return False
        
        collection_path = self.db_path / f"{name}.json"
        if collection_path.exists():
            try:
                collection_path.unlink()
                self.collections.pop(name, None)
                return True
            except OSError as e:
                logger.log_operation("ERROR", "COLLECTION_DROP", self.name, f"Failed to delete collection file: {e}")
                raise
        return False

        # database.py (partial update)
    def get_collection(self, name: str) -> Optional[Collection]:
        """Get a collection by name with transaction awareness"""
        if name in self.collections:
            collection = self.collections[name]
            if self._active_transaction:
                collection.set_transaction_context(self._active_transaction, self._log_operation)
            return collection
        
        collection_path = self.db_path / f"{name}.json"
        if collection_path.exists():
            collection = Collection(name, collection_path)
            if self._active_transaction:
                collection.set_transaction_context(self._active_transaction, self._log_operation)
            self.collections[name] = collection
            return collection
        
        return None

    def list_collections(self) -> List[str]:
        """List all collections in the database"""
        try:
            collections = [file.stem for file in self.db_path.glob("*.json")]
            return collections
        except OSError as e:
            logger.log_operation("ERROR", "LIST_COLLECTIONS", self.name, f"Failed to list collections: {e}")
            raise

    def drop_database(self):
        """Remove the entire database"""
        if self._active_transaction:
            raise RuntimeError("Cannot drop database during active transaction")
        
        import shutil
        try:
            shutil.rmtree(self.db_path)
            self.collections.clear()
        except OSError as e:
            logger.log_operation("ERROR", "DROP_DATABASE", self.name, f"Failed to drop database: {e}")
            raise

    def aggregate(self, collection_name: str, pipeline: List[Dict]) -> List[Dict]:
        """Perform aggregation on a collection"""
        collection = self.get_collection(collection_name)
        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found")
        return collection.aggregate(pipeline)

    def is_in_transaction(self) -> bool:
        """Check if a transaction is currently active"""
        return self._active_transaction is not None

    def cleanup_stale_logs(self):
        """Clean up any stale transaction logs (e.g., from crashes)"""
        try:
            for log_file in self._transaction_log_path.glob("*.log"):
                try:
                    log_file.unlink()
                    logger.log_operation("INFO", "CLEANUP_STALE_LOG", self.name, 
                                       f"Removed stale transaction log: {log_file.name}")
                except OSError as e:
                    logger.log_operation("ERROR", "CLEANUP_STALE_LOG", self.name, 
                                       f"Failed to remove stale log {log_file.name}: {e}")
        except OSError as e:
            logger.log_operation("ERROR", "CLEANUP_STALE_LOG", self.name, 
                               f"Failed to access transaction log directory: {e}")
    
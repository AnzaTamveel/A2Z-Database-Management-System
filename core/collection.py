#collection.py
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import time
from uuid import uuid4
from core.query import Query
from utils.helpers import deep_update, match_document
from utils.logger import logger

class Collection:
    def __init__(self, name: str, file_path: Path, indexes: List[str] = None):
        self.name = name
        self.file_path = file_path
        self.indexes = indexes if indexes else []
        self.indexing_enabled = False
        self.documents = []
        self.doc_id_map = {}  # Map _id to document for fast lookup
        self.indexes_dict = {index: {} for index in self.indexes}
        self._transaction_id: Optional[str] = None
        self._transaction_buffer: List[Dict] = []
        self._log_operation = None
        self._load_data()
        self._build_indexes()
        logger.log_operation(
            "COLLECTION_INIT",
            f"collection:{name}",
            "COMPLETED",
            f"path:{file_path}, indexes:{self.indexes}, documents:{len(self.documents)}"
        )

    def set_transaction_context(self, transaction_id: str, log_operation=None):
        """Set the transaction context for this collection"""
        self._transaction_id = transaction_id
        self._transaction_buffer = []
        self._log_operation = log_operation
        logger.log_operation(
            "TRANSACTION_CONTEXT",
            f"collection:{self.name}",
            "SET",
            f"transaction_id:{transaction_id}"
        )

    def apply_operation(self, operation: Dict):
        """Apply a transaction operation during commit"""
        op_type = operation.get('type')
        try:
            if op_type == 'dakhil karo':
                self.documents.append(operation['document'])
                self.doc_id_map[operation['document']['_id']] = operation['document']
                self._update_indexes(operation['document'])
            elif op_type == 'update':
                for i, doc in enumerate(self.documents):
                    if doc['_id'] == operation['doc_id']:
                        if operation.get('set'):
                            deep_update(doc, operation['set'])
                        elif operation.get('unset'):
                            for field in operation['unset']:
                                if field in doc:
                                    del doc[field]
                        self.doc_id_map[doc['_id']] = doc
                        self._update_indexes(doc)
                        break
            elif op_type == 'delete':
                self.documents = [doc for doc in self.documents if doc['_id'] != operation['doc_id']]
                self.doc_id_map.pop(operation['doc_id'], None)
                self._update_indexes(operation['document'], is_delete=True)
            else:
                raise ValueError(f"Unsupported operation type: {op_type}")
            self._save_data()
            logger.log_operation(
                "TRANSACTION_APPLY",
                f"collection:{self.name}",
                "SUCCESS",
                f"type:{op_type}, transaction_id:{self._transaction_id}"
            )
        except Exception as e:
            logger.log_operation(
                "TRANSACTION_APPLY",
                f"collection:{self.name}",
                "FAILED",
                f"type:{op_type}, error:{str(e)}"
            )
            raise

    def undo_operation(self, operation: Dict):
        """Properly undo a transaction operation during rollback"""
        op_type = operation.get('type')
        try:
            if op_type == 'dakhil karo':
                self.documents = [doc for doc in self.documents 
                                if doc['_id'] != operation['document']['_id']]
                self.doc_id_map.pop(operation['document']['_id'], None)
                self._update_indexes(operation['document'], is_delete=True)
            elif op_type == 'update':
                for i, doc in enumerate(self.documents):
                    if doc['_id'] == operation['doc_id']:
                        self.documents[i] = operation['original_doc'].copy()
                        self.doc_id_map[doc['_id']] = self.documents[i]
                        self._update_indexes(self.documents[i])
                        break
            elif op_type == 'delete':
                self.documents.append(operation['document'])
                self.doc_id_map[operation['document']['_id']] = operation['document']
                self._update_indexes(operation['document'])
            else:
                raise ValueError(f"Unsupported operation type: {op_type}")
            self._save_data()
            logger.log_operation(
                "TRANSACTION_UNDO",
                f"collection:{self.name}",
                "SUCCESS",
                f"type:{op_type}, transaction_id:{self._transaction_id}"
            )
        except Exception as e:
            logger.log_operation(
                "TRANSACTION_UNDO",
                f"collection:{self.name}",
                "FAILED",
                f"type:{op_type}, error:{str(e)}"
            )
            raise

    def _load_data(self):
        """Load data from the collection file"""
        try:
            with open(self.file_path, 'r') as f:
                self.documents = json.load(f)
            self.doc_id_map = {doc['_id']: doc for doc in self.documents}
            logger.log_operation(
                "DATA_LOAD",
                f"collection:{self.name}",
                "SUCCESS",
                f"loaded {len(self.documents)} documents"
            )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.documents = []
            self.doc_id_map = {}
            logger.log_operation(
                "DATA_LOAD",
                f"collection:{self.name}",
                "INITIALIZED",
                f"new collection created - {str(e)}"
            )

    def _save_data(self):
        """Save data to the collection file (only outside transactions)"""
        if self._transaction_id:
            return
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.documents, f, indent=2)
            logger.log_operation(
                "DATA_SAVE",
                f"collection:{self.name}",
                "SUCCESS",
                f"saved {len(self.documents)} documents"
            )
        except Exception as e:
            logger.log_operation(
                "DATA_SAVE",
                f"collection:{self.name}",
                "FAILED",
                str(e)
            )
            raise

    def insert_one(self, document: Dict) -> str:
        """Insert a single document into the collection"""
        try:
            if not isinstance(document, dict):
                raise ValueError("Document must be a dictionary")
            
            if "_id" not in document:
                document["_id"] = str(uuid4())
            
            if self._transaction_id:
                operation = {
                    'type': 'insert',
                    'collection': self.name,
                    'document': document.copy(),
                    'timestamp': time.time()
                }
                self._transaction_buffer.append(operation)
                if self._log_operation:
                    self._log_operation(operation)
                return document["_id"]
            
            self.documents.append(document)
            self.doc_id_map[document['_id']] = document
            self._update_indexes(document)
            self._save_data()
            logger.log_operation(
                "DOCUMENT_INSERT",
                f"collection:{self.name}",
                "SUCCESS",
                f"id:{document['_id']}"
            )
            return document["_id"]
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_INSERT",
                f"collection:{self.name}",
                "FAILED",
                str(e)
            )
            raise

    def insert_many(self, documents: List[Dict]) -> List[str]:
        """Insert multiple documents into the collection"""
        if not isinstance(documents, list):
            raise ValueError("Documents must be a list")
        
        ids = []
        try:
            for doc in documents:
                if not isinstance(doc, dict):
                    raise ValueError("Each document must be a dictionary")
                if "_id" not in doc:
                    doc["_id"] = str(uuid4())
                ids.append(doc["_id"])
            
            if self._transaction_id:
                for doc in documents:
                    operation = {
                        'type': 'insert',
                        'collection': self.name,
                        'document': doc.copy(),
                        'timestamp': time.time()
                    }
                    self._transaction_buffer.append(operation)
                    if self._log_operation:
                        self._log_operation(operation)
                return ids
            
            self.documents.extend(documents)
            for doc in documents:
                self.doc_id_map[doc['_id']] = doc
                self._update_indexes(doc)
            self._save_data()
            logger.log_operation(
                "DOCUMENT_INSERT_MANY",
                f"collection:{self.name}",
                "SUCCESS",
                f"inserted {len(ids)} documents"
            )
            return ids
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_INSERT_MANY",
                f"collection:{self.name}",
                "FAILED",
                str(e)
            )
            raise

    def update_one(self, query: Dict, update: Dict) -> bool:
        """Update a single document matching the query"""
        try:
            for i, doc in enumerate(self.documents):
                if match_document(doc, query):
                    if self._transaction_id:
                        original_doc = doc.copy()
                        operation = {
                            'type': 'update',
                            'collection': self.name,
                            'doc_id': doc['_id'],
                            'original_doc': original_doc,
                            'timestamp': time.time()
                        }
                        if "$set" in update:
                            operation['set'] = update["$set"]
                            deep_update(doc, update["$set"])
                        elif "$unset" in update:
                            operation['unset'] = update["$unset"]
                            for field in update["$unset"]:
                                if field in doc:
                                    del doc[field]
                        elif "$push" in update:
                            operation['push'] = update["$push"]
                            for field, value in update["$push"].items():
                                if field not in doc:
                                    doc[field] = []
                                if not isinstance(doc[field], list):
                                    raise ValueError(f"Cannot push to non-array field: {field}")
                                doc[field].append(value)
                        else:
                            operation['set'] = update
                            deep_update(doc, update)
                        self._transaction_buffer.append(operation)
                        if self._log_operation:
                            self._log_operation(operation)
                        return True
                    
                    if "$set" in update:
                        deep_update(doc, update["$set"])
                    elif "$unset" in update:
                        for field in update["$unset"]:
                            if field in doc:
                                del doc[field]
                    elif "$push" in update:
                        for field, value in update["$push"].items():
                            if field not in doc:
                                doc[field] = []
                            if not isinstance(doc[field], list):
                                raise ValueError(f"Cannot push to non-array field: {field}")
                            doc[field].append(value)
                    else:
                        deep_update(doc, update)
                    self.doc_id_map[doc['_id']] = doc
                    self._update_indexes(doc)
                    self._save_data()
                    logger.log_operation(
                        "DOCUMENT_UPDATE",
                        f"collection:{self.name}",
                        "SUCCESS",
                        f"id:{doc['_id']}, query:{query}, update:{update}"
                    )
                    return True
            
            logger.log_operation(
                "DOCUMENT_UPDATE",
                f"collection:{self.name}",
                "NOT_FOUND",
                f"query:{query}"
            )
            return False
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_UPDATE",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise

    def update_many(self, query: Dict, update: Dict) -> int:
        """Update all documents matching the query"""
        count = 0
        try:
            for doc in self.documents:
                if match_document(doc, query):
                    if self._transaction_id:
                        original_doc = doc.copy()
                        operation = {
                            'type': 'update',
                            'collection': self.name,
                            'doc_id': doc['_id'],
                            'original_doc': original_doc,
                            'timestamp': time.time()
                        }
                        if "$set" in update:
                            operation['set'] = update["$set"]
                            deep_update(doc, update["$set"])
                        elif "$unset" in update:
                            operation['unset'] = update["$unset"]
                            for field in update["$unset"]:
                                if field in doc:
                                    del doc[field]
                        elif "$push" in update:
                            operation['push'] = update["$push"]
                            for field, value in update["$push"].items():
                                if field not in doc:
                                    doc[field] = []
                                if not isinstance(doc[field], list):
                                    raise ValueError(f"Cannot push to non-array field: {field}")
                                doc[field].append(value)
                        else:
                            operation['set'] = update
                            deep_update(doc, update)
                        self._transaction_buffer.append(operation)
                        if self._log_operation:
                            self._log_operation(operation)
                    else:
                        if "$set" in update:
                            deep_update(doc, update["$set"])
                        elif "$unset" in update:
                            for field in update["$unset"]:
                                if field in doc:
                                    del doc[field]
                        elif "$push" in update:
                            for field, value in update["$push"].items():
                                if field not in doc:
                                    doc[field] = []
                                if not isinstance(doc[field], list):
                                    raise ValueError(f"Cannot push to non-array field: {field}")
                                doc[field].append(value)
                        else:
                            deep_update(doc, update)
                        self.doc_id_map[doc['_id']] = doc
                        self._update_indexes(doc)
                    count += 1
            
            if count > 0 and not self._transaction_id:
                self._save_data()
            logger.log_operation(
                "DOCUMENT_UPDATE_MANY",
                f"collection:{self.name}",
                "SUCCESS",
                f"updated {count} documents, query:{query}"
            )
            return count
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_UPDATE_MANY",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise
        
    def delete_one(self, query: Dict) -> bool:
        """Delete a single document matching the query"""
        try:
            for i, doc in enumerate(self.documents):
                if match_document(doc, query):
                    if self._transaction_id:
                        operation = {
                            'type': 'delete',
                            'collection': self.name,
                            'doc_id': doc['_id'],
                            'document': doc.copy(),
                            'timestamp': time.time()
                        }
                        self._transaction_buffer.append(operation)
                        if self._log_operation:
                            self._log_operation(operation)
                        self.documents.pop(i)
                        self.doc_id_map.pop(doc['_id'], None)
                        return True
                    
                    del self.documents[i]
                    self.doc_id_map.pop(doc['_id'], None)
                    self._update_indexes(doc, is_delete=True)
                    self._save_data()
                    logger.log_operation(
                        "DOCUMENT_DELETE",
                        f"collection:{self.name}",
                        "SUCCESS",
                        f"id:{doc['_id']}"
                    )
                    return True
            
            logger.log_operation(
                "DOCUMENT_DELETE",
                f"collection:{self.name}",
                "NOT_FOUND",
                f"query:{query}"
            )
            return False
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_DELETE",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise

    def delete_many(self, query: Dict) -> int:
        """Delete all documents matching the query"""
        try:
            deleted_count = 0
            new_documents = []
            for doc in self.documents:
                if match_document(doc, query):
                    if self._transaction_id:
                        operation = {
                            'type': 'delete',
                            'collection': self.name,
                            'doc_id': doc['_id'],
                            'document': doc.copy(),
                            'timestamp': time.time()
                        }
                        self._transaction_buffer.append(operation)
                        if self._log_operation:
                            self._log_operation(operation)
                        deleted_count += 1
                    else:
                        self._update_indexes(doc, is_delete=True)
                        deleted_count += 1
                else:
                    new_documents.append(doc)
            
            self.documents = new_documents
            self.doc_id_map = {doc['_id']: doc for doc in new_documents}
            if deleted_count > 0 and not self._transaction_id:
                self._save_data()
            logger.log_operation(
                "DOCUMENT_DELETE_MANY",
                f"collection:{self.name}",
                "SUCCESS",
                f"deleted {deleted_count} documents, query:{query}"
            )
            return deleted_count
        except Exception as e:
            logger.log_operation(
                "DOCUMENT_DELETE_MANY",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise

    def find(self, query: Optional[Dict] = None) -> List[Dict]:
        """Find documents matching query with proper index usage"""
        start_time = time.perf_counter()
        
        if not query:
            results = self.documents.copy()
            print(f"Query: {query}, Indexing Enabled: {self.indexing_enabled}, Indexes: {self.indexes}")
            self._log_query_performance("FULL_SCAN", start_time, len(results), reason="No query provided")
            return results
        
        if self.indexing_enabled:
            for field, value in query.items():
                if field in self.indexes:
                    if not isinstance(value, dict):
                        if value in self.indexes_dict[field]:
                            doc_ids = self.indexes_dict[field][value]
                            results = [self.doc_id_map[doc_id] for doc_id in doc_ids 
                                     if doc_id in self.doc_id_map and self._matches_query(self.doc_id_map[doc_id], query)]
                            self._log_query_performance("INDEX_USED", start_time, len(results), field=field, reason="Direct equality match")
                            print(f"Query (direct equality): {query}, Indexing Enabled: {self.indexing_enabled}, Indexes: {self.indexes}")
                            return results
                    elif "$eq" in value and value["$eq"] in self.indexes_dict[field]:
                        doc_ids = self.indexes_dict[field][value["$eq"]]
                        results = [self.doc_id_map[doc_id] for doc_id in doc_ids 
                                 if doc_id in self.doc_id_map and self._matches_query(self.doc_id_map[doc_id], query)]
                        self._log_query_performance("INDEX_USED", start_time, len(results), field=field, reason="Operator-based equality match")
                        print(f"Query ($eq): {query}, Indexing Enabled: {self.indexing_enabled}, Indexes: {self.indexes}")
                        return results
                    elif "$in" in value:
                        doc_ids = []
                        for val in value["$in"]:
                            if val in self.indexes_dict[field]:
                                doc_ids.extend(self.indexes_dict[field][val])
                        doc_ids = list(set(doc_ids))  # Remove duplicates
                        results = [self.doc_id_map[doc_id] for doc_id in doc_ids 
                                 if doc_id in self.doc_id_map and self._matches_query(self.doc_id_map[doc_id], query)]
                        self._log_query_performance("INDEX_USED", start_time, len(results), field=field, reason="In operator match")
                        print(f"Query ($in): {query}, Indexing Enabled: {self.indexing_enabled}, Indexes: {self.indexes}")
                        return results
        
        results = [doc for doc in self.documents if self._matches_query(doc, query)]
        self._log_query_performance("FULL_SCAN", start_time, len(results), reason="No suitable index found")
        return results

    def _log_query_performance(self, scan_type, start_time, result_count, field=None, reason=None):
        """Log query performance with additional context"""
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        log_msg = f"{scan_type} query returned {result_count} docs in {elapsed_ms:.2f}ms"
        if field:
            log_msg += f" (used index on {field})"
        if reason:
            log_msg += f" (reason: {reason})"
        logger.log_operation(
            "QUERY_EXECUTE",
            f"collection:{self.name}",
            scan_type,
            log_msg
        )

    def _matches_query(self, doc: Dict, query: Dict) -> bool:
        """Check if a document matches the query criteria"""
        for field, condition in query.items():
            if field not in doc:
                return False
            if isinstance(condition, dict):
                for op, value in condition.items():
                    if op == "$gt":
                        if not doc[field] > value:
                            return False
                    elif op == "$lt":
                        if not doc[field] < value:
                            return False
                    elif op == "$eq":
                        if not doc[field] == value:
                            return False
                    elif op == "$ne":
                        if not doc[field] != value:
                            return False
                    elif op == "$in":
                        if doc[field] not in value:
                            return False
                    else:
                        return False
            else:
                if doc[field] != condition:
                    return False
        return True

    def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        """Perform aggregation operations"""
        results = self.documents.copy()
        for stage in pipeline:
            if "$match" in stage:
                results = [doc for doc in results if Query.evaluate(doc, stage["$match"])]
            elif "$group" in stage:
                results = self._group_documents(results, stage["$group"])
            elif "$sort" in stage:
                results = sorted(results, key=lambda x: self._get_sort_key(x, stage["$sort"]))
            elif "$limit" in stage:
                results = results[:stage["$limit"]]
            elif "$skip" in stage:
                results = results[stage["$skip"]:]
            elif "$project" in stage:
                results = self._project_documents(results, stage["$project"])
        return results

    def _get_sort_key(self, doc: Dict, sort_spec: Dict) -> tuple:
        """Generate sort key for a document"""
        keys = []
        for field, order in sort_spec.items():
            value = self._get_field_value(doc, field)
            keys.append((value, order))
        return tuple(keys)

    def _get_field_value(self, doc: Dict, field_path: str) -> Any:
        """Get a nested field value from a document using dot notation"""
        if field_path.startswith("$"):
            field_path = field_path[1:]
        parts = field_path.split('.')
        value = doc
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value

    def _group_documents(self, docs: List[Dict], group: Dict) -> List[Dict]:
        """Handle $group aggregation"""
        groups = {}
        id_fields = group["_id"]
        for doc in docs:
            if isinstance(id_fields, dict):
                group_key = tuple(self._get_field_value(doc, field) for field in id_fields.values())
            elif id_fields is None or id_fields == "$none":
                group_key = None
            else:
                field_path = id_fields[1:] if isinstance(id_fields, str) and id_fields.startswith("$") else id_fields
                group_key = self._get_field_value(doc, field_path)
            
            if group_key not in groups:
                groups[group_key] = {"_id": group_key}
                for field, op in group.items():
                    if field != "_id":
                        if isinstance(op, dict) and "operator" in op:
                            if op["operator"] in ["$sum", "$avg", "$min", "$max"]:
                                groups[group_key][field] = []
                            elif op["operator"] == "$count":
                                groups[group_key][field] = 0
            
            for field, op in group.items():
                if field != "_id":
                    if isinstance(op, dict) and "operator" in op:
                        field_path = op.get("field", field)
                        if field_path.startswith("$"):
                            field_path = field_path[1:]
                        value = self._get_field_value(doc, field_path)
                        if op["operator"] == "$sum":
                            if isinstance(value, (int, float)) and value is not None:
                                groups[group_key][field].append(value)
                        elif op["operator"] == "$avg":
                            if isinstance(value, (int, float)) and value is not None:
                                groups[group_key][field].append(value)
                        elif op["operator"] == "$min" or op["operator"] == "$max":
                            if value is not None:
                                groups[group_key][field].append(value)
                        elif op["operator"] == "$count":
                            groups[group_key][field] += 1
                        elif op["operator"] == "$first":
                            if field not in groups[group_key] or groups[group_key][field] is None:
                                groups[group_key][field] = value
                        elif op["operator"] == "$last":
                            groups[group_key][field] = value
        
        result = []
        for group_data in groups.values():
            new_doc = {"_id": group_data["_id"]}
            for field, values in group_data.items():
                if field != "_id":
                    if isinstance(values, list):
                        op = group[field]["operator"]
                        new_doc[field] = self._apply_aggregation(values, op)
                    else:
                        new_doc[field] = values
            result.append(new_doc)
        return result

    def _apply_aggregation(self, values: List, operator: str) -> Any:
        """Apply aggregation operator to values"""
        if not values and operator != "$count":
            return 0 if operator in ["$sum", "$avg", "$count"] else None
        if operator == "$sum":
            return sum(v for v in values if isinstance(v, (int, float)))
        elif operator == "$avg":
            nums = [v for v in values if isinstance(v, (int, float))]
            return sum(nums) / len(nums) if nums else 0
        elif operator == "$min":
            return min(values) if values else None
        elif operator == "$max":
            return max(values) if values else None
        elif operator == "$count":
            return len(values)
        elif operator == "$first":
            return values[0] if values else None
        elif operator == "$last":
            return values[-1] if values else None
        else:
            raise ValueError(f"Unsupported aggregation operator: {operator}")
        
    def _apply_aggregation(self, values: List, operator: str) -> Any:
        """Apply aggregation operator to values"""
        if not values:
            return None
        if operator == "$sum":
            return sum(v for v in values if isinstance(v, (int, float)))
        elif operator == "$avg":
            nums = [v for v in values if isinstance(v, (int, float))]
            return sum(nums)/len(nums) if nums else 0
        elif operator == "$min":
            return min(values) if values else None
        elif operator == "$max":
            return max(values) if values else None
        elif operator == "$count":
            return len(values)
        elif operator == "$first":
            return values[0] if values else None
        elif operator == "$last":
            return values[-1] if values else None
        else:
            raise ValueError(f"Unsupported aggregation operator: {operator}")

    def _build_indexes(self):
        """Build indexes for specified fields"""
        self.indexes_dict = {index: {} for index in self.indexes}
        for doc in self.documents:
            for index in self.indexes:
                if index in doc:
                    value = doc[index]
                    if value not in self.indexes_dict[index]:
                        self.indexes_dict[index][value] = []
                    self.indexes_dict[index][value].append(doc["_id"])

    def _update_indexes(self, document: Dict, is_delete=False):
        """Update indexes, now works during transactions for rollback"""
        for index in self.indexes:
            if index in document:
                value = document[index]
                if is_delete:
                    if value in self.indexes_dict[index]:
                        if document["_id"] in self.indexes_dict[index][value]:
                            self.indexes_dict[index][value].remove(document["_id"])
                            if not self.indexes_dict[index][value]:
                                del self.indexes_dict[index][value]
                else:
                    if value not in self.indexes_dict[index]:
                        self.indexes_dict[index][value] = []
                    if document["_id"] not in self.indexes_dict[index][value]:
                        self.indexes_dict[index][value].append(document["_id"])

    def create_index(self, field: str):
        """Create an index on the specified field"""
        try:
            if field not in self.indexes:
                self.indexes.append(field)
                self._build_indexes()
                self._save_data()
                logger.log_operation(
                    "INDEX_CREATE",
                    f"collection:{self.name}",
                    "SUCCESS",
                    f"field:{field}"
                )
            else:
                raise ValueError(f"Index already exists on field: {field}")
        except Exception as e:
            logger.log_operation(
                "INDEX_CREATE",
                f"collection:{self.name}",
                "FAILED",
                str(e)
            )
            raise

    def enable_indexing(self, enabled: bool):
        """Enable or disable using indexes for queries"""
        self.indexing_enabled = enabled
        logger.log_operation(
            "INDEX_TOGGLE",
            f"collection:{self.name}",
            "SUCCESS",
            f"indexing_enabled:{enabled}"
        )

    def list_indexes(self) -> List[Dict]:
        """Return information about all indexes"""
        return [{"name": f"{field}_index", "key": field} for field in self.indexes]

    def find_one(self, query: Dict) -> Optional[Dict]:
        """Find a single document matching the query using indexes if available"""
        try:
            if query and self.indexing_enabled:
                for field, value in query.items():
                    if field in self.indexes:
                        if not isinstance(value, dict):
                            if value in self.indexes_dict[field]:
                                doc_id = self.indexes_dict[field][value][0]
                                doc = self.doc_id_map.get(doc_id)
                                if doc and match_document(doc, query):
                                    return doc
                        elif "$eq" in value and value["$eq"] in self.indexes_dict[field]:
                            doc_id = self.indexes_dict[field][value["$eq"]][0]
                            doc = self.doc_id_map.get(doc_id)
                            if doc and match_document(doc, query):
                                return doc
            return next((doc for doc in self.documents if match_document(doc, query)), None)
        except Exception as e:
            logger.log_operation(
                "FIND_ONE",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise

    def count_documents(self, query: Optional[Dict] = None) -> int:
        """Count documents matching the query"""
        try:
            count = len(self.find(query)) if query else len(self.documents)
            logger.log_operation(
                "COUNT_DOCUMENTS",
                f"collection:{self.name}",
                "SUCCESS",
                f"query:{query}, count:{count}"
            )
            return count
        except Exception as e:
            logger.log_operation(
                "COUNT_DOCUMENTS",
                f"collection:{self.name}",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise

    def _project_documents(self, docs: List[Dict], project: Dict) -> List[Dict]:
        """Handle $project stage in aggregation"""
        results = []
        for doc in docs:
            new_doc = {}
            for field, value in project.items():
                if value == 1:
                    new_doc[field] = self._get_field_value(doc, field)
                elif value == 0:
                    continue
                elif isinstance(value, dict):
                    if "$literal" in value:
                        new_doc[field] = value["$literal"]
            results.append(new_doc)
        return results
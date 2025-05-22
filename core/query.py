#query.py
from typing import Optional, Dict, List
import json
import time
from utils.logger import logger

class Query:
    """Custom query language parser for database operations"""
        
    @staticmethod
    def parse(query: str) -> Dict:
        """Parse the custom query language"""
        query = query.strip()
        operation = query.lower()
        
        try:
            # Transaction operations
            if operation == "begin tx":
                logger.log_operation(
                    "QUERY_PARSE",
                    "TRANSACTION",
                    "SUCCESS",
                    "operation:begin_transaction"
                )
                return {"operation": "begin_transaction"}
            elif operation == "commit":
                logger.log_operation(
                    "QUERY_PARSE",
                    "TRANSACTION",
                    "SUCCESS",
                    "operation:commit"
                )
                return {"operation": "commit"}
            elif operation == "rollback":
                logger.log_operation(
                    "QUERY_PARSE",
                    "TRANSACTION",
                    "SUCCESS",
                    "operation:rollback"
                )
                return {"operation": "rollback"}
            
            # CRUD operations
            if operation.startswith("nava database banao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "DATABASE",
                    "SUCCESS",
                    f"operation:create_db, name:{query[19:].strip()}"
                )
                return {"operation": "create_db", "name": query[19:].strip()}
            elif operation.startswith("database nu mitao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "DATABASE",
                    "SUCCESS",
                    f"operation:drop_db, name:{query[17:].strip()}"
                )
                return {"operation": "drop_db", "name": query[17:].strip()}
            elif operation.startswith("database chalao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "DATABASE",
                    "SUCCESS",
                    f"operation:use_db, name:{query[15:].strip()}"
                )
                return {"operation": "use_db", "name": query[15:].strip()}
            elif operation.startswith("nava collection banao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "COLLECTION",
                    "SUCCESS",
                    f"operation:create_collection, name:{query[21:].strip()}"
                )
                return {"operation": "create_collection", "name": query[21:].strip()}
            elif operation.startswith("collection nu mitao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "COLLECTION",
                    "SUCCESS",
                    f"operation:drop_collection, name:{query[19:].strip()}"
                )
                return {"operation": "drop_collection", "name": query[19:].strip()}
            elif operation.startswith("index banao"):
                parts = query[11:].strip().split()
                if len(parts) >= 2:
                    logger.log_operation(
                        "QUERY_PARSE",
                        "INDEX",
                        "SUCCESS",
                        f"operation:create_index, field:{parts[0]}, collection:{parts[1]}"
                    )
                    return {"operation": "create_index", "field": parts[0], "collection": parts[1]}
                raise ValueError("Invalid create index syntax. Use: create index field collection")
            
            # Document operations
            elif operation.startswith("dakhil karo"):
                try:
                    # Split on first space after collection name
                    parts = query[11:].strip().split(None, 1)
                    if len(parts) < 2:
                        raise ValueError("Missing document data. Use: insert into collection {document} or insert into collection [documents]")
                    collection, data_part = parts
                    data_part = data_part.strip()
                    
                    if not data_part:
                        raise ValueError("Document data cannot be empty")
                    
                    # Parse JSON data
                    try:
                        if data_part.startswith("{"):
                            document = json.loads(data_part)
                            if not isinstance(document, dict):
                                raise ValueError("Single document must be a dictionary")
                            logger.log_operation(
                                "QUERY_PARSE",
                                "DOCUMENT",
                                "SUCCESS",
                                f"operation:insert, collection:{collection}"
                            )
                            return {
                                "operation": "insert",
                                "collection": collection,
                                "document": document
                            }
                        elif data_part.startswith("["):
                            documents = json.loads(data_part)
                            if not isinstance(documents, list):
                                raise ValueError("Multi-document data must be a JSON array")
                            if not all(isinstance(doc, dict) for doc in documents):
                                raise ValueError("All elements in array must be documents (dictionaries)")
                            logger.log_operation(
                                "QUERY_PARSE",
                                "DOCUMENT",
                                "SUCCESS",
                                f"operation:insert_many, collection:{collection}, count:{len(documents)}"
                            )
                            return {
                                "operation": "insert_many",
                                "collection": collection,
                                "documents": documents
                            }
                        else:
                            raise ValueError("Data must be a document {} or array of documents []")
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON format in document data: {str(e)} at position {e.pos}, line {e.lineno}, column {e.colno}"
                        logger.log_operation(
                            "QUERY_PARSE",
                            "ERROR",
                            "FAILED",
                            f"query:{query}, error:{error_msg}"
                        )
                        raise ValueError(error_msg)
                        
                except ValueError as e:
                    raise ValueError(f"Invalid insert syntax. Use: insert into collection {{document}} or insert into collection [documents]. Error: {str(e)}")
            
            elif operation.startswith("badlo"):
                try:
                    # Split on first space to get collection
                    parts = query[5:].strip().split(None, 1)
                    if len(parts) < 2:
                        raise ValueError("Missing query and update data. Use: badlo <collection> {query} {update}")
                    collection, rest = parts
                    collection = collection.strip()
                    
                    # Find the first { for query and the second { for update
                    rest = rest.strip()
                    if not rest.startswith("{"):
                        raise ValueError("Query must start with '{'. Use: badlo <collection> {query} {update}")
                    
                    # Parse the query and update as JSON objects
                    # Find the end of the first JSON object (query)
                    brace_count = 0
                    query_end = -1
                    for i, char in enumerate(rest):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                query_end = i + 1
                                break
                    if query_end == -1:
                        raise ValueError("Invalid query JSON: missing closing '}'")
                    
                    query_part = rest[:query_end]
                    update_part = rest[query_end:].strip()
                    if not update_part:
                        raise ValueError("Missing update JSON object. Use: badlo <collection> {query} {update}")
                    if not update_part.startswith("{"):
                        raise ValueError("Update must start with '{'. Use: badlo <collection> {query} {update}")
                    
                    # Parse JSON
                    query_json = json.loads(query_part)
                    update_json = json.loads(update_part)
                    
                    if not isinstance(query_json, dict):
                        raise ValueError("Query must be a JSON object")
                    if not isinstance(update_json, dict):
                        raise ValueError("Update must be a JSON object")
                    
                    logger.log_operation(
                        "QUERY_PARSE",
                        "DOCUMENT",
                        "SUCCESS",
                        f"operation:update, collection:{collection}"
                    )
                    return {
                        "operation": "update",
                        "collection": collection,
                        "query": query_json,
                        "update": update_json
                    }
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON format: {str(e)} at position {e.pos}, line {e.lineno}, column {e.colno}"
                    logger.log_operation(
                        "QUERY_PARSE",
                        "ERROR",
                        "FAILED",
                        f"query:{query}, error:{error_msg}"
                    )
                    raise ValueError(f"Invalid JSON in query or update: {error_msg}")
                except ValueError as e:
                    logger.log_operation(
                        "QUERY_PARSE",
                        "ERROR",
                        "FAILED",
                        f"query:{query}, error:{str(e)}"
                    )
                    raise ValueError(f"Invalid update syntax. Use: badlo <collection> {{query}} {{update}}. Error: {str(e)}")
                                
            elif operation.startswith("mitao"):
                try:
                    collection, query_part = query[5:].strip().split("{", 1)
                    logger.log_operation(
                        "QUERY_PARSE",
                        "DOCUMENT",
                        "SUCCESS",
                        f"operation:delete, collection:{collection.strip()}"
                    )
                    return {
                        "operation": "delete",
                        "collection": collection.strip(),
                        "query": json.loads("{" + query_part)
                    }
                except (ValueError, json.JSONDecodeError):
                    raise ValueError("Invalid delete syntax. Use: delete from collection {query}")
            
            # Query operations
            elif operation.startswith("labbo"):
                try:
                    collection, query_part = query[5:].strip().split("{", 1)
                    logger.log_operation(
                        "QUERY_PARSE",
                        "QUERY",
                        "SUCCESS",
                        f"operation:find, collection:{collection.strip()}"
                    )
                    return {
                        "operation": "find",
                        "collection": collection.strip(),
                        "query": json.loads("{" + query_part)
                    }
                except (ValueError, json.JSONDecodeError):
                    logger.log_operation(
                        "QUERY_PARSE",
                        "QUERY",
                        "SUCCESS",
                        f"operation:find, collection:{query[7:].strip()}, query:{{}}"
                    )
                    return {
                        "operation": "find",
                        "collection": query[7:].strip(),
                        "query": {}
                    }
            
            # Aggregation
            elif operation.startswith("aggregate in"):
                try:
                    collection, pipeline = query[12:].strip().split("[", 1)
                    logger.log_operation(
                        "QUERY_PARSE",
                        "AGGREGATION",
                        "SUCCESS",
                        f"operation:aggregate, collection:{collection.strip()}"
                    )
                    return {
                        "operation": "aggregate",
                        "collection": collection.strip(),
                        "pipeline": json.loads("[" + pipeline)
                    }
                except (ValueError, json.JSONDecodeError):
                    raise ValueError("Invalid aggregate syntax. Use: aggregate in collection [pipeline]")
            
            # Backup operations
            elif operation.startswith("backup banao"):
                name = query[12:].strip()
                if not name:
                    ValueError("Database name required for backup. Use: backup banao <database_name>")
                logger.log_operation(
                    "QUERY_PARSE",
                    "BACKUP",
                    "SUCCESS",
                    f"operation:backup, name:{name}"
                )
                return {"operation": "backup", "name": name}
            elif operation.startswith("restore karo"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "RESTORE",
                    "SUCCESS",
                    f"operation:restore, name:{query[12:].strip()}"
                )
                return {"operation": "restore", "name": query[12:].strip()}
# Index operations
            elif operation.startswith("index dikhao"):
                logger.log_operation(
                    "QUERY_PARSE",
                    "INDEX",
                    "SUCCESS",
                    f"operation:list_indexes, collection:{query[12:].strip()}"
                )
                return {"operation": "list_indexes", "collection": query[12:].strip()}
            
            # Toggle indexing
            elif operation == "index chalo karo":
                logger.log_operation(
                    "QUERY_PARSE",
                    "INDEX",
                    "SUCCESS",
                    "operation:enable_indexing, enable:True"
                )
                return {"operation": "enable_indexing", "enable": True}
            elif operation == "index band karo":
                logger.log_operation(
                    "QUERY_PARSE",
                    "INDEX",
                    "SUCCESS",
                    "operation:enable_indexing, enable:False"
                )
                return {"operation": "enable_indexing", "enable": False}
            
            else:
                raise ValueError(f"Unknown query command: {query}")
                
        except ValueError as e:
            logger.log_operation(
                "QUERY_PARSE",
                "ERROR",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise
        
    @staticmethod
    def evaluate(doc: Dict, query: Dict) -> bool:
        """Evaluate if a document matches the query"""
        try:
            for field, condition in query.items():
                if field not in doc:
                    return False
                    
                if isinstance(condition, dict):
                    # Handle operators
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
                    # Direct equality match
                    if doc[field] != condition:
                        return False
                        
            return True
        except Exception as e:
            logger.log_operation(
                "QUERY_EVALUATE",
                "ERROR",
                "FAILED",
                f"query:{query}, error:{str(e)}"
            )
            raise
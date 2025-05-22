from typing import Dict, List, Set
from enum import Enum, auto

class Permission(Enum):
    # Database operations
    CREATE_DATABASE = auto()
    DROP_DATABASE = auto()
    USE_DATABASE = auto()
    
    # Collection operations
    CREATE_COLLECTION = auto()
    DROP_COLLECTION = auto()
    
    # Document operations
    INSERT_DOCUMENT = auto()
    UPDATE_DOCUMENT = auto()
    DELETE_DOCUMENT = auto()
    READ_DOCUMENT = auto()
    
    # Index operations
    CREATE_INDEX = auto()
    LIST_INDEXES = auto()
    
    # Transaction operations
    BEGIN_TRANSACTION = auto()
    COMMIT = auto()
    ROLLBACK = auto()
    
    # Backup operations
    CREATE_BACKUP = auto()
    RESTORE_BACKUP = auto()

class Role:
    def __init__(self, name: str, permissions: Set[Permission]):
        self.name = name
        self.permissions = permissions

class PermissionManager:
    def __init__(self):
        self.roles: Dict[str, Role] = self._initialize_default_roles()
    
    def _initialize_default_roles(self) -> Dict[str, Role]:
        return {
            "admin": Role("admin", {
                Permission.CREATE_DATABASE,
                Permission.DROP_DATABASE,
                Permission.USE_DATABASE,
                Permission.CREATE_COLLECTION,
                Permission.DROP_COLLECTION,
                Permission.INSERT_DOCUMENT,
                Permission.UPDATE_DOCUMENT,
                Permission.DELETE_DOCUMENT,
                Permission.READ_DOCUMENT,
                Permission.CREATE_INDEX,
                Permission.LIST_INDEXES,
                Permission.BEGIN_TRANSACTION,
                Permission.COMMIT,
                Permission.ROLLBACK,
                Permission.CREATE_BACKUP,
                Permission.RESTORE_BACKUP
            }),
            "read_write": Role("read_write", {
                Permission.USE_DATABASE,
                Permission.INSERT_DOCUMENT,
                Permission.UPDATE_DOCUMENT,
                Permission.DELETE_DOCUMENT,
                Permission.READ_DOCUMENT,
                Permission.LIST_INDEXES
            }),
            "read": Role("read", {
                Permission.USE_DATABASE,
                Permission.READ_DOCUMENT,
                Permission.LIST_INDEXES
            })
        }
    
    def check_permission(self, role_names: List[str], permission: Permission) -> bool:
        for role_name in role_names:
            if role_name in self.roles and permission in self.roles[role_name].permissions:
                return True
        return False
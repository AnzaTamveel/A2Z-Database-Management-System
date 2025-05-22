from functools import wraps
from core.auth import AuthManager
from core.permissions import Permission, PermissionManager
from utils.logger import logger

def requires_auth(permission: Permission):
    def decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'current_user'):
                logger.log_operation("AUTH", "ACCESS", "DENIED", "No user session")
                raise PermissionError("Authentication required")
            
            if not PermissionManager().check_permission(
                self.current_user.roles, permission
            ):
                logger.log_operation(
                    "AUTH", 
                    "ACCESS", 
                    "DENIED", 
                    f"user:{self.current_user.username}, required:{permission.name}"
                )
                raise PermissionError("Insufficient permissions")
            
            return f(self, *args, **kwargs)
        return wrapper
    return decorator
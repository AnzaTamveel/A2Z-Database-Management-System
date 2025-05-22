import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4
from utils.logger import logger

class User:
    def __init__(self, username: str, password_hash: str, roles: list):
        self.username = username
        self.password_hash = password_hash
        self.roles = roles
        self.id = str(uuid4())

class AuthManager:
    def __init__(self, auth_db_path: Path = Path("db/auth.db")):
        self.auth_db_path = auth_db_path
        self.users: Dict[str, User] = {}
        self._load_users()
        
    def _load_users(self):
        try:
            if self.auth_db_path.exists():
                with open(self.auth_db_path, 'r') as f:
                    data = json.load(f)
                    self.users = {
                        username: User(
                            username=username,
                            password_hash=user_data['password_hash'],
                            roles=user_data['roles']
                        )
                        for username, user_data in data.items()
                    }
            logger.log_operation("AUTH", "LOAD", "SUCCESS", f"Loaded {len(self.users)} users")
        except Exception as e:
            logger.log_operation("AUTH", "LOAD", "FAILED", str(e))
            raise

    def _save_users(self):
        try:
            data = {
                user.username: {
                    "password_hash": user.password_hash,
                    "roles": user.roles
                }
                for user in self.users.values()
            }
            with open(self.auth_db_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.log_operation("AUTH", "SAVE", "SUCCESS", f"Saved {len(self.users)} users")
        except Exception as e:
            logger.log_operation("AUTH", "SAVE", "FAILED", str(e))
            raise

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, password: str, roles: list = None) -> User:
        if username in self.users:
            raise ValueError("User already exists")
        if not roles:
            roles = ["read"]
            
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            roles=roles
        )
        self.users[username] = user
        self._save_users()
        logger.log_operation("AUTH", "CREATE_USER", "SUCCESS", f"username:{username}")
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user and user.password_hash == self._hash_password(password):
            logger.log_operation("AUTH", "AUTHENTICATE", "SUCCESS", f"username:{username}")
            return user
        logger.log_operation("AUTH", "AUTHENTICATE", "FAILED", f"username:{username}")
        return None

    def delete_user(self, username: str):
        if username in self.users:
            del self.users[username]
            self._save_users()
            logger.log_operation("AUTH", "DELETE_USER", "SUCCESS", f"username:{username}")
            return True
        return False

    def update_user_roles(self, username: str, roles: list):
        if username in self.users:
            self.users[username].roles = roles
            self._save_users()
            logger.log_operation("AUTH", "UPDATE_ROLES", "SUCCESS", f"username:{username}, roles:{roles}")
            return True
        return False
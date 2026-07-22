from typing import List
from backend.platform.config.security import ROLE_PERMISSIONS, ROLES_HIERARCHY

class PermissionManager:
    @staticmethod
    def has_permission(user_role: str, required_permission: str) -> bool:
        if user_role not in ROLE_PERMISSIONS:
            return False
        
        user_permissions = ROLE_PERMISSIONS[user_role]
        if "*" in user_permissions:
            return True
            
        return required_permission in user_permissions

    @staticmethod
    def is_at_least_role(user_role: str, target_role: str) -> bool:
        if user_role not in ROLES_HIERARCHY or target_role not in ROLES_HIERARCHY:
            return False
        return ROLES_HIERARCHY[user_role] >= ROLES_HIERARCHY[target_role]

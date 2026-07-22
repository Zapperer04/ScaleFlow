# Security and role permissions configurations

# Roles list
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_USER = "user"

ROLES_HIERARCHY = {
    ROLE_USER: 1,
    ROLE_MANAGER: 2,
    ROLE_ADMIN: 3
}

# Permissions mapping to endpoints/actions
ROLE_PERMISSIONS = {
    ROLE_USER: ["read:document", "read:chat", "write:chat"],
    ROLE_MANAGER: ["read:document", "write:document", "read:chat", "write:chat", "delete:document"],
    ROLE_ADMIN: ["*"] # All permissions
}

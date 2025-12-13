from rest_framework.permissions import BasePermission


class IsAdministrador(BasePermission):
    """Permite acceso solo a usuarios con rol 'admin'"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.perfil.rol == 'admin'
        except AttributeError:
            return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.perfil.rol == 'admin'
        except AttributeError:
            return False


class IsCliente(BasePermission):
    """Permite acceso solo a usuarios con rol 'cliente'"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.perfil.rol == 'cliente'
        except AttributeError:
            return False
    
    def has_object_permission(self, request, view, obj):
        """Cliente solo puede acceder a sus propios objetos"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            if request.user.perfil.rol != 'cliente':
                return False
            
            # Para reservas, verificar que pertenezcan al cliente
            if hasattr(obj, 'cliente'):
                return obj.cliente == request.user
            
            return False
        except AttributeError:
            return False


class IsAdminOrCliente(BasePermission):
    """Permite acceso a admin o cliente (usuario autenticado)"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsFormOwnerOrReadonly(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return obj.business.user == request.user

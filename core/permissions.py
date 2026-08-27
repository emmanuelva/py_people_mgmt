from rest_framework.permissions import IsAdminUser


class StaffRequiredForCreateMixin:
    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminUser()]
        return super().get_permissions()

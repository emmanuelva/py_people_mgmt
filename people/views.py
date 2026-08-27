from rest_framework import viewsets

from people.models import Person
from people.serializers import PersonSerializer


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer

    def get_queryset(self):
        return Person.objects.filter(deleted_at__isnull=True).order_by('last_name', 'first_name')

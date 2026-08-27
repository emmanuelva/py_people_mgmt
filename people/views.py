from rest_framework import viewsets

from core.permissions import StaffRequiredForCreateMixin
from people.models import Person, Tag
from people.serializers import PersonSerializer, TagSerializer


class TagViewSet(StaffRequiredForCreateMixin, viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(deleted_at__isnull=True).order_by('name')


class PersonViewSet(StaffRequiredForCreateMixin, viewsets.ModelViewSet):
    serializer_class = PersonSerializer

    def get_queryset(self):
        queryset = Person.objects.filter(deleted_at__isnull=True).prefetch_related('tags')

        tags = self.request.query_params.get('tags')
        if tags:
            tag_names = [tag.strip() for tag in tags.split(',') if tag.strip()]
            queryset = queryset.filter(tags__name__in=tag_names).distinct()

        return queryset.order_by('last_name', 'first_name')

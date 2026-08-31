import operator
from datetime import timedelta
from functools import reduce

from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.pagination import PageNumberSizePagination
from core.permissions import StaffRequiredForCreateMixin
from people.models import Person, Tag
from people.serializers import PersonSerializer, TagSerializer


def _week_bounds(reference_date):
    monday = reference_date - timedelta(days=reference_date.weekday())
    return monday, monday + timedelta(days=6)


def _birthday_query(monday, sunday):
    days = [monday + timedelta(days=offset) for offset in range((sunday - monday).days + 1)]
    return reduce(operator.or_, (Q(month_of_birth=day.month, day_of_birth=day.day) for day in days))


class TagViewSet(StaffRequiredForCreateMixin, viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(deleted_at__isnull=True).order_by('name')


class PersonViewSet(StaffRequiredForCreateMixin, viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    pagination_class = PageNumberSizePagination

    def get_queryset(self):
        queryset = Person.objects.filter(deleted_at__isnull=True).prefetch_related(
            Prefetch('tags', queryset=Tag.objects.filter(deleted_at__isnull=True))
        )

        tags = self.request.query_params.get('tags')
        if tags:
            tag_names = [tag.strip() for tag in tags.split(',') if tag.strip()]
            queryset = queryset.filter(tags__name__in=tag_names).distinct()

        return queryset.order_by('name')

    @action(detail=False, methods=['get'])
    def birthdays(self, request):
        current_monday, current_sunday = _week_bounds(timezone.localdate())
        next_monday, next_sunday = current_monday + timedelta(days=7), current_sunday + timedelta(days=7)

        base_queryset = self.get_queryset()

        def serialize(monday, sunday):
            people = base_queryset.filter(_birthday_query(monday, sunday)).order_by(
                'month_of_birth', 'day_of_birth', 'name'
            )
            return PersonSerializer(people, many=True).data

        return Response({
            'current': serialize(current_monday, current_sunday),
            'next': serialize(next_monday, next_sunday),
        })

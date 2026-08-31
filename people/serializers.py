from django.utils import timezone
from rest_framework import serializers

from people.models import Person, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PersonSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.filter(deleted_at__isnull=True), required=False
    )
    age = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            'id',
            'name',
            'normalized_name',
            'external_id',
            'dob',
            'day_of_birth',
            'month_of_birth',
            'age',
            'gender',
            'status',
            'marital_status',
            'phone',
            'email',
            'tags',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'normalized_name', 'day_of_birth', 'month_of_birth', 'created_at', 'updated_at',
        ]

    def get_age(self, obj) -> int | None:
        if not obj.dob:
            return None
        today = timezone.localdate()
        had_birthday_this_year = (today.month, today.day) >= (obj.dob.month, obj.dob.day)
        return today.year - obj.dob.year - (0 if had_birthday_this_year else 1)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return representation

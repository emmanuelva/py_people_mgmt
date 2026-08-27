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

    class Meta:
        model = Person
        fields = [
            'id',
            'first_name',
            'last_name',
            'second_last_name',
            'dob',
            'day_of_birth',
            'month_of_birth',
            'gender',
            'status',
            'phone',
            'email',
            'tags',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'day_of_birth', 'month_of_birth', 'created_at', 'updated_at']

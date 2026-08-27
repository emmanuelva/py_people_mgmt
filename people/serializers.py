from rest_framework import serializers

from people.models import Person


class PersonSerializer(serializers.ModelSerializer):
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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'day_of_birth', 'month_of_birth', 'created_at', 'updated_at']

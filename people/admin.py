from django.contrib import admin

from people.models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'second_last_name', 'gender', 'status', 'email', 'phone')
    list_filter = ('gender', 'status')
    search_fields = ('first_name', 'last_name', 'second_last_name', 'email', 'phone')

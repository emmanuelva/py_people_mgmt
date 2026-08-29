from django.contrib import admin

from people.models import Person, Tag


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'gender', 'status', 'marital_status', 'email', 'phone')
    list_filter = ('gender', 'status', 'marital_status', 'tags')
    search_fields = ('name', 'normalized_name', 'external_id', 'email', 'phone')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

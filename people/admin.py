from django.contrib import admin

from people.models import Person, Tag


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'status', 'email', 'phone')
    list_filter = ('gender', 'status', 'tags')
    search_fields = ('name', 'normalized_name', 'email', 'phone')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

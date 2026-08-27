import re
import unicodedata

from django.db import models

from core.models import SoftDeleteModel


def normalize_name(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    return re.sub(r'\s+', ' ', name).strip().lower()


class Tag(SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Person(SoftDeleteModel):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        MEMBER = 'member', 'Member'

    name = models.CharField(max_length=250)
    normalized_name = models.CharField(max_length=250, editable=False, blank=True)
    dob = models.DateField(null=True, blank=True)
    day_of_birth = models.SmallIntegerField(null=True, blank=True, editable=False)
    month_of_birth = models.SmallIntegerField(null=True, blank=True, editable=False)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='people', blank=True)

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.name)
        if self.dob:
            self.day_of_birth = self.dob.day
            self.month_of_birth = self.dob.month
        else:
            self.day_of_birth = None
            self.month_of_birth = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

from django.db import models

from core.models import SoftDeleteModel


class Person(SoftDeleteModel):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        MEMBER = 'member', 'Member'

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    second_last_name = models.CharField(max_length=150, blank=True)
    dob = models.DateField(null=True, blank=True)
    day_of_birth = models.SmallIntegerField(null=True, blank=True, editable=False)
    month_of_birth = models.SmallIntegerField(null=True, blank=True, editable=False)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def save(self, *args, **kwargs):
        if self.dob:
            self.day_of_birth = self.dob.day
            self.month_of_birth = self.dob.month
        else:
            self.day_of_birth = None
            self.month_of_birth = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

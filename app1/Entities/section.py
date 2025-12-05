from django.db import models
from django.contrib.auth.models import User


class Section(models.Model):
    name = models.CharField(max_length=100)
    manager = models.ManyToManyField(User)

    def __str__(self):
        return self.name

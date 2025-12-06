from django.db import models
from django.contrib.auth.models import User


class Station(models.Model):
    """Represents a workflow stage/station"""
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    description = models.TextField(blank=True, null=True)
    is_initial = models.BooleanField(default=False, help_text='Is this a starting station?')
    is_final = models.BooleanField(default=False, help_text='Is this a completion station?')
    color = models.CharField(max_length=7, blank=True, null=True, help_text='Hex color code (e.g., #FF5733)')
    order = models.IntegerField(default=0, help_text='Global display order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'

    def __str__(self):
        return f"{self.name} ({self.name_ar})"

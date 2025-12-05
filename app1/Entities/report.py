from django.db import models
from django.contrib.auth.models import User
from .service_request import ServiceRequest


class Report(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    needs_outsourcing = models.BooleanField(default=False)
    needs_items = models.BooleanField(default=False)

    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title + ' - ' + self.service_request.title

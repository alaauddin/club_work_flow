from django.db import models
from django.contrib.auth.models import User
from .service_request import ServiceRequest
from .station import Station


class ServiceRequestLog(models.Model):
    LOG_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('station_change', 'Station Change'),
        ('assignment', 'Assignment Change'),
        ('update', 'General Update'),
    ]
    
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='logs')
    from_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_from')
    to_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_to')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default='comment')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Service Request Log'
        verbose_name_plural = 'Service Request Logs'

    def __str__(self):
        if self.log_type == 'station_change' and self.from_station and self.to_station:
            return f"{self.service_request.title} - {self.from_station.name} → {self.to_station.name}"
        return self.service_request.title + ' - ' + self.comment[:50]

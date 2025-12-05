from django.db import models
from django.contrib.auth.models import User
from .report import Report


class InventoryOrder(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='inventory_order')
    refrence_number = models.CharField(max_length=100)
    status = models.CharField(
        max_length=100, 
        choices=[
            ('pending', 'قيد العمل'), 
            ('used', 'تم الاستلام والاستخدام')
        ], 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.report.title

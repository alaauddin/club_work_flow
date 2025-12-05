from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Section(models.Model):
    name = models.CharField(max_length=100)
    manager  = models.ManyToManyField(User)

    def __str__(self):
        return self.name
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=100)
    image = models.ImageField(upload_to='profile_images', null=True, blank=True)

    def __str__(self):
        return self.user.username
    

class ServiceProvider(models.Model):
    name = models.CharField(max_length=100)
    manager = models.ManyToManyField(User)

    def __str__(self):
        return self.name
    



class ServiceRequest(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    status = models.CharField(max_length=100, choices=[('pending', 'قيد الانتظار'), ('in_progress', 'قيد التنفيذ'), ('under_review', 'قيد المراجعة'), ('completed', 'مكتمل')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_by')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_to', null=True, blank=True)

    def __str__(self):
        return self.title


class ServiceRequestLog(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.service_request.title + ' - ' + self.comment
    



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
    

class CompletionReport(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title + ' - ' + self.service_request.title
    



class PurchaseOrder(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='purchase_order')
    refrence_number = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=[ ('approved', 'جاهز للشراء'), ('supplied', 'تم التوريد'),('used','تم الاستخدام')], default='approved')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.report.title 
    

class InventoryOrder(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='inventory_order')
    refrence_number = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=[('pending', 'قيد العمل'), ('used', 'تم الاستلام والاستخدام')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.report.title 
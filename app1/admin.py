from django.contrib import admin
from .models import Section, ServiceProvider, ServiceRequest, ServiceRequestLog, Report, CompletionReport, PurchaseOrder, InventoryOrder
from .models import UserProfile
# Register your models here.

admin.site.register(Section)
admin.site.register(ServiceProvider)
admin.site.register(ServiceRequest)
admin.site.register(ServiceRequestLog)
admin.site.register(Report)
admin.site.register(CompletionReport)
admin.site.register(PurchaseOrder)
admin.site.register(InventoryOrder)
admin.site.register(UserProfile)
# Compare this snippet from app1/templates/read/home.html:
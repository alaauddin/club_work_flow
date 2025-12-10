from django.contrib import admin
from django.contrib.auth.models import User
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Section, ServiceProvider, ServiceRequest, ServiceRequestLog, Report, CompletionReport, PurchaseOrder, InventoryOrder
from .models import UserProfile
# Register your models here.

# User Resource for import/export
class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'is_superuser', 'date_joined', 'last_login')
        export_order = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'is_superuser', 'date_joined', 'last_login')

# User Admin with import/export
class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')

# Unregister User if already registered, then register with our custom admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
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
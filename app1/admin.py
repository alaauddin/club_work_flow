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
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

# Admin classes with import/export for all models
@admin.register(Section)
class SectionAdmin(ImportExportModelAdmin):
    list_display = ['name']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(UserProfile)
class UserProfileAdmin(ImportExportModelAdmin):
    list_display = ['user', 'phone']
    search_fields = ['user__username', 'phone']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(ServiceProvider)
class ServiceProviderAdmin(ImportExportModelAdmin):
    list_display = ['name']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(ServiceRequest)
class ServiceRequestAdmin(ImportExportModelAdmin):
    list_display = ['title', 'section', 'service_provider', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'section', 'service_provider', 'created_at']
    search_fields = ['title', 'description']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(ServiceRequestLog)
class ServiceRequestLogAdmin(ImportExportModelAdmin):
    list_display = ['service_request', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['service_request__title', 'comment']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(Report)
class ReportAdmin(ImportExportModelAdmin):
    list_display = ['title', 'service_request', 'needs_outsourcing', 'needs_items', 'created_by', 'created_at']
    list_filter = ['needs_outsourcing', 'needs_items', 'created_at']
    search_fields = ['title', 'description', 'service_request__title']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(CompletionReport)
class CompletionReportAdmin(ImportExportModelAdmin):
    list_display = ['title', 'service_request', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'service_request__title']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ImportExportModelAdmin):
    list_display = ['report', 'refrence_number', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refrence_number', 'report__title']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

@admin.register(InventoryOrder)
class InventoryOrderAdmin(ImportExportModelAdmin):
    list_display = ['report', 'refrence_number', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refrence_number', 'report__title']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

# Unregister User if already registered, then register with our custom admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
# Compare this snippet from app1/templates/read/home.html:
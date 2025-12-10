from django.contrib import admin
from django.contrib.auth.models import User
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Section, UserProfile, ServiceProvider, Station, Pipeline, PipelineStation,
    ServiceRequest, ServiceRequestLog, Report, CompletionReport, 
    PurchaseOrder, InventoryOrder
)

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

# Unregister User if already registered, then register with our custom admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


@admin.register(Section)
class SectionAdmin(ImportExportModelAdmin):
    list_display = ['name']
    filter_horizontal = ['manager']
    
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
    filter_horizontal = ['manager']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass


@admin.register(Station)
class StationAdmin(ImportExportModelAdmin):
    list_display = ['name', 'name_ar', 'is_initial', 'is_final', 'order', 'color']
    list_editable = ['order']
    list_filter = ['is_initial', 'is_final']
    search_fields = ['name', 'name_ar']
    ordering = ['order', 'name']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass


class PipelineStationInline(admin.TabularInline):
    model = PipelineStation
    extra = 1
    fields = ['station', 'order', 'can_skip', 'allowed_users']
    filter_horizontal = ['allowed_users']
    ordering = ['order']


@admin.register(Pipeline)
class PipelineAdmin(ImportExportModelAdmin):
    list_display = ['name', 'name_ar', 'is_active', 'created_at']
    list_filter = ['is_active', 'sections']
    search_fields = ['name', 'name_ar']
    filter_horizontal = ['sections']
    inlines = [PipelineStationInline]
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass
    

@admin.register(PipelineStation)
class PipelineStationAdmin(ImportExportModelAdmin):
    list_display = ['pipeline', 'station', 'order', 'can_skip']
    list_filter = ['pipeline', 'can_skip']
    filter_horizontal = ['allowed_users']
    ordering = ['pipeline', 'order']
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass


class ServiceRequestLogInline(admin.TabularInline):
    model = ServiceRequestLog
    extra = 0
    readonly_fields = ['from_station', 'to_station', 'log_type', 'comment', 'created_at', 'created_by']
    can_delete = False
    fields = ['log_type', 'from_station', 'to_station', 'comment', 'created_by', 'created_at']
    ordering = ['-created_at']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(ImportExportModelAdmin):
    list_display = ['title', 'section', 'service_provider', 'pipeline', 'current_station', 'get_progress', 'created_by', 'created_at']
    list_filter = ['current_station', 'pipeline', 'section', 'service_provider']
    search_fields = ['title', 'description']
    readonly_fields = ['station_entered_at', 'created_at', 'updated_at', 'get_progress']
    inlines = [ServiceRequestLogInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'section', 'service_provider')
        }),
        ('Workflow', {
            'fields': ('pipeline', 'current_station', 'station_entered_at', 'get_progress')
        }),
        ('Assignment', {
            'fields': ('assigned_to',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_progress(self, obj):
        """Display progress percentage"""
        return f"{obj.get_pipeline_progress()}%"
    get_progress.short_description = 'Progress'
    
    actions = ['move_to_next_station']
    
    def move_to_next_station(self, request, queryset):
        """Admin action to move selected requests to next station"""
        success_count = 0
        for service_request in queryset:
            success, message = service_request.move_to_next_station(request.user, comment='Moved by admin')
            if success:
                success_count += 1
        
        self.message_user(request, f'Successfully moved {success_count} request(s) to next station.')
    move_to_next_station.short_description = 'Move to Next Station'
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass


@admin.register(ServiceRequestLog)
class ServiceRequestLogAdmin(ImportExportModelAdmin):
    list_display = ['service_request', 'log_type', 'from_station', 'to_station', 'created_by', 'created_at']
    list_filter = ['log_type', 'from_station', 'to_station', 'created_at']
    search_fields = ['service_request__title', 'comment']
    readonly_fields = ['service_request', 'from_station', 'to_station', 'log_type', 'comment', 'created_at', 'created_by']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
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
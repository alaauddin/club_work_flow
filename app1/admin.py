from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    Section, UserProfile, ServiceProvider, Station, Pipeline, PipelineStation,
    ServiceRequest, ServiceRequestLog, Report, CompletionReport, 
    PurchaseOrder, InventoryOrder
)

# Register your models here.

# Base admin class combining Unfold ModelAdmin with ImportExport functionality
# Using multiple inheritance to get both Unfold styling and import/export features
class UnfoldImportExportModelAdmin(ImportExportModelAdmin, ModelAdmin):
    """Combines Unfold's ModelAdmin with django-import-export functionality"""
    
    # Disable logging to avoid compatibility issue with Django 5.x
    def generate_log_entries(self, result, request):
        """Override to skip logging due to Django 5.x compatibility issue"""
        pass

# User Resource for import/export
class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'is_superuser', 'date_joined', 'last_login')
        export_order = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'is_superuser', 'date_joined', 'last_login')
        import_id_fields = ('username',)  # Match by username - allows override even with different id
        skip_unchanged = False  # Allow updates even if unchanged
        report_skipped = True
        use_natural_foreign_keys = False
    
    def before_import_row(self, row, **kwargs):
        """Custom validation and processing before importing a user row"""
        # Ensure required fields are present
        if 'username' not in row or not row.get('username'):
            raise ValueError("Username is required")
        
        # Normalize email if provided
        if 'email' in row and row.get('email'):
            row['email'] = row['email'].strip().lower()
        
        # Set default values for boolean fields if not provided
        if 'is_staff' not in row or row.get('is_staff') == '':
            row['is_staff'] = False
        if 'is_active' not in row or row.get('is_active') == '':
            row['is_active'] = True
        if 'is_superuser' not in row or row.get('is_superuser') == '':
            row['is_superuser'] = False
        
        return row
    
    def after_import_instance(self, instance, row, **kwargs):
        """Custom processing after user instance is created/updated"""
        # Additional processing can be added here if needed
        return instance
    
    def save_instance(self, instance, using_transactions=True, dry_run=False):
        """Set password to '123' for all imported users"""
        if not dry_run:
            # Set password to '123' for all users during import
            instance.set_password('123')
        return super().save_instance(instance, using_transactions, dry_run)

# Resource classes for all models - configured to allow override/update even with different IDs
class SectionResource(resources.ModelResource):
    class Meta:
        model = Section
        import_id_fields = ('name',)  # Match by name first, allows override even with different id
        skip_unchanged = False  # Allow updates even if unchanged
        fields = ('id', 'name', 'manager')
    
    def before_import_row(self, row, **kwargs):
        """Custom validation and processing before importing a section row"""
        # Ensure name is present
        if 'name' not in row or not row.get('name'):
            raise ValueError("Section name is required")
        return row
    
    def after_import_instance(self, instance, row, **kwargs):
        """Handle manager ManyToMany relationship after instance is created/updated"""
        # Handle manager field if provided in CSV
        # Expected format: comma-separated usernames (e.g., "user1,user2,user3")
        if 'manager' in row and row.get('manager'):
            manager_usernames = [username.strip() for username in str(row['manager']).split(',') if username.strip()]
            managers = User.objects.filter(username__in=manager_usernames)
            instance.manager.set(managers)
        return instance

class UserProfileResource(resources.ModelResource):
    class Meta:
        model = UserProfile
        import_id_fields = ('user',)  # Match by user, allows override even with different id
        skip_unchanged = False

class ServiceProviderResource(resources.ModelResource):
    class Meta:
        model = ServiceProvider
        import_id_fields = ('name',)  # Match by name, allows override even with different id
        skip_unchanged = False
        fields = ('id', 'name', 'manager')
    
    def before_import_row(self, row, **kwargs):
        """Custom validation and processing before importing a service provider row"""
        # Ensure name is present
        if 'name' not in row or not row.get('name'):
            raise ValueError("Service provider name is required")
        return row
    
    def after_import_instance(self, instance, row, **kwargs):
        """Handle manager ManyToMany relationship after instance is created/updated"""
        # Handle manager field if provided in CSV
        # Expected format: comma-separated usernames (e.g., "user1,user2,user3")
        if 'manager' in row and row.get('manager'):
            manager_usernames = [username.strip() for username in str(row['manager']).split(',') if username.strip()]
            managers = User.objects.filter(username__in=manager_usernames)
            instance.manager.set(managers)
        return instance

class StationResource(resources.ModelResource):
    class Meta:
        model = Station
        import_id_fields = ('name',)  # Match by name, allows override even with different id
        skip_unchanged = False

class PipelineResource(resources.ModelResource):
    class Meta:
        model = Pipeline
        import_id_fields = ('name',)  # Match by name, allows override even with different id
        skip_unchanged = False

class PipelineStationResource(resources.ModelResource):
    class Meta:
        model = PipelineStation
        import_id_fields = ('id',)  # Match by id
        skip_unchanged = False

class ServiceRequestResource(resources.ModelResource):
    class Meta:
        model = ServiceRequest
        import_id_fields = ('title',)  # Match by title, allows override even with different id
        skip_unchanged = False

class ServiceRequestLogResource(resources.ModelResource):
    class Meta:
        model = ServiceRequestLog
        import_id_fields = ('id',)  # Match by id
        skip_unchanged = False

class ReportResource(resources.ModelResource):
    class Meta:
        model = Report
        import_id_fields = ('title',)  # Match by title, allows override even with different id
        skip_unchanged = False

class CompletionReportResource(resources.ModelResource):
    class Meta:
        model = CompletionReport
        import_id_fields = ('title',)  # Match by title, allows override even with different id
        skip_unchanged = False

class PurchaseOrderResource(resources.ModelResource):
    class Meta:
        model = PurchaseOrder
        import_id_fields = ('refrence_number',)  # Match by reference number, allows override even with different id
        skip_unchanged = False

class InventoryOrderResource(resources.ModelResource):
    class Meta:
        model = InventoryOrder
        import_id_fields = ('refrence_number',)  # Match by reference number, allows override even with different id
        skip_unchanged = False

# User Admin with import/export
class UserAdmin(UnfoldImportExportModelAdmin):
    resource_class = UserResource
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'view_details_link')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ['view_selected_details', 'activate_users', 'deactivate_users']
    
    def view_details_link(self, obj):
        """Create a link to view user details"""
        url = reverse('user_detail_view', args=[obj.pk])
        return format_html('<a href="{}">View Details</a>', url)
    view_details_link.short_description = 'Actions'
    
    def view_selected_details(self, request, queryset):
        """Admin action to view details of selected users"""
        if queryset.count() == 1:
            # If only one user selected, redirect to detail view
            user = queryset.first()
            return redirect('user_detail_view', pk=user.pk)
        else:
            # If multiple users, show list view
            return redirect('user_list_view')
    view_selected_details.short_description = 'View details of selected users'
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'Successfully activated {count} user(s).')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {count} user(s).')
    deactivate_users.short_description = 'Deactivate selected users'

# Unregister User if already registered, then register with our custom admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


@admin.register(Section)
class SectionAdmin(UnfoldImportExportModelAdmin):
    resource_class = SectionResource
    list_display = ['name', 'get_manager_count', 'view_details_link']
    filter_horizontal = ['manager']
    actions = ['view_selected_details']
    
    def get_manager_count(self, obj):
        """Display count of managers"""
        return obj.manager.count()
    get_manager_count.short_description = 'Managers'
    
    def view_details_link(self, obj):
        """Create a link to view section details"""
        url = reverse('section_detail_view', args=[obj.pk])
        return format_html('<a href="{}">View Details</a>', url)
    view_details_link.short_description = 'Actions'
    
    def view_selected_details(self, request, queryset):
        """Admin action to view details of selected sections"""
        if queryset.count() == 1:
            section = queryset.first()
            return redirect('section_detail_view', pk=section.pk)
        else:
            return redirect('section_list_view')
    view_selected_details.short_description = 'View details of selected sections'


@admin.register(UserProfile)
class UserProfileAdmin(UnfoldImportExportModelAdmin):
    resource_class = UserProfileResource
    list_display = ['user', 'phone']
    search_fields = ['user__username', 'phone']


@admin.register(ServiceProvider)
class ServiceProviderAdmin(UnfoldImportExportModelAdmin):
    resource_class = ServiceProviderResource
    list_display = ['name', 'get_manager_count', 'view_details_link']
    filter_horizontal = ['manager']
    actions = ['view_selected_details']
    
    def get_manager_count(self, obj):
        """Display count of managers"""
        return obj.manager.count()
    get_manager_count.short_description = 'Managers'
    
    def view_details_link(self, obj):
        """Create a link to view service provider details"""
        url = reverse('serviceprovider_detail_view', args=[obj.pk])
        return format_html('<a href="{}">View Details</a>', url)
    view_details_link.short_description = 'Actions'
    
    def view_selected_details(self, request, queryset):
        """Admin action to view details of selected service providers"""
        if queryset.count() == 1:
            provider = queryset.first()
            return redirect('serviceprovider_detail_view', pk=provider.pk)
        else:
            return redirect('serviceprovider_list_view')
    view_selected_details.short_description = 'View details of selected service providers'


@admin.register(Station)
class StationAdmin(UnfoldImportExportModelAdmin):
    resource_class = StationResource
    list_display = ['name', 'name_ar', 'is_initial', 'is_final', 'order', 'color']
    list_editable = ['order']
    list_filter = ['is_initial', 'is_final']
    search_fields = ['name', 'name_ar']
    ordering = ['order', 'name']


class PipelineStationInline(TabularInline):
    model = PipelineStation
    extra = 1
    fields = ['station', 'order', 'can_skip', 'allowed_users', 'can_create_purchase_order', 'can_create_inventory_order', 'can_create_completion_report', 'can_send_back', 'can_edit_completion_report', 'can_edit_purchase_order', 'can_edit_inventory_order', 'show_assigned_requests', 'show_the_managers_only']
    filter_horizontal = ['allowed_users']
    ordering = ['order']


@admin.register(Pipeline)
class PipelineAdmin(UnfoldImportExportModelAdmin):
    resource_class = PipelineResource
    list_display = ['name', 'name_ar', 'is_active', 'created_at']
    list_filter = ['is_active', 'sections']
    search_fields = ['name', 'name_ar']
    filter_horizontal = ['sections']
    inlines = [PipelineStationInline]
    

@admin.register(PipelineStation)
class PipelineStationAdmin(UnfoldImportExportModelAdmin):
    resource_class = PipelineStationResource
    list_display = ['pipeline', 'station', 'order', 'can_skip']
    list_filter = ['pipeline', 'can_skip']
    filter_horizontal = ['allowed_users']
    ordering = ['pipeline', 'order']


class ServiceRequestLogInline(TabularInline):
    model = ServiceRequestLog
    extra = 0
    readonly_fields = ['from_station', 'to_station', 'log_type', 'comment', 'created_at', 'created_by']
    can_delete = False
    fields = ['log_type', 'from_station', 'to_station', 'comment', 'created_by', 'created_at']
    ordering = ['-created_at']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(UnfoldImportExportModelAdmin):
    resource_class = ServiceRequestResource
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


@admin.register(ServiceRequestLog)
class ServiceRequestLogAdmin(UnfoldImportExportModelAdmin):
    resource_class = ServiceRequestLogResource
    list_display = ['service_request', 'log_type', 'from_station', 'to_station', 'created_by', 'created_at']
    list_filter = ['log_type', 'from_station', 'to_station', 'created_at']
    search_fields = ['service_request__title', 'comment']
    readonly_fields = ['service_request', 'from_station', 'to_station', 'log_type', 'comment', 'created_at', 'created_by']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(UnfoldImportExportModelAdmin):
    resource_class = ReportResource
    list_display = ['title', 'service_request', 'needs_outsourcing', 'needs_items', 'created_by', 'created_at']
    list_filter = ['needs_outsourcing', 'needs_items', 'created_at']
    search_fields = ['title', 'description', 'service_request__title']


@admin.register(CompletionReport)
class CompletionReportAdmin(UnfoldImportExportModelAdmin):
    resource_class = CompletionReportResource
    list_display = ['title', 'service_request', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'service_request__title']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(UnfoldImportExportModelAdmin):
    resource_class = PurchaseOrderResource
    list_display = ['report', 'refrence_number', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refrence_number', 'report__title']


@admin.register(InventoryOrder)
class InventoryOrderAdmin(UnfoldImportExportModelAdmin):
    resource_class = InventoryOrderResource
    list_display = ['report', 'refrence_number', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refrence_number', 'report__title']
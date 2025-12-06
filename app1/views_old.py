from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.core.serializers import serialize
from django.utils.dateformat import format as date_format
from django.contrib.auth.models import User

from app1.forms import CompletionReportForm, InventoryOrderForm, PurchaseOrderForm, ServiceRequestLogForm
from .models import *

import json
import threading
import requests
import logging
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

def send_message(number, message):
    def send():
        data = {
            "User": "Altarfeehi",
            "Pass": "Altarfeehi@277",
            "Method": "Chat",
            "To": str(number),
            "Body": str(message)
        }
        try:
            response = requests.post(
                url="http://185.216.203.97:8070/AWE/Api/index.php",
                data=data,
                timeout=20
            )
            print(response.json())
        except Exception as e:
            print(f"Message sending failed: {e}")
    
    threading.Thread(target=send).start()


# ============================================================================
# HELPER FUNCTIONS FOR STATION WORKFLOW
# ============================================================================

def can_user_access_station(user, station, service_request=None):
    """Check if user is allowed to work in this station
    
    Args:
        user: The user to check
        station: The station to check access for
        service_request: Optional ServiceRequest to get pipeline context
    
    Returns:
        bool: True if user can access the station, False otherwise
    """
    # If we have a service request with a pipeline, check pipeline-station permissions
    if service_request and service_request.pipeline:
        try:
            pipeline_station = PipelineStation.objects.get(
                pipeline=service_request.pipeline,
                station=station
            )
            # Check if allowed_users is empty (unrestricted) or user is in allowed_users
            if not pipeline_station.allowed_users.exists():
                return True  # No restrictions
            return pipeline_station.allowed_users.filter(id=user.id).exists()
        except PipelineStation.DoesNotExist:
            return False
    
    # Without pipeline context, check if user has access through ANY pipeline-station
    user_pipeline_stations = PipelineStation.objects.filter(
        station=station
    ).filter(
        Q(allowed_users=user) | ~Q(allowed_users__isnull=False)
    )
    
    return user_pipeline_stations.exists()


def get_station_by_name(name):
    """Get station by name, returns None if not found"""
    try:
        return Station.objects.get(name=name)
    except Station.DoesNotExist:
        return None

@login_required
def home(request):
    """Analytics dashboard with statistics and charts"""
    
    # Overall statistics
    total_requests = ServiceRequest.objects.count()
    my_requests_count = ServiceRequest.objects.filter(created_by=request.user).count()
    requests_to_me_count = ServiceRequest.objects.filter(assigned_to=request.user).count()
    requests_without_pipeline = ServiceRequest.objects.filter(pipeline__isnull=True).count()
    
    # Station-based statistics
    stations = Station.objects.all().order_by('order')
    station_data = []
    station_labels = []
    station_colors = []
    
    for station in stations:
        count = ServiceRequest.objects.filter(current_station=station).count()
        if count > 0:  # Only include stations with requests
            station_labels.append(station.name_ar)
            station_data.append(count)
            station_colors.append(station.color)
    
    # Pipeline statistics
    from django.db.models import Count
    pipeline_stats = ServiceRequest.objects.filter(
        pipeline__isnull=False
    ).values('pipeline__name_ar').annotate(count=Count('id')).order_by('-count')
    
    pipeline_labels = [p['pipeline__name_ar'] for p in pipeline_stats]
    pipeline_data = [p['count'] for p in pipeline_stats]
    
    # Requests over time (last 30 days)
    from datetime import datetime, timedelta
    from django.db.models.functions import TruncDate
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_requests = ServiceRequest.objects.filter(
        created_at__gte=thirty_days_ago
    ).annotate(date=TruncDate('created_at')).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Create date labels for last 30 days
    date_labels = []
    date_data = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i)).date()
        date_labels.append(date.strftime('%m/%d'))
        # Find count for this date
        count = next((d['count'] for d in daily_requests if d['date'] == date), 0)
        date_data.append(count)
    
    context = {
        'total_requests': total_requests,
        'my_requests_count': my_requests_count,
        'requests_to_me_count': requests_to_me_count,
        'requests_without_pipeline': requests_without_pipeline,
        # Chart data
        'station_labels': json.dumps(station_labels),
        'station_data': json.dumps(station_data),
        'station_colors': json.dumps(station_colors),
        'pipeline_labels': json.dumps(pipeline_labels),
        'pipeline_data': json.dumps(pipeline_data),
        'date_labels': json.dumps(date_labels),
        'date_data': json.dumps(date_data),
    }

    return render(request, 'read/home.html', context)


def my_request(request):
    section = Section.objects.filter(manager=request.user)
    filter_type = request.GET.get('filter', 'all')
    
    service_requests = ServiceRequest.objects.filter(section__in=section)

    if filter_type == 'supplied':
        service_requests = service_requests.filter(
            reports__purchase_order__status='supplied'
        )
    elif filter_type != 'all':
        # Try to filter by station name
        station = get_station_by_name(filter_type.replace('_', ' ').title())
        if station:
            service_requests = service_requests.filter(current_station=station)
    
    service_requests = service_requests.order_by('-id').distinct()

    # Get all stations for filter dropdown
    stations = Station.objects.all().order_by('order')

    context = {
        'service_requests': service_requests,
        'filter': filter_type,
        'stations': stations,
    }
    return render(request, 'read/my_request.html', context)


def my_stations(request):
    """Show stations the user has access to"""
    
    # Superusers see ALL stations with ALL requests
    if request.user.is_superuser:
        # Get all pipeline-stations
        all_pipeline_stations = PipelineStation.objects.all().select_related('station', 'pipeline').distinct()
        
        # Group by station and calculate counts (all requests, no filtering)
        from collections import defaultdict
        station_data = defaultdict(lambda: {'pipelines': [], 'total_count': 0, 'station_obj': None})
        
        for ps in all_pipeline_stations:
            station = ps.station
            
            # Count ALL requests in this station for this pipeline (no user filtering)
            request_count = ServiceRequest.objects.filter(
                current_station=station,
                pipeline=ps.pipeline
            ).count()
            
            station_data[station.id]['station_obj'] = station
            station_data[station.id]['pipelines'].append(ps.pipeline)
            station_data[station.id]['total_count'] += request_count
    else:
        # Normal users: filter by permissions
        # Get all pipeline-station combinations the user is allowed to access
        if request.user.is_authenticated:
            # Show pipeline-stations where user is in allowed_users OR where allowed_users is empty (unrestricted)
            allowed_pipeline_stations = PipelineStation.objects.filter(
                Q(allowed_users=request.user) | ~Q(allowed_users__isnull=False)
            ).select_related('station', 'pipeline').distinct()
        else:
            # For anonymous users, show unrestricted pipeline-stations
            allowed_pipeline_stations = PipelineStation.objects.filter(
                allowed_users__isnull=True
            ).select_related('station', 'pipeline').distinct()
        logger.info(f'here are the request allowed_pipeline_stations {allowed_pipeline_stations}')
        
        # Group by station and calculate counts
        from collections import defaultdict
        station_data = defaultdict(lambda: {'pipelines': [], 'total_count': 0, 'station_obj': None})
        
        for ps in allowed_pipeline_stations:
            station = ps.station
            
            # Start with base filter for station and pipeline
            base_filter = Q(current_station=station, pipeline=ps.pipeline)
            
            # Add show_assigned_requests filter if enabled
            if ps.show_assigned_requests:
                base_filter &= Q(assigned_to=request.user)
            
            # Add show_the_managers_only filter if enabled
            if ps.show_the_managers_only:
                # Only show requests from sections where current user is a manager
                base_filter &= Q(section__manager=request.user)
            
            # Count requests with combined filters
            request_count = ServiceRequest.objects.filter(base_filter).count()
            logger.info(f'Pipeline-Station {ps}: request count {request_count} (show_assigned={ps.show_assigned_requests}, show_managers_only={ps.show_the_managers_only})')

            station_data[station.id]['station_obj'] = station
            station_data[station.id]['pipelines'].append(ps.pipeline)
            station_data[station.id]['total_count'] += request_count
    
    # Convert to list format for template
    stations_with_counts = []
    for station_id, data in station_data.items():
        station = data['station_obj']
        stations_with_counts.append({
            'station': station,
            'count': data['total_count'],
            'is_special': False
        })
    
    # Sort by station order
    stations_with_counts.sort(key=lambda x: x['station'].order)
    
    # Add special card for requests without pipeline (SP_ADMIN only)
    is_sp_admin = request.user.groups.filter(name='SP_ADMIN').exists()
    if is_sp_admin:
        unassigned_count = ServiceRequest.objects.filter(pipeline__isnull=True).count()
        # Create a pseudo-station object for unassigned requests
        stations_with_counts.insert(0, {
            'station': None,
            'count': unassigned_count,
            'is_special': True,
            'special_type': 'unassigned_pipeline',
            'name_ar': 'طلبات بدون مسار عمل',
            'color': '#f59e0b',  # Warning orange color
            'description': 'الطلبات التي لم يتم تعيين مسار عمل لها'
        })
    
    # Add special card for requests without pipeline but assigned to current user (SP group only)
    is_sp = request.user.groups.filter(name='SP').exists()
    if is_sp:
        assigned_no_pipeline_count = ServiceRequest.objects.filter(
            pipeline__isnull=True,
            assigned_to=request.user  # Only current user's requests
        ).count()
        # Create a pseudo-station object for assigned requests without pipeline
        stations_with_counts.insert(0, {
            'station': None,
            'count': assigned_no_pipeline_count,
            'is_special': True,
            'special_type': 'assigned_no_pipeline',
            'name_ar': f'طلبات معينة لـ ({request.user.get_full_name()})',
            'color': '#3b82f6',  # Blue color
            'description': 'طلباتي المعينة لي بدون مسار عمل محدد'
        })
    
    context = {
        'stations_with_counts': stations_with_counts,
        'is_sp_admin': is_sp_admin,
        'is_sp': is_sp,
    }
    return render(request, 'read/my_stations.html', context)


def station_requests(request):
    """Display requests for a specific station or special filter"""
    station_id = request.GET.get('station', '')
    filter_type = request.GET.get('type', '')  # 'unassigned_pipeline' or 'assigned_no_pipeline'
    
    service_requests = ServiceRequest.objects.none()  # Start with empty queryset
    page_title = 'الطلبات'
    page_description = ''
    page_color = '#667eea'
    
    # Filter based on type
    if filter_type == 'unassigned_pipeline':
        # SP_ADMIN: All requests without pipeline
        service_requests = ServiceRequest.objects.filter(pipeline__isnull=True)
        page_title = 'طلبات بدون مسار عمل'
        page_description = 'جميع الطلبات التي لم يتم تعيين مسار عمل لها'
        page_color = '#f59e0b'
        
    elif filter_type == 'assigned_no_pipeline':
        # SP: Requests without pipeline assigned to current user
        service_requests = ServiceRequest.objects.filter(
            pipeline__isnull=True,
            assigned_to=request.user  # Only current user's requests
        )
        page_title = 'طلبات معينة بدون مسار'
        page_description = 'طلباتي المعينة لي بدون مسار عمل محدد'
        page_color = '#3b82f6'
        
    elif station_id:
        # Regular station filter
        try:
            station = Station.objects.get(id=station_id)
            
            # Superusers see ALL requests in the station
            logger.info(f'User {request.user} is a superuser: {request.user.is_superuser}')
            if request.user.is_superuser:
                service_requests = ServiceRequest.objects.filter(current_station=station)
                page_description = f'جميع الطلبات في محطة {station.name_ar} (عرض المشرف)'
                page_title = station.name_ar
            else:
                # Check if user has access to this station through any pipeline
                user_pipeline_stations = PipelineStation.objects.filter(
                    station=station
                ).filter(
                    Q(allowed_users=request.user) | ~Q(allowed_users__isnull=False)
                ).select_related('pipeline')
                
                if not user_pipeline_stations.exists():
                    messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه المحطة')
                    return redirect('my_stations')
                
                # Build queryset by combining requests from each accessible pipeline
                from django.db.models import Q as Q_filter
                combined_query = Q_filter()
                has_show_assigned = False
                
                for ps in user_pipeline_stations:
                    # Start with base filter for this pipeline-station
                    ps_filter = Q_filter(current_station=station, pipeline=ps.pipeline)
                    
                    # Add show_assigned_requests filter if enabled
                    if ps.show_assigned_requests:
                        ps_filter &= Q_filter(assigned_to=request.user)
                        has_show_assigned = True
                    
                    # Add show_the_managers_only filter if enabled
                    if ps.show_the_managers_only:
                        ps_filter &= Q_filter(section__manager=request.user)
                    
                    # Add this pipeline-station's filter to combined query
                    combined_query |= ps_filter
                
                service_requests = ServiceRequest.objects.filter(combined_query)
                
                # Update description based on whether any pipeline has show_assigned_requests
                if has_show_assigned:
                    page_description = f'الطلبات في محطة {station.name_ar} (بعضها مقيد بالطلبات المعينة لك)'
                else:
                    page_description = station.description or f'الطلبات في محطة {station.name_ar}'
                
                # Set page title with pipeline info if available
                if user_pipeline_stations.count() == 1:
                    page_title = f'{station.name_ar} - {user_pipeline_stations.first().pipeline.name_ar}'
                else:
                    page_title = station.name_ar
            
            page_color = station.color or '#667eea'
        except Station.DoesNotExist:
            messages.error(request, 'المحطة غير موجودة')
            return redirect('my_stations')
    
    service_requests = service_requests.order_by('-created_at').distinct()
    
    # Calculate statistics
    total_count = service_requests.count()
    pending_count = service_requests.filter(
        Q(current_station__isnull=True) | Q(current_station__is_initial=True)
    ).count()
    in_progress_count = service_requests.filter(
        current_station__isnull=False,
        current_station__is_initial=False,
        current_station__is_final=False
    ).count()
    completed_count = service_requests.filter(current_station__is_final=True).count()
    
    context = {
        'service_requests': service_requests,
        'page_title': page_title,
        'page_description': page_description,
        'page_color': page_color,
        'total_count': total_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
    }
    return render(request, 'read/station_requests.html', context)


def requests_to_me(request):
    service_providers = ServiceProvider.objects.filter(manager=request.user)
    filter_type = request.GET.get('filter', 'all')
    assigned_user_id = request.GET.get('assigned_to', '').strip()
    station_filter = request.GET.get('station', '')  # Station ID filter
    no_pipeline_filter = request.GET.get('no_pipeline', '')  # No pipeline filter
    assigned_no_pipeline_filter = request.GET.get('assigned_no_pipeline', '')  # Assigned but no pipeline filter

    # Get stations the user is allowed to access via PipelineStation
    if request.user.is_authenticated:
        # Get all pipeline-stations where user is allowed or unrestricted
        allowed_pipeline_stations = PipelineStation.objects.filter(
            Q(allowed_users=request.user) | ~Q(allowed_users__isnull=False)
        ).select_related('station').distinct()
        
        # Extract unique stations from allowed pipeline-stations
        allowed_stations = Station.objects.filter(
            id__in=allowed_pipeline_stations.values_list('station_id', flat=True)
        ).distinct().order_by('order')
    else:
        # For anonymous users, show stations from unrestricted pipeline-stations
        allowed_pipeline_stations = PipelineStation.objects.filter(
            allowed_users__isnull=True
        ).select_related('station').distinct()
        
        allowed_stations = Station.objects.filter(
            id__in=allowed_pipeline_stations.values_list('station_id', flat=True)
        ).distinct().order_by('order')
    
    # Get all stations for admin/display purposes
    all_stations = Station.objects.all().order_by('order')

    service_requests = ServiceRequest.objects.filter(service_provider__in=service_providers)

    # Filter by assigned but no pipeline if requested (SP group)
    if assigned_no_pipeline_filter == 'true':
        service_requests = service_requests.filter(
            pipeline__isnull=True,
            assigned_to__isnull=False
        )
    # Filter by no pipeline if requested (SP_ADMIN)
    elif no_pipeline_filter == 'true':
        service_requests = service_requests.filter(pipeline__isnull=True)
    # Filter by station if selected
    elif station_filter:
        try:
            selected_station = Station.objects.get(id=station_filter)
            # Check if user can access this station
            if selected_station in allowed_stations:
                service_requests = service_requests.filter(current_station=selected_station)
            else:
                messages.warning(request, 'ليس لديك صلاحية للوصول إلى هذه المحطة')
        except Station.DoesNotExist:
            pass
    
    # Legacy filters
    if filter_type == 'supplied':
        service_requests = service_requests.filter(
            reports__purchase_order__status='supplied'
        )
    elif filter_type == 'assigned_to_me':
        service_requests = service_requests.filter(assigned_to=request.user)
    elif filter_type != 'all':
        # Try to filter by station name (legacy support)
        station = get_station_by_name(filter_type.replace('_', ' ').title())
        if station and station in allowed_stations:
            service_requests = service_requests.filter(current_station=station)

    if assigned_user_id == 'unassigned':
        service_requests = service_requests.filter(assigned_to__isnull=True)
    elif assigned_user_id:
        service_requests = service_requests.filter(assigned_to_id=assigned_user_id)
    
    service_requests = service_requests.order_by('-id').distinct()
    
    filter_options = [
        {'key': 'all', 'label': 'كل الطلبات', 'icon': 'list'},
    ]
    
    # Add station-based filters (only for allowed stations)
    for station in allowed_stations:
        filter_options.append({
            'key': station.name.lower().replace(' ', '_'),
            'label': station.name_ar,
            'icon': 'circle'
        })
    
    filter_options.extend([

        {'key': 'supplied', 'label': 'طلبات مشتريات موردة', 'icon': 'check'},
        {'key': 'assigned_to_me', 'label': 'طلبات مسندة إليّ', 'icon': 'user-check'},
    ])

    assigned_users = User.objects.filter(
        assigned_to__service_provider__in=service_providers
    ).distinct().order_by('username')

    # Calculate statistics for the dashboard using DB queries
    pending_count = service_requests.filter(
        Q(current_station__isnull=True) | Q(current_station__is_initial=True)
    ).count()
    
    completed_count = service_requests.filter(current_station__is_final=True).count()
    
    in_progress_count = service_requests.filter(
        current_station__isnull=False,
        current_station__is_initial=False,
        current_station__is_final=False
    ).count()

    # Check if user is in Admin group
    is_admin = request.user.groups.filter(name='SP_admin').exists() or request.user.is_superuser

    context = {
        'service_requests': service_requests,
        'filter': filter_type,
        'filter_options': filter_options,
        'assigned_users': assigned_users,
        'assigned_user_id': assigned_user_id,
        'stations': all_stations,
        'allowed_stations': allowed_stations,
        'selected_station': station_filter,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'is_admin': is_admin,
    }
    return render(request, 'read/requests_to_me.html', context)


# ============================================================================
# SERVICE REQUEST DETAILS
# ============================================================================

def request_detail_sm(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_request_logs = ServiceRequestLog.objects.filter(service_request=service_request)
    reports = Report.objects.filter(service_request=service_request)
    completion_reports = CompletionReport.objects.filter(service_request=service_request)
    
    # Get next and previous stations
    next_station = service_request.get_next_station()
    previous_station = service_request.get_previous_station()
    
    # Get all stations in pipeline for jump capability
    pipeline_stations = service_request.pipeline.get_ordered_stations() if service_request.pipeline else []
    
    context = {
        'service_request': service_request,
        'service_request_logs': service_request_logs,
        'reports': reports,
        'completion_reports': completion_reports,
        'next_station': next_station,
        'previous_station': previous_station,
        'pipeline_stations': pipeline_stations,
        'progress': service_request.get_pipeline_progress(),
    }
    return render(request, 'read/request_detail_sm.html', context)


def request_detail(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_request_logs = ServiceRequestLog.objects.filter(service_request=service_request)
    reports = Report.objects.filter(service_request=service_request)
    completion_reports = CompletionReport.objects.filter(service_request=service_request)
    
    # Get next and previous stations (only if pipeline exists)
    next_station = service_request.get_next_station() if service_request.pipeline else None
    previous_station = service_request.get_previous_station() if service_request.pipeline else None
    
    # Check if user can access next station
    can_move_next = True

    
    # Get all stations in pipeline for manual selection
    pipeline_stations = service_request.pipeline.get_ordered_stations() if service_request.pipeline else []
    
    # Filter stations user can access
    accessible_stations = [
        s for s in pipeline_stations 
        if can_user_access_station(request.user, s, service_request)
    ]
    
    # Get available pipelines for assignment
    available_pipelines = Pipeline.objects.filter(is_active=True)
    
    # Get current station permissions for creating orders/reports
    can_create_purchase = False
    can_create_inventory = False
    can_create_completion = False
    can_send_back = False
    can_edit_completion = False
    can_edit_purchase = False
    can_edit_inventory = False
    
    if service_request.pipeline and service_request.current_station:
        try:
            current_pipeline_station = PipelineStation.objects.get(
                pipeline=service_request.pipeline,
                station=service_request.current_station
            )
            can_create_purchase = current_pipeline_station.can_create_purchase_order
            can_create_inventory = current_pipeline_station.can_create_inventory_order
            can_create_completion = current_pipeline_station.can_create_completion_report
            can_send_back = current_pipeline_station.can_send_back
            can_edit_completion = current_pipeline_station.can_edit_completion_report
            can_edit_purchase = current_pipeline_station.can_edit_purchase_order
            can_edit_inventory = current_pipeline_station.can_edit_inventory_order
        except PipelineStation.DoesNotExist:
            pass
    
    context = {
        'service_request': service_request,
        'service_request_logs': service_request_logs,
        'reports': reports,
        'completion_reports': completion_reports,
        'next_station': next_station,
        'previous_station': previous_station,
        'pipeline_stations': pipeline_stations,
        'accessible_stations': accessible_stations,
        'can_move_next': can_move_next,
        'progress': service_request.get_pipeline_progress() if service_request.pipeline else 0,
        'is_completed': service_request.is_completed() if service_request.pipeline else False,
        'available_pipelines': available_pipelines,
        # Station permissions
        'can_create_purchase_order': can_create_purchase,
        'can_create_inventory_order': can_create_inventory,
        'can_create_completion_report': can_create_completion,
        'can_send_back': can_send_back,
        'can_edit_completion_report': can_edit_completion,
        'can_edit_purchase_order': can_edit_purchase,
        'can_edit_inventory_order': can_edit_inventory,
    }
    return render(request, 'read/request_detail.html', context)


def assign_to_user(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = User.objects.get(id=user_id)
        service_request.assigned_to = user
        service_request.save()
        
        # Log the assignment
        ServiceRequestLog.objects.create(
            service_request=service_request,
            log_type='assignment',
            comment=f'تم تعيين الطلب الى المستخدم {user.username}',
            created_by=request.user
        )
        
        user_profile = UserProfile.objects.filter(user=user).first()
        if user_profile:
            link_to_order = f"بمكنك الدخول عبر الرابط التالي: https://net.sportainmentclub.com/request_detail/{id}"
            send_message(user_profile.phone, f'تم تعيين الطلب اليك: {service_request.title}\n{link_to_order}')
        
        messages.success(request, f'تم تعيين الطلب الى المستخدم {user.username}')
        return redirect('request_detail', id=id)
    
    users = User.objects.all()
    context = {
        'service_request': service_request,
        'users': users
    }
    return render(request, 'write/assign_to_user.html', context)


def print_request(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_request_logs = ServiceRequestLog.objects.filter(service_request=service_request)
    reports = Report.objects.filter(service_request=service_request)
    completion_report = CompletionReport.objects.filter(service_request=service_request).first()
    
    context = {
        'service_request': service_request,
        'service_request_logs': service_request_logs,
        'reports': reports,
        'completion_report': completion_report
    }
    return render(request, 'read/print_request.html', context)


# ============================================================================
# STATION TRANSITIONS
# ============================================================================

def move_to_next_station_view(request, id):
    """Move service request to next station in pipeline"""
    service_request = ServiceRequest.objects.get(id=id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        
        success, message = service_request.move_to_next_station(
            user=request.user,
            comment=comment
        )
        
        if success:
            messages.success(request, message)
            
            # Send notifications if moving to final station
            if service_request.is_completed():
                user_to_alert_phone = service_request.created_by.profile.phone
                msg = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                send_message(user_to_alert_phone, msg)
        else:
            messages.error(request, message)
        
        return redirect('request_detail', id=id)
    
    context = {
        'service_request': service_request,
        'next_station': service_request.get_next_station(),
    }
    return render(request, 'write/move_to_next_station.html', context)


def move_to_station_view(request, id, station_id):
    """Move service request to a specific station"""
    service_request = ServiceRequest.objects.get(id=id)
    station = Station.objects.get(id=station_id)
    
    # Check if user can access this station
    if not can_user_access_station(request.user, station):
        messages.error(request, 'ليس لديك صلاحية للانتقال إلى هذه المحطة')
        return redirect('request_detail', id=id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        
        success, message = service_request.move_to_station(
            station=station,
            user=request.user,
            comment=comment
        )
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('request_detail', id=id)
    
    context = {
        'service_request': service_request,
        'target_station': station,
    }
    return render(request, 'write/move_to_station.html', context)


def send_back_to_previous(request, id):
    """Send service request back to previous station"""
    service_request = ServiceRequest.objects.get(id=id)
    previous_station = service_request.get_previous_station()
    
    if not previous_station:
        messages.error(request, 'لا توجد محطة سابقة للعودة إليها')
        return redirect('request_detail', id=id)
    
    # Check if current station allows sending back
    can_send_back = False
    if service_request.pipeline and service_request.current_station:
        try:
            current_pipeline_station = PipelineStation.objects.get(
                pipeline=service_request.pipeline,
                station=service_request.current_station
            )
            can_send_back = current_pipeline_station.can_send_back
        except PipelineStation.DoesNotExist:
            pass
    
    if not can_send_back:
        messages.error(request, 'هذه المحطة لا تسمح بإرجاع الطلبات')
        return redirect('request_detail', id=id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        success, message = service_request.move_to_station(
            station=previous_station,
            user=request.user,
            comment=f'تم إرجاع الطلب للمحطة السابقة - السبب: {reason}'
        )
        
        if success:
            messages.success(request, f'تم إرجاع الطلب إلى {previous_station.name_ar}')
        else:
            messages.error(request, message)
        
        return redirect('request_detail', id=id)
    
    context = {
        'service_request': service_request,
        'previous_station': previous_station,
    }
    return render(request, 'write/send_back.html', context)


# ============================================================================
# PIPELINE ASSIGNMENT
# ============================================================================

def assign_pipeline(request, id):
    """Assign a pipeline to a service request and optionally create an initial report"""
    service_request = ServiceRequest.objects.get(id=id)
    
    # Only allow if no pipeline assigned yet
    if service_request.pipeline:
        messages.warning(request, 'تم تعيين مسار عمل بالفعل لهذا الطلب')
        return redirect('request_detail', id=id)
    
    if request.method == 'POST':
        pipeline_id = request.POST.get('pipeline')
        
        if pipeline_id:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            initial_station = pipeline.get_initial_station()
            
            if not initial_station:
                messages.error(request, 'خطأ: المسار المحدد لا يحتوي على محطة ابتدائية')
                return redirect('request_detail', id=id)
            
            # Assign pipeline and initial station
            service_request.pipeline = pipeline
            service_request.current_station = initial_station
            service_request.save()
            
            # Log the assignment
            ServiceRequestLog.objects.create(
                service_request=service_request,
                to_station=initial_station,
                log_type='station_change',
                comment=f'تم تعيين مسار العمل: {pipeline.name_ar} وبدء المحطة: {initial_station.name_ar}',
                created_by=request.user
            )
            
            # Report creation is now MANDATORY
            report_title = request.POST.get('report_title', '').strip()
            report_description = request.POST.get('report_description', '').strip()
            
            if not report_title or not report_description:
                messages.error(request, 'الرجاء إدخال عنوان وتفاصيل التقرير')
                return redirect('request_detail', id=id)
            
            # Create the mandatory report
            report = Report.objects.create(
                service_request=service_request,
                title=report_title,
                description=report_description,
                needs_outsourcing=False,
                needs_items=False,
                created_by=request.user
            )
            
            # Log report creation
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment=f'تم إنشاء تقرير مبدئي: {report_title}',
                created_by=request.user
            )
            
            messages.success(request, f'تم تعيين مسار العمل و إنشاء التقرير بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'الرجاء اختيار مسار عمل')
            return redirect('request_detail', id=id)
    
    # GET request - redirect to request_detail (modal handles the UI)
    return redirect('request_detail', id=id)


# ============================================================================
# CREATE SERVICE REQUEST
# ============================================================================

def create_service_request(request):
    sections = Section.objects.filter(manager=request.user)
    service_providers = ServiceProvider.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        section_id = request.POST.get('section')
        service_provider_id = request.POST.get('service_provider')

        if title and description and section_id and service_provider_id:
            # Check if the request already exists
            existing_request = ServiceRequest.objects.filter(
                title=title,
                description=description,
                section_id=section_id,
                service_provider_id=service_provider_id,
                created_by=request.user
            ).exists()

            if existing_request:
                messages.warning(request, 'هذا الطلب موجود بالفعل')
                return redirect('create_service_request')

            # Create new request WITHOUT pipeline (will be assigned later)
            service_request = ServiceRequest.objects.create(
                title=title,
                description=description,
                section_id=section_id,
                service_provider_id=service_provider_id,
                pipeline=None,  # No pipeline yet
                current_station=None,  # No station yet
                created_by=request.user,
                updated_by=request.user
            )
            
            service_provider = service_request.service_provider

            message = f'*نظام صيانة النادي الترفيهي الرياضي*\nلديك طلب صيانة: {service_request.section.name}\nعنوان الطلب كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'

            for user in service_provider.manager.all():
                user_profile = user.profile
                if user_profile:
                    send_message(user_profile.phone, message)
            
            # Log creation
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment='تم إنشاء طلب جديد - في انتظار تحديد مسار العمل',
                created_by=request.user
            )

            messages.success(request, 'تم إنشاء الطلب بنجاح. يرجى تحديد مسار العمل.')
            return redirect('request_detail_sm', id=service_request.id)
        else:
            messages.error(request, 'الرجاء ملء جميع الحقول')
            return redirect('create_service_request')

    context = {
        'sections': sections,
        'service_providers': service_providers,
    }
    return render(request, 'write/create_service_request.html', context)


# ============================================================================
# REPORT CREATION
# ============================================================================

def create_report(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        reports = Report.objects.filter(service_request=service_request)
        
        if not reports:
            report_title = request.POST.get('report_title')
            report_description = request.POST.get('report_description')
            purchase_request_refrence = request.POST.get('purchase_request_refrence')
            inventory_order_refrence = request.POST.get('inventory_order_refrence')
            
            if report_title and report_description:
                report = Report.objects.create(
                    service_request=service_request,
                    title=report_title,
                    description=report_description,
                    created_by=request.user
                )
                
                # Log report creation
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء تقرير جديد',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء تقرير بنجاح')

            if purchase_request_refrence:
                PurchaseOrder.objects.create(
                    report=report,
                    refrence_number=purchase_request_refrence,
                    created_by=request.user
                )
                report.needs_outsourcing = True
                report.save()
                
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء طلب شراء',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب شراء بنجاح')

            if inventory_order_refrence:
                InventoryOrder.objects.create(
                    report=report,
                    refrence_number=inventory_order_refrence,
                    created_by=request.user
                )
                report.needs_items = True
                report.save()
                
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء طلب مخزني',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            
            # Move to "In Progress" station if exists
            in_progress = get_station_by_name('In Progress')
            if in_progress and service_request.current_station != in_progress:
                service_request.move_to_station(
                    station=in_progress,
                    user=request.user,
                    comment='تم إنشاء التقرير - بدء العمل'
                )
            
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'تم إنشاء تقرير بالفعل')
            return redirect('request_detail', id=id)


def create_completion_report(request, id):
    if request.method == 'POST':
        logger.info(f'Creating completion report for service request {id} by user {request.user}')
        service_request = ServiceRequest.objects.get(id=id)
        report_details = request.POST.get('report_details')
        reports = Report.objects.filter(service_request=service_request)
        
        logger.info(f'Service request current station: {service_request.current_station}')
        logger.info(f'Pipeline: {service_request.pipeline}')
        
        if not reports:
            logger.info('No existing report found, creating new report')
            report = Report.objects.create(
                service_request=service_request,
                title='تقرير إنجاز',
                created_by=request.user
            )    
        else:
            logger.info(f'Found {reports.count()} existing reports')
        
        completion_report = CompletionReport.objects.create(
            service_request=service_request,
            title='تقرير إنجاز',
            description=report_details,
            created_by=request.user
        )
        logger.info(f'Completion report created with ID: {completion_report.id}')
        
        # Log completion report
        ServiceRequestLog.objects.create(
            service_request=service_request,
            log_type='update',
            comment='تم إنشاء تقرير إنجاز',
            created_by=request.user
        )
        
        # Automatically move to next station
        next_station = service_request.get_next_station()
        logger.info(f'Next station: {next_station}')
        
        if next_station:
            logger.info(f'Attempting to move to next station: {next_station.name}')
            success, msg = service_request.move_to_next_station(
                user=request.user,
                comment='تم إنشاء تقرير الإنجاز - الانتقال للمحطة التالية'
            )
            logger.info(f'Move to next station result - Success: {success}, Message: {msg}')
            
            if success:
                logger.info(f'Successfully moved to {service_request.current_station.name}')
                # Send notification if moved to final station
                if service_request.is_completed():
                    logger.info('Service request is now completed, sending notification')
                    user_to_alert_phone = service_request.created_by.profile.phone
                    message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                    send_message(user_to_alert_phone, message)
                    logger.info(f'Notification sent to {user_to_alert_phone}')
            else:
                logger.warning(f'Failed to move to next station: {msg}')
        else:
            logger.warning('No next station available in pipeline')
        
        messages.success(request, 'تم إنشاء تقرير إنجاز بنجاح والانتقال للمحطة التالية')
        logger.info(f'Completion report workflow completed for request {id}')
        return redirect('request_detail', id=id)


def create_purchase_order(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report = Report.objects.filter(service_request=service_request).first()
        purchase_request_refrence = request.POST.get('purchase_request_refrence')
        
        if report:
            PurchaseOrder.objects.create(
                report=report,
                refrence_number=purchase_request_refrence,
                created_by=request.user
            )
            report.needs_outsourcing = True
            report.save()
            
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment='تم إنشاء طلب شراء',
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء طلب شراء بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'التقرير غير موجود')
            return redirect('request_detail', id=id)


def create_inventory_order(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report = Report.objects.filter(service_request=service_request).first()
        inventory_order_refrence = request.POST.get('inventory_order_refrence')
        
        if report:
            InventoryOrder.objects.create(
                report=report,
                refrence_number=inventory_order_refrence,
                created_by=request.user
            )
            report.needs_items = True
            report.save()
            
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment='تم إنشاء طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'التقرير غير موجود')
            return redirect('request_detail', id=id)


# ============================================================================
# EDIT REPORTS & ORDERS
# ============================================================================

def edit_completion_report(request, id):
    completion_report = CompletionReport.objects.get(id=id) 
    form = CompletionReportForm(instance=completion_report)
    
    if request.method == 'POST':
        form = CompletionReportForm(request.POST, instance=completion_report)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=completion_report.service_request,
                log_type='update',
                comment='تم تعديل تقرير إنجاز',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل تقرير إنجاز بنجاح')
            return redirect('request_detail', id=completion_report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_completion_report.html', context)


def purchase_order_mark_as_approved(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى جاهز للشراء',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى جاهز للشراء')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_pending(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى قيد الاعتماد',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى قيد الاعتماد')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_used(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'used'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى تم الاستخدام')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def inventory_order_mark_as_approved(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'used'
    inventory_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب مخزني الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى تم الاستخدام')
    return redirect('request_detail', id=inventory_order.report.service_request.id)


def inventory_order_mark_as_pending(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'pending'
    inventory_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب مخزني الى قيد العمل',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى قيد العمل')
    return redirect('request_detail', id=inventory_order.report.service_request.id)


def edit_purchase_order(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    form = PurchaseOrderForm(instance=purchase_order)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=purchase_order.report.service_request,
                log_type='update',
                comment='تم تعديل طلب الشراء',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب الشراء بنجاح')
            return redirect('request_detail', id=purchase_order.report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_purchase_order.html', context)


def edit_inventory_order(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    form = InventoryOrderForm(instance=inventory_order)
    
    if request.method == 'POST':
        form = InventoryOrderForm(request.POST, instance=inventory_order)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=inventory_order.report.service_request,
                log_type='update',
                comment='تم تعديل طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب مخزني بنجاح')
            return redirect('request_detail', id=inventory_order.report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_inventory_order.html', context)


# ============================================================================
# LEGACY STATUS TRANSITION VIEWS (Now using stations)
# ============================================================================

def mark_as_under_review(request, id):
    """Legacy view - now moves to 'Under Review' station"""
    service_request = ServiceRequest.objects.get(id=id)
    report = Report.objects.filter(service_request=service_request).first()
    completion_report = CompletionReport.objects.filter(service_request=service_request).first()

    if report and completion_report:
        under_review = get_station_by_name('Under Review')
        
        if under_review:
            success, message = service_request.move_to_station(
                station=under_review,
                user=request.user,
                comment='تم نقل الطلب للمراجعة'
            )
            
            if success:
                # Send notification
                user_to_alert_phone = service_request.created_by.profile.phone
                msg = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                send_message(user_to_alert_phone, msg)
                
                # Mark purchase and inventory orders as used
                purchase_order = PurchaseOrder.objects.filter(report=report).first()
                inventory_order = InventoryOrder.objects.filter(report=report).first()
                if purchase_order:
                    purchase_order.status = 'used'
                    purchase_order.save()
                if inventory_order:
                    inventory_order.status = 'used'
                    inventory_order.save()
                
                messages.success(request, 'تم تعديل حالة الطلب الى قيد المراجعة')
            else:
                messages.error(request, message)
        else:
            messages.error(request, 'محطة "قيد المراجعة" غير موجودة')
    else:
        messages.error(request, 'حالة الطلب لا تسمح بالمراجعة')
    
    return redirect('request_detail', id=id)


def mark_as_in_progress(request, id):
    """Legacy view - now moves back to 'In Progress' station"""
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    
    if request.method == 'POST':
        form = ServiceRequestLogForm(request.POST)
        if form.is_valid():
            comment = 'تم اعادة حالة الطلب الى قيد العمل: ' + form.cleaned_data['comment']
            
            in_progress = get_station_by_name('In Progress')
            if in_progress:
                success, msg = service_request.move_to_station(
                    station=in_progress,
                    user=request.user,
                    comment=comment
                )
                
                if success:
                    # Send notification to service provider
                    message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اعادة الطلب الي حيث وان هناك مشكلة\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}\nتفاصيل المشكلة: {comment}'
                    
                    for user in service_provider.manager.all():
                        user_profile = user.profile
                        if user_profile:
                            send_message(user_profile.phone, message)
                    
                    messages.success(request, 'تم اعادة حالة الطلب الى قيد العمل')
                else:
                    messages.error(request, msg)
            else:
                messages.error(request, 'محطة "قيد العمل" غير موجودة')
                
            return redirect('request_detail', id=id)
    
    context = {'form': ServiceRequestLogForm()}
    return render(request, 'write/mark_as_in_progress.html', context)


def mark_as_complete(request, id):
    """Legacy view - now moves to final/completed station"""
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    
    # Try to move to the final station
    completed = get_station_by_name('Completed')
    if completed:
        success, msg = service_request.move_to_station(
            station=completed,
            user=request.user,
            comment='تم اكمال الطلب'
        )
        
        if success:
            # Send notification
            message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم استلام العمل من قبل قسم: {service_request.section.name}\nعنوان الطلب كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
            
            for user in service_provider.manager.all():
                user_profile = user.profile
                if user_profile:
                    send_message(user_profile.phone, message)
            
            messages.success(request, 'تم اكمال الطلب')
        else:
            messages.error(request, msg)
    else:
        messages.error(request, 'محطة "مكتمل" غير موجودة')
    
    return redirect(request.GET.get('next', 'home'))


# ============================================================================
# PURCHASE ORDERS
# ============================================================================

def purchase_order_list(request):
    orders = PurchaseOrder.objects.filter(
        status__in=['approved', 'supplied']
    ).order_by('-created_at')
    return render(request, 'read/purchase_orders.html', {'orders': orders})


def purchase_order_list_api(request):
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    orders = PurchaseOrder.objects.all()
    
    if status:
        orders = orders.filter(status__in=status.split(','))
    if search:
        orders = orders.filter(refrence_number__icontains=search)
    
    orders_data = []
    for order in orders:
        if order.status == 'pending':
            badge_class = "bg-warning"
        elif order.status == 'approved':
            badge_class = "bg-info"
        elif order.status == 'supplied':
            badge_class = "bg-success"
        elif order.status == 'used':
            badge_class = "bg-secondary"
        else:
            badge_class = "bg-dark"
            
        orders_data.append({
            'id': order.id,
            'refrence_number': order.refrence_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'badge_class': badge_class,
            'created_at': date_format(order.created_at, "Y-m-d H:i"),
            'service_request_id': order.report.service_request.id,
        })
    
    return JsonResponse({'orders': orders_data})


@require_POST
def update_order_status(request):
    order_id = request.POST.get('id')
    new_status = request.POST.get('status')
    order = get_object_or_404(PurchaseOrder, id=order_id)
    order.status = new_status
    order.save()

    if new_status == 'supplied':
        badge_class = "bg-success"
        service_providers = order.report.service_request.service_provider.manager.all()
        for service_provider in service_providers:
            user_profile = service_provider.profile
            if user_profile:
                message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم توريد الطلب الخاص بك\nعنوان الطلب كان: {order.report.service_request.title}\nتفاصيل الطلب: {order.report.service_request.description}'
                send_message(user_profile.phone, message)
    elif new_status == 'approved':
        badge_class = "bg-warning"
    elif new_status == 'used':
        badge_class = "bg-secondary"
    else:
        badge_class = "bg-dark"

    return JsonResponse({
        'status': new_status,
        'status_display': order.get_status_display(),
        'badge_class': badge_class,
    })

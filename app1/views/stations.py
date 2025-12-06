from collections import defaultdict
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.auth.models import User
from app1.models import PipelineStation, Station, ServiceRequest, ServiceProvider
from .helpers import get_station_by_name

logger = logging.getLogger(__name__)

def my_stations(request):
    """Show stations the user has access to"""
    
    # Superusers see ALL stations with ALL requests
    if request.user.is_superuser:
        # Get all pipeline-stations
        all_pipeline_stations = PipelineStation.objects.all().select_related('station', 'pipeline').distinct()
        
        # Group by station and calculate counts (all requests, no filtering)
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

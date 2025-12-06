import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from app1.models import ServiceRequest, Station, Section
from .helpers import get_station_by_name

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
    pipeline_stats = ServiceRequest.objects.filter(
        pipeline__isnull=False
    ).values('pipeline__name_ar').annotate(count=Count('id')).order_by('-count')
    
    pipeline_labels = [p['pipeline__name_ar'] for p in pipeline_stats]
    pipeline_data = [p['count'] for p in pipeline_stats]
    
    # Requests over time (last 30 days)
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

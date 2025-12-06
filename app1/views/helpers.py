from django.db.models import Q
from app1.models import PipelineStation, Station

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

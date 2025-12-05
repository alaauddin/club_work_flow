from django.db import models
from django.contrib.auth.models import User
from .section import Section
from .service_provider import ServiceProvider
from .pipeline import Pipeline
from .station import Station
from .pipeline_station import PipelineStation


class ServiceRequest(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    
    # Dynamic workflow fields
    pipeline = models.ForeignKey(Pipeline, on_delete=models.PROTECT, null=True, blank=True, help_text='Workflow pipeline for this request')
    current_station = models.ForeignKey(Station, on_delete=models.PROTECT, null=True, blank=True, help_text='Current station in the workflow')
    station_entered_at = models.DateTimeField(auto_now_add=True, help_text='When the request entered the current station')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_by')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_to', null=True, blank=True)

    def __str__(self):
        return self.title

    def get_next_station(self):
        """Returns the next station in the pipeline, or None if at the end"""
        if not self.pipeline or not self.current_station:
            return None
            
        try:
            current_ps = PipelineStation.objects.get(
                pipeline=self.pipeline,
                station=self.current_station
            )
            next_ps = PipelineStation.objects.filter(
                pipeline=self.pipeline,
                order__gt=current_ps.order
            ).order_by('order').first()
            
            return next_ps.station if next_ps else None
        except PipelineStation.DoesNotExist:
            return None

    def get_previous_station(self):
        """Returns the previous station in the pipeline, or None if at  the start"""
        if not self.pipeline or not self.current_station:
            return None
            
        try:
            current_ps = PipelineStation.objects.get(
                pipeline=self.pipeline,
                station=self.current_station
            )
            previous_ps = PipelineStation.objects.filter(
                pipeline=self.pipeline,
                order__lt=current_ps.order
            ).order_by('-order').first()
            
            return previous_ps.station if previous_ps else None
        except PipelineStation.DoesNotExist:
            return None

    def can_move_to_next(self, user=None):
        """Validates if the request can move to the next station"""
        next_station = self.get_next_station()
        if not next_station:
            return False
        
        # Check if a specific role is required for the current station
        if user:
            try:
                current_ps = PipelineStation.objects.get(
                    pipeline=self.pipeline,
                    station=self.current_station
                )
                if current_ps.required_role and not user.groups.filter(id=current_ps.required_role.id).exists():
                    return False
            except PipelineStation.DoesNotExist:
                return False
        
        return True

    def move_to_next_station(self, user, comment=''):
        """Transitions the request to the next station and creates a log entry"""
        from django.utils import timezone
        from .service_request_log import ServiceRequestLog
        
        next_station = self.get_next_station()
        if not next_station:
            return False, "Already at the final station"
        
        if not self.can_move_to_next(user):
            return False, "Not authorized to move to next station"
        
        old_station = self.current_station
        self.current_station = next_station
        self.station_entered_at = timezone.now()
        self.updated_by = user
        self.save()
        
        # Create log entry
        ServiceRequestLog.objects.create(
            service_request=self,
            from_station=old_station,
            to_station=next_station,
            log_type='station_change',
            comment=comment or f'Moved from {old_station.name} to {next_station.name}',
            created_by=user
        )
        
        return True, f"Successfully moved to {next_station.name}"

    def move_to_station(self, station, user, comment=''):
        """Moves the request to a specific station (with validation)"""
        from django.utils import timezone
        from .service_request_log import ServiceRequestLog
        
        # Validate that the station is part of this pipeline
        if not PipelineStation.objects.filter(pipeline=self.pipeline, station=station).exists():
            return False, "Station is not part of this pipeline"
        
        if station == self.current_station:
            return False, "Already at this station"
        
        old_station = self.current_station
        self.current_station = station
        self.station_entered_at = timezone.now()
        self.updated_by = user
        self.save()
        
        # Create log entry
        ServiceRequestLog.objects.create(
            service_request=self,
            from_station=old_station,
            to_station=station,
            log_type='station_change',
            comment=comment or f'Moved from {old_station.name if old_station else "None"} to {station.name}',
            created_by=user
        )
        
        return True, f"Successfully moved to {station.name}"

    def get_pipeline_progress(self):
        """Returns the completion percentage based on current station position"""
        if not self.pipeline or not self.current_station:
            return 0
            
        try:
            total_stations = PipelineStation.objects.filter(pipeline=self.pipeline).count()
            if total_stations == 0:
                return 0
            
            current_ps = PipelineStation.objects.get(
                pipeline=self.pipeline,
                station=self.current_station
            )
            
            return int((current_ps.order / total_stations) * 100)
        except (PipelineStation.DoesNotExist, ZeroDivisionError):
            return 0

    def is_completed(self):
        """Checks if the request is in a final station"""
        if not self.current_station:
            return False
        return self.current_station.is_final

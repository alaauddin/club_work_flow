from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Section(models.Model):
    name = models.CharField(max_length=100)
    manager = models.ManyToManyField(User)

    def __str__(self):
        return self.name
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=100)
    image = models.ImageField(upload_to='profile_images', null=True, blank=True)

    def __str__(self):
        return self.user.username
    

class ServiceProvider(models.Model):
    name = models.CharField(max_length=100)
    manager = models.ManyToManyField(User)

    def __str__(self):
        return self.name
    


class Station(models.Model):
    """Represents a workflow stage/station"""
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    description = models.TextField(blank=True, null=True)
    is_initial = models.BooleanField(default=False, help_text='Is this a starting station?')
    is_final = models.BooleanField(default=False, help_text='Is this a completion station?')
    color = models.CharField(max_length=7, blank=True, null=True, help_text='Hex color code (e.g., #FF5733)')
    order = models.IntegerField(default=0, help_text='Global display order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    allowed_users = models.ManyToManyField(User)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'

    def __str__(self):
        return f"{self.name} ({self.name_ar})"


class Pipeline(models.Model):
    """Defines a workflow template with ordered stations"""
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    description = models.TextField(blank=True, null=True)
    sections = models.ManyToManyField(Section, blank=True, help_text='Which sections can use this pipeline')
    is_active = models.BooleanField(default=True)
    stations = models.ManyToManyField(Station, through='PipelineStation', related_name='pipelines')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Pipeline'
        verbose_name_plural = 'Pipelines'

    def __str__(self):
        return f"{self.name} ({self.name_ar})"

    def get_ordered_stations(self):
        """Returns stations in order for this pipeline"""
        return self.stations.order_by('pipelinestation__order')

    def get_initial_station(self):
        """Returns the first station in this pipeline"""
        return self.get_ordered_stations().first()


class PipelineStation(models.Model):
    """Junction table defining station order within a pipeline"""
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    order = models.IntegerField(help_text='Order of this station in the pipeline')
    can_skip = models.BooleanField(default=False, help_text='Can this station be skipped?')
    required_role = models.ForeignKey(
        'auth.Group', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text='Required role to approve/move from this station'
    )

    class Meta:
        ordering = ['pipeline', 'order']
        unique_together = [['pipeline', 'station'], ['pipeline', 'order']]
        verbose_name = 'Pipeline Station'
        verbose_name_plural = 'Pipeline Stations'

    def __str__(self):
        return f"{self.pipeline.name} - {self.station.name} (Order: {self.order})"


class ServiceRequest(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    
    # Dynamic workflow fields
    pipeline = models.ForeignKey(Pipeline, on_delete=models.PROTECT, help_text='Workflow pipeline for this request')
    current_station = models.ForeignKey(Station, on_delete=models.PROTECT, help_text='Current station in the workflow')
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
        """Returns the previous station in the pipeline, or None if at the start"""
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
            comment=comment or f'Moved from {old_station.name} to {station.name}',
            created_by=user
        )
        
        return True, f"Successfully moved to {station.name}"

    def get_pipeline_progress(self):
        """Returns the completion percentage based on current station position"""
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
        return self.current_station.is_final if self.current_station else False


class ServiceRequestLog(models.Model):
    LOG_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('station_change', 'Station Change'),
        ('assignment', 'Assignment Change'),
        ('update', 'General Update'),
    ]
    
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='logs')
    from_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_from')
    to_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_to')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default='comment')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Service Request Log'
        verbose_name_plural = 'Service Request Logs'

    def __str__(self):
        if self.log_type == 'station_change' and self.from_station and self.to_station:
            return f"{self.service_request.title} - {self.from_station.name} → {self.to_station.name}"
        return self.service_request.title + ' - ' + self.comment[:50]
    


class Report(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    needs_outsourcing = models.BooleanField(default=False)
    needs_items = models.BooleanField(default=False)

    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title + ' - ' + self.service_request.title
    

class CompletionReport(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title + ' - ' + self.service_request.title
    


class PurchaseOrder(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='purchase_order')
    refrence_number = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=[('approved', 'جاهز للشراء'), ('supplied', 'تم التوريد'), ('used', 'تم الاستخدام')], default='approved')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.report.title 
    

class InventoryOrder(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='inventory_order')
    refrence_number = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=[('pending', 'قيد العمل'), ('used', 'تم الاستلام والاستخدام')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.report.title
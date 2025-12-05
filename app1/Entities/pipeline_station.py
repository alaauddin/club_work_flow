from django.db import models
from .pipeline import Pipeline
from .station import Station


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

from django.db import models
from .section import Section
from .station import Station


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

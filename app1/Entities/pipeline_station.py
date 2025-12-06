from django.db import models
from .pipeline import Pipeline
from .station import Station


class PipelineStation(models.Model):
    """Junction table defining station order within a pipeline"""
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    order = models.IntegerField(help_text='Order of this station in the pipeline')
    can_skip = models.BooleanField(default=False, help_text='Can this station be skipped?')

    # Permission controls for this station in this specific pipeline
    allowed_users = models.ManyToManyField(
        'auth.User',
        blank=True,
        help_text='Users allowed to work on this station in this pipeline. Empty means all users can access.'
    )

    # Action permissions
    can_create_purchase_order = models.BooleanField(default=False, help_text='Can this station create a purchase order?')
    can_create_inventory_order = models.BooleanField(default=False, help_text='Can this station create an inventory order?')
    can_create_completion_report = models.BooleanField(default=False, help_text='Can this station create a completion report?')
    can_send_back = models.BooleanField(default=False, help_text='Can this station send the request back to the previous station?')
    can_edit_completion_report = models.BooleanField(default=False, help_text='Can this station edit the completion report?')
    can_edit_purchase_order = models.BooleanField(default=False, help_text='Can this station edit the purchase order?')
    can_edit_inventory_order = models.BooleanField(default=False, help_text='Can this station edit the inventory order?')
    show_assigned_requests = models.BooleanField(default=False, help_text='Show assigned requests to this station?')
    show_the_managers_only = models.BooleanField(default=False, help_text='Show the managers only?')

    class Meta:
        ordering = ['pipeline', 'order']
        unique_together = [['pipeline', 'station'], ['pipeline', 'order']]
        verbose_name = 'Pipeline Station'
        verbose_name_plural = 'Pipeline Stations'

    def __str__(self):
        return f"{self.pipeline.name} - {self.station.name} (Order: {self.order})"

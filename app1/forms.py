



from django import forms
from app1.models import *


class CompletionReportForm(forms.ModelForm):
    class Meta:
        model = CompletionReport
        fields = ['description']


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['refrence_number']


class InventoryOrderForm(forms.ModelForm):
    class Meta:
        model = InventoryOrder
        fields = ['refrence_number']



class ServiceRequestLogForm(forms.ModelForm):
    class Meta:
        model = ServiceRequestLog
        fields = ['comment']



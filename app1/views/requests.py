from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from app1.models import (
    ServiceRequest, ServiceRequestLog, Report, CompletionReport, 
    Pipeline, PipelineStation, UserProfile, Section, ServiceProvider
)
from .notifications import send_message
from .helpers import can_user_access_station

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


def assign_pipeline(request, id):
    """Assign a pipeline to a service request and optionally create an initial report"""
    service_request = get_object_or_404(ServiceRequest, id=id)
    
    if request.method == 'POST':
        pipeline_id = request.POST.get('pipeline')
        print(f'pipeline_id: {pipeline_id}')
        if pipeline_id:
            try:
                pipeline = Pipeline.objects.get(id=pipeline_id)
                
                # Assign pipeline
                service_request.pipeline = pipeline
                
                # Set initial station
                initial_station = pipeline.get_initial_station()
                print(f'initial_station: {initial_station}')
                if initial_station:
                    service_request.current_station = initial_station
                
                service_request.save()
                
                # Create log entry
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='status_change',
                    comment=f'تم تعيين مسار العمل: {pipeline.name_ar}',
                    created_by=request.user
                )
                
                messages.success(request, f'تم تعيين مسار العمل {pipeline.name_ar} بنجاح')
                
            except Pipeline.DoesNotExist:
                messages.error(request, 'مسار العمل غير موجود')
        else:
            messages.error(request, 'الرجاء اختيار مسار عمل')
            
    return redirect('request_detail', id=id)


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

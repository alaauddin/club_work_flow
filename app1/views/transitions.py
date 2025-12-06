from django.shortcuts import render, redirect
from django.contrib import messages
from app1.models import ServiceRequest, Station, PipelineStation, Report, CompletionReport, PurchaseOrder, InventoryOrder
from app1.forms import ServiceRequestLogForm
from .helpers import can_user_access_station, get_station_by_name
from .notifications import send_message

def move_to_next_station_view(request, id):
    """Move service request to next station in pipeline"""
    service_request = ServiceRequest.objects.get(id=id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        
        success, message = service_request.move_to_next_station(
            user=request.user,
            comment=comment
        )
        
        if success:
            messages.success(request, message)
            
            # Send notifications if moving to final station
            if service_request.is_completed():
                user_to_alert_phone = service_request.created_by.profile.phone
                msg = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                send_message(user_to_alert_phone, msg)
        else:
            messages.error(request, message)
        
        return redirect('request_detail', id=id)
    
    context = {
        'service_request': service_request,
        'next_station': service_request.get_next_station(),
    }
    return render(request, 'write/move_to_next_station.html', context)


def move_to_station_view(request, id, station_id):
    """Move service request to a specific station"""
    service_request = ServiceRequest.objects.get(id=id)
    station = Station.objects.get(id=station_id)
    
    # Check if user can access this station
    if not can_user_access_station(request.user, station):
        messages.error(request, 'ليس لديك صلاحية للانتقال إلى هذه المحطة')
        return redirect('request_detail', id=id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        
        success, message = service_request.move_to_station(
            station=station,
            user=request.user,
            comment=comment
        )
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('request_detail', id=id)
    
    context = {
        'service_request': service_request,
        'target_station': station,
    }
    return render(request, 'write/move_to_station.html', context)


def send_back_to_previous(request, id):
    """Send service request back to previous station"""
    service_request = ServiceRequest.objects.get(id=id)
    previous_station = service_request.get_previous_station()
    
    if not previous_station:
        messages.error(request, 'لا توجد محطة سابقة للعودة إليها')
        return redirect('request_detail', id=id)
    
    # Check if current station allows sending back
    can_send_back = False
    if service_request.pipeline and service_request.current_station:
        try:
            current_pipeline_station = PipelineStation.objects.get(
                pipeline=service_request.pipeline,
                station=service_request.current_station
            )
            can_send_back = current_pipeline_station.can_send_back
        except PipelineStation.DoesNotExist:
            pass
            
    if not can_send_back:
        messages.error(request, 'هذه المحطة لا تسمح بإعادة الطلب للخلف')
        return redirect('request_detail', id=id)
        
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        
        success, message = service_request.move_to_station(
            station=previous_station,
            user=request.user,
            comment=f'تم إعادة الطلب للمحطة السابقة: {comment}'
        )
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('request_detail', id=id)
        
    context = {
        'service_request': service_request,
        'previous_station': previous_station
    }
    return render(request, 'write/send_back.html', context)


# ============================================================================
# LEGACY STATUS TRANSITION VIEWS (Now using stations)
# ============================================================================

def mark_as_under_review(request, id):
    """Legacy view - now moves to 'Under Review' station"""
    service_request = ServiceRequest.objects.get(id=id)
    report = Report.objects.filter(service_request=service_request).first()
    completion_report = CompletionReport.objects.filter(service_request=service_request).first()

    if report and completion_report:
        under_review = get_station_by_name('Under Review')
        
        if under_review:
            success, message = service_request.move_to_station(
                station=under_review,
                user=request.user,
                comment='تم نقل الطلب للمراجعة'
            )
            
            if success:
                # Send notification
                user_to_alert_phone = service_request.created_by.profile.phone
                msg = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                send_message(user_to_alert_phone, msg)
                
                # Mark purchase and inventory orders as used
                purchase_order = PurchaseOrder.objects.filter(report=report).first()
                inventory_order = InventoryOrder.objects.filter(report=report).first()
                if purchase_order:
                    purchase_order.status = 'used'
                    purchase_order.save()
                if inventory_order:
                    inventory_order.status = 'used'
                    inventory_order.save()
                
                messages.success(request, 'تم تعديل حالة الطلب الى قيد المراجعة')
            else:
                messages.error(request, message)
        else:
            messages.error(request, 'محطة "قيد المراجعة" غير موجودة')
    else:
        messages.error(request, 'حالة الطلب لا تسمح بالمراجعة')
    
    return redirect('request_detail', id=id)


def mark_as_in_progress(request, id):
    """Legacy view - now moves back to 'In Progress' station"""
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    
    if request.method == 'POST':
        form = ServiceRequestLogForm(request.POST)
        if form.is_valid():
            comment = 'تم اعادة حالة الطلب الى قيد العمل: ' + form.cleaned_data['comment']
            
            in_progress = get_station_by_name('In Progress')
            if in_progress:
                success, msg = service_request.move_to_station(
                    station=in_progress,
                    user=request.user,
                    comment=comment
                )
                
                if success:
                    # Send notification to service provider
                    message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اعادة الطلب الي حيث وان هناك مشكلة\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}\nتفاصيل المشكلة: {comment}'
                    
                    for user in service_provider.manager.all():
                        user_profile = user.profile
                        if user_profile:
                            send_message(user_profile.phone, message)
                    
                    messages.success(request, 'تم اعادة حالة الطلب الى قيد العمل')
                else:
                    messages.error(request, msg)
            else:
                messages.error(request, 'محطة "قيد العمل" غير موجودة')
                
            return redirect('request_detail', id=id)
    
    context = {'form': ServiceRequestLogForm()}
    return render(request, 'write/mark_as_in_progress.html', context)


def mark_as_complete(request, id):
    """Legacy view - now moves to final/completed station"""
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    
    # Try to move to the final station
    completed = get_station_by_name('Completed')
    if completed:
        success, msg = service_request.move_to_station(
            station=completed,
            user=request.user,
            comment='تم اكمال الطلب'
        )
        
        if success:
            # Send notification
            message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم استلام العمل من قبل قسم: {service_request.section.name}\nعنوان الطلب كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
            
            for user in service_provider.manager.all():
                user_profile = user.profile
                if user_profile:
                    send_message(user_profile.phone, message)
            
            messages.success(request, 'تم اكمال الطلب')
        else:
            messages.error(request, msg)
    else:
        messages.error(request, 'محطة "مكتمل" غير موجودة')
    
    return redirect(request.GET.get('next', 'home'))

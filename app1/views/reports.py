import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.dateformat import format as date_format
from app1.models import (
    ServiceRequest, ServiceRequestLog, Report, CompletionReport, 
    PurchaseOrder, InventoryOrder
)
from app1.forms import CompletionReportForm, PurchaseOrderForm, InventoryOrderForm
from .helpers import get_station_by_name
from .notifications import send_message

logger = logging.getLogger(__name__)

def create_report(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        reports = Report.objects.filter(service_request=service_request)
        
        if not reports:
            report_title = request.POST.get('report_title')
            report_description = request.POST.get('report_description')
            purchase_request_refrence = request.POST.get('purchase_request_refrence')
            inventory_order_refrence = request.POST.get('inventory_order_refrence')
            
            if report_title and report_description:
                report = Report.objects.create(
                    service_request=service_request,
                    title=report_title,
                    description=report_description,
                    created_by=request.user
                )
                
                # Log report creation
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء تقرير جديد',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء تقرير بنجاح')

            if purchase_request_refrence:
                PurchaseOrder.objects.create(
                    report=report,
                    refrence_number=purchase_request_refrence,
                    created_by=request.user
                )
                report.needs_outsourcing = True
                report.save()
                
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء طلب شراء',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب شراء بنجاح')

            if inventory_order_refrence:
                InventoryOrder.objects.create(
                    report=report,
                    refrence_number=inventory_order_refrence,
                    created_by=request.user
                )
                report.needs_items = True
                report.save()
                
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    log_type='update',
                    comment='تم إنشاء طلب مخزني',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            
            # Move to "In Progress" station if exists
            in_progress = get_station_by_name('In Progress')
            if in_progress and service_request.current_station != in_progress:
                service_request.move_to_station(
                    station=in_progress,
                    user=request.user,
                    comment='تم إنشاء التقرير - بدء العمل'
                )
            
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'تم إنشاء تقرير بالفعل')
            return redirect('request_detail', id=id)


def create_completion_report(request, id):
    if request.method == 'POST':
        logger.info(f'Creating completion report for service request {id} by user {request.user}')
        service_request = ServiceRequest.objects.get(id=id)
        report_details = request.POST.get('report_details')
        reports = Report.objects.filter(service_request=service_request)
        
        logger.info(f'Service request current station: {service_request.current_station}')
        logger.info(f'Pipeline: {service_request.pipeline}')
        
        if not reports:
            logger.info('No existing report found, creating new report')
            report = Report.objects.create(
                service_request=service_request,
                title='تقرير إنجاز',
                created_by=request.user
            )    
        else:
            logger.info(f'Found {reports.count()} existing reports')
        
        completion_report = CompletionReport.objects.create(
            service_request=service_request,
            title='تقرير إنجاز',
            description=report_details,
            created_by=request.user
        )
        logger.info(f'Completion report created with ID: {completion_report.id}')
        
        # Log completion report
        ServiceRequestLog.objects.create(
            service_request=service_request,
            log_type='update',
            comment='تم إنشاء تقرير إنجاز',
            created_by=request.user
        )
        
        # Automatically move to next station
        next_station = service_request.get_next_station()
        logger.info(f'Next station: {next_station}')
        
        if next_station:
            logger.info(f'Attempting to move to next station: {next_station.name}')
            success, msg = service_request.move_to_next_station(
                user=request.user,
                comment='تم إنشاء تقرير الإنجاز - الانتقال للمحطة التالية'
            )
            logger.info(f'Move to next station result - Success: {success}, Message: {msg}')
            
            if success:
                logger.info(f'Successfully moved to {service_request.current_station.name}')
                # Send notification if moved to final station
                if service_request.is_completed():
                    logger.info('Service request is now completed, sending notification')
                    user_to_alert_phone = service_request.created_by.profile.phone
                    message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم اكمال طلبك بنجاح\nعنوان طلبك كان: {service_request.title}\nتفاصيل الطلب: {service_request.description}'
                    send_message(user_to_alert_phone, message)
                    logger.info(f'Notification sent to {user_to_alert_phone}')
            else:
                logger.warning(f'Failed to move to next station: {msg}')
        else:
            logger.warning('No next station available in pipeline')
        
        messages.success(request, 'تم إنشاء تقرير إنجاز بنجاح والانتقال للمحطة التالية')
        logger.info(f'Completion report workflow completed for request {id}')
        return redirect('request_detail', id=id)


def create_purchase_order(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report = Report.objects.filter(service_request=service_request).first()
        purchase_request_refrence = request.POST.get('purchase_request_refrence')
        
        if report:
            PurchaseOrder.objects.create(
                report=report,
                refrence_number=purchase_request_refrence,
                created_by=request.user
            )
            report.needs_outsourcing = True
            report.save()
            
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment='تم إنشاء طلب شراء',
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء طلب شراء بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'التقرير غير موجود')
            return redirect('request_detail', id=id)


def create_inventory_order(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report = Report.objects.filter(service_request=service_request).first()
        inventory_order_refrence = request.POST.get('inventory_order_refrence')
        
        if report:
            InventoryOrder.objects.create(
                report=report,
                refrence_number=inventory_order_refrence,
                created_by=request.user
            )
            report.needs_items = True
            report.save()
            
            ServiceRequestLog.objects.create(
                service_request=service_request,
                log_type='update',
                comment='تم إنشاء طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'التقرير غير موجود')
            return redirect('request_detail', id=id)


def edit_completion_report(request, id):
    completion_report = CompletionReport.objects.get(id=id) 
    form = CompletionReportForm(instance=completion_report)
    
    if request.method == 'POST':
        form = CompletionReportForm(request.POST, instance=completion_report)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=completion_report.service_request,
                log_type='update',
                comment='تم تعديل تقرير إنجاز',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل تقرير إنجاز بنجاح')
            return redirect('request_detail', id=completion_report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_completion_report.html', context)


def purchase_order_mark_as_approved(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى جاهز للشراء',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى جاهز للشراء')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_pending(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى قيد الاعتماد',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى قيد الاعتماد')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_used(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'used'
    purchase_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب الشراء الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى تم الاستخدام')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def inventory_order_mark_as_approved(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'used'
    inventory_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب مخزني الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى تم الاستخدام')
    return redirect('request_detail', id=inventory_order.report.service_request.id)


def inventory_order_mark_as_pending(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'pending'
    inventory_order.save()
    
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        log_type='update',
        comment='تم تعديل حالة طلب مخزني الى قيد العمل',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى قيد العمل')
    return redirect('request_detail', id=inventory_order.report.service_request.id)


def edit_purchase_order(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    form = PurchaseOrderForm(instance=purchase_order)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=purchase_order.report.service_request,
                log_type='update',
                comment='تم تعديل طلب الشراء',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب الشراء بنجاح')
            return redirect('request_detail', id=purchase_order.report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_purchase_order.html', context)


def edit_inventory_order(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    form = InventoryOrderForm(instance=inventory_order)
    
    if request.method == 'POST':
        form = InventoryOrderForm(request.POST, instance=inventory_order)
        if form.is_valid():
            form.save()
            
            ServiceRequestLog.objects.create(
                service_request=inventory_order.report.service_request,
                log_type='update',
                comment='تم تعديل طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب مخزني بنجاح')
            return redirect('request_detail', id=inventory_order.report.service_request.id)
    
    context = {'form': form}
    return render(request, 'write/edit_inventory_order.html', context)


def purchase_order_list(request):
    orders = PurchaseOrder.objects.filter(
        status__in=['approved', 'supplied']
    ).order_by('-created_at')
    return render(request, 'read/purchase_orders.html', {'orders': orders})


def purchase_order_list_api(request):
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    orders = PurchaseOrder.objects.all()
    
    if status:
        orders = orders.filter(status__in=status.split(','))
    if search:
        orders = orders.filter(refrence_number__icontains=search)
    
    orders_data = []
    for order in orders:
        if order.status == 'pending':
            badge_class = "bg-warning"
        elif order.status == 'approved':
            badge_class = "bg-info"
        elif order.status == 'supplied':
            badge_class = "bg-success"
        elif order.status == 'used':
            badge_class = "bg-secondary"
        else:
            badge_class = "bg-dark"
            
        orders_data.append({
            'id': order.id,
            'refrence_number': order.refrence_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'badge_class': badge_class,
            'created_at': date_format(order.created_at, "Y-m-d H:i"),
            'service_request_id': order.report.service_request.id,
        })
    
    return JsonResponse({'orders': orders_data})


@require_POST
def update_order_status(request):
    order_id = request.POST.get('id')
    new_status = request.POST.get('status')
    order = get_object_or_404(PurchaseOrder, id=order_id)
    order.status = new_status
    order.save()

    if new_status == 'supplied':
        badge_class = "bg-success"
        service_providers = order.report.service_request.service_provider.manager.all()
        for service_provider in service_providers:
            user_profile = service_provider.profile
            if user_profile:
                message = f'*نظام صيانة النادي الترفيهي الرياضي*\nتم توريد الطلب الخاص بك\nعنوان الطلب كان: {order.report.service_request.title}\nتفاصيل الطلب: {order.report.service_request.description}'
                send_message(user_profile.phone, message)
    elif new_status == 'approved':
        badge_class = "bg-warning"
    elif new_status == 'used':
        badge_class = "bg-secondary"
    else:
        badge_class = "bg-dark"

    return JsonResponse({
        'status': new_status,
        'status_display': order.get_status_display(),
        'badge_class': badge_class,
    })

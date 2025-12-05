from django.shortcuts import redirect, render

from app1.forms import CompletionReportForm, InventoryOrderForm, PurchaseOrderForm, ServiceRequestLogForm
from .models import *
from django.contrib import messages


from django.db.models import Count

import json
from django.db.models import Count
import requests


import threading
import requests

def send_message(number, message):
    def send():
        data = {
            "User": "Altarfeehi",
            "Pass": "Altarfeehi@277",
            "Method": "Chat",
            "To": str(number),
            "Body": str(message)
        }
        try:
            response = requests.post(
                url="http://185.216.203.97:8070/AWE/Api/index.php",
                data=data,
                timeout=20  # Optional: prevent long hanging
            )
            print(response.json())
        except Exception as e:
            print(f"Message sending failed: {e}")
    
    threading.Thread(target=send).start()






def home(request):
    # Count Service Requests by status
    total_requests = ServiceRequest.objects.count()
    pending_requests = ServiceRequest.objects.filter(status='pending').count()
    in_progress_requests = ServiceRequest.objects.filter(status='in_progress').count()
    under_review_requests = ServiceRequest.objects.filter(status='under_review').count()
    completed_requests = ServiceRequest.objects.filter(status='completed').count()

    # Count Reports and related objects
    total_reports = Report.objects.count()
    total_completion_reports = CompletionReport.objects.count()
    total_purchase_orders = PurchaseOrder.objects.count()
    total_inventory_orders = InventoryOrder.objects.count()

    # --- New Code for Chart Data ---
    # Aggregate counts for each section and status
    section_status_data = ServiceRequest.objects.values('section__name', 'status').annotate(count=Count('id'))
    
    # Get all section names (you may sort them if needed)
    sections = list(Section.objects.values_list('name', flat=True))
    
    # Define the statuses you want to chart
    status_choices = ['pending', 'in_progress', 'under_review', 'completed']
    
    # Initialize a dictionary to hold counts for each status per section.
    chart_data = {status: [0] * len(sections) for status in status_choices}
    
    # Create a mapping for section name to its index in the list
    section_index = {name: i for i, name in enumerate(sections)}
    
    # Populate chart_data with the counts from the aggregation query.
    for entry in section_status_data:
        section_name = entry['section__name']
        status = entry['status']
        if section_name in section_index:
            idx = section_index[section_name]
            chart_data[status][idx] = entry['count']
    # --- End of New Code ---

    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'under_review_requests': under_review_requests,
        'completed_requests': completed_requests,
        'total_reports': total_reports,
        'total_completion_reports': total_completion_reports,
        'total_purchase_orders': total_purchase_orders,
        'total_inventory_orders': total_inventory_orders,
        # Encode data as JSON strings:
        'chart_sections': json.dumps(sections),
        'chart_data': json.dumps(chart_data),
        'status_choices': json.dumps(status_choices),
    }

    return render(request, 'read/home.html', context)





def my_request(request):
    section = Section.objects.filter(manager=request.user)
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'supplied':
        service_requests = ServiceRequest.objects.filter(
            section__in=section,
            reports__purchase_order__status='supplied'
        )
    elif filter_type == 'pending':
        service_requests = ServiceRequest.objects.filter(
            section__in=section,
            status='pending'
        )
    elif filter_type == 'in_progress':
        service_requests = ServiceRequest.objects.filter(
            section__in=section,
            status='in_progress'
        )
    elif filter_type == 'under_review':
        service_requests = ServiceRequest.objects.filter(
            section__in=section,
            status='under_review'
        )
    else:
        service_requests = ServiceRequest.objects.filter(section__in=section)
    
    service_requests = service_requests.order_by('-id')

    context = {
        'service_requests': service_requests,
        'filter': filter_type,  # pass the current filter to the template if needed for active styling
    }
    return render(request, 'read/my_request.html', context)

def requests_to_me(request):
    service_providers = ServiceProvider.objects.filter(manager=request.user)
    filter_type = request.GET.get('filter', 'all')
    assigned_user_id = request.GET.get('assigned_to', '').strip()

    if filter_type == 'supplied':
        service_requests = ServiceRequest.objects.filter(
            service_provider__in=service_providers,
            reports__purchase_order__status='supplied'
        )
    elif filter_type == 'pending':
        service_requests = ServiceRequest.objects.filter(
            service_provider__in=service_providers,
            status='pending'
        )
    elif filter_type == 'under_review':
        service_requests = ServiceRequest.objects.filter(
            service_provider__in=service_providers,
            status='under_review'
        )
    elif filter_type == 'assigned_to_me':
        service_requests = ServiceRequest.objects.filter(
            service_provider__in=service_providers,
            assigned_to=request.user
        )
    else:
        service_requests = ServiceRequest.objects.filter(service_provider__in=service_providers)

    if assigned_user_id == 'unassigned':
        service_requests = service_requests.filter(assigned_to__isnull=True)
    elif assigned_user_id:
        service_requests = service_requests.filter(assigned_to_id=assigned_user_id)
    
    service_requests = service_requests.order_by('-id')

    filter_options = [
        {'key': 'all', 'label': 'كل الطلبات', 'icon': 'list'},
        {'key': 'pending', 'label': 'طلبات في الانتظار', 'icon': 'hourglass-half'},
        {'key': 'under_review', 'label': 'طلبات قيد المراجعة', 'icon': 'eye'},
        {'key': 'supplied', 'label': 'طلبات مشتريات موردة', 'icon': 'check'},
        {'key': 'assigned_to_me', 'label': 'طلبات مسندة إليّ', 'icon': 'user-check'},
    ]

    assigned_users = User.objects.filter(
        assigned_to__service_provider__in=service_providers
    ).distinct().order_by('username')

    context = {
        'service_requests': service_requests,
        'filter': filter_type,  # pass the current filter to the template if needed for active styling
        'filter_options': filter_options,
        'assigned_users': assigned_users,
        'assigned_user_id': assigned_user_id,
    }
    return render(request, 'read/requests_to_me.html', context)



def request_detail_sm(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_request_logs = ServiceRequestLog.objects.filter(service_request=service_request)
    reports = Report.objects.filter(service_request=service_request)
    completion_reports = CompletionReport.objects.filter(service_request=service_request)
    context = {
        'service_request': service_request,
        'service_request_logs': service_request_logs,
        'reports': reports,
        'completion_reports': completion_reports
    }
    return render(request, 'read/request_detail_sm.html', context)

def request_detail(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_request_logs = ServiceRequestLog.objects.filter(service_request=service_request)
    reports = Report.objects.filter(service_request=service_request)
    completion_reports = CompletionReport.objects.filter(service_request=service_request)
    context = {
        'service_request': service_request,
        'service_request_logs': service_request_logs,
        'reports': reports,
        'completion_reports': completion_reports
    }
    return render(request, 'read/request_detail.html', context)



def assign_to_user(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = User.objects.get(id=user_id)
        service_request.assigned_to = user
        service_request.save()
        # log
        ServiceRequestLog.objects.create(
            service_request=service_request,
            comment=f'تم تعيين الطلب الى المستخدم {user.username}',
            created_by=request.user
        )
        user_profile = UserProfile.objects.filter(user=user).first()
        link_to_order  = f"بمكنك الدخول عبد الراب.التالي: https://net.sportainmentclub.com/request_detail/{id}"
        send_message(user_profile.phone, f'تم تعيين الطلب اليك :{service_request.title} \n {link_to_order}')
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
                # log
                ServiceRequestLog.objects.create(
                    service_request=service_request,
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
                # log
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    comment='تم إنشاء طلب شراء ',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب شراء بنجاح')

            if inventory_order_refrence:
                InventoryOrder.objects.create(
                    report=report,
                    refrence_number=inventory_order_refrence,
                    created_by=request.user

                )

                report.needs_outsourcing = True
                # log
                ServiceRequestLog.objects.create(
                    service_request=service_request,
                    comment='تم إنشاء طلب مخزني',
                    created_by=request.user
                )
                messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            
            service_request.status = 'in_progress'
            service_request.save()
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'تم إنشاء تقرير بالفعل')
            return redirect('request_detail', id=id)
    
    
def create_completion_report(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report_details = request.POST.get('report_details')
        mark_as_completed = request.POST.get('mark_as_completed')
        reports = Report.objects.filter(service_request=service_request)
        if not reports:
            report = Report.objects.create(
                service_request=service_request,
                title='تقرير إنجاز',
                created_by=request.user
            )    
            CompletionReport.objects.create(
                service_request=service_request,
                title='تقرير إنجاز',
                description=report_details,
                created_by=request.user
            )
            # log
            ServiceRequestLog.objects.create(
                service_request=service_request,
                comment='تم إنشاء تقرير إنجاز',
                created_by=request.user
            )
            user_to_alart_phone = service_request.created_by.profile.phone
            # message with request details
            message = f'*نظام صيانة النادي الترفيهي الرياضي* \nتم اكمال طلبك بنجاح \n عنوان طلبك كان: {service_request.title} \n تفاصيل الطلب: {service_request.description}'
            # send message
            send_message(user_to_alart_phone, message)
            service_request.status = 'under_review'
            service_request.save()
            messages.success(request, 'تم إنشاء تقرير إنجاز بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'تم إنشاء تقرير إنجاز بالفعل')
            return redirect('request_detail', id=id)


def create_report_out_source(request, id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        report_details = request.POST.get('report_details')
        reports = Report.objects.filter(service_request=service_request)
        if not reports:
            report = Report.objects.create(
                service_request=service_request,
                title='تقرير احتياج خدمة خارجية',
                created_by=request.user,
                description = report_details
            )    

            ServiceRequestLog.objects.create(
                service_request=service_request,
                comment='تم انشاء تقرير احتياج خدمة خارجية',
                created_by=request.user
            )
            service_request.status = 'in_progress'
            service_request.save()
            messages.success(request, 'تم إنشاء تقرير إنجاز بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'تم إنشاء تقرير إنجاز بالفعل')
            return redirect('request_detail', id=id)
        

def create_completion_report_out_source(request,id):
    if request.method == 'POST':
        service_request = ServiceRequest.objects.get(id=id)
        reports = Report.objects.filter(service_request=service_request)
        report_details = request.POST.get('report_details')
        if not reports:
            messages.error(request,"حصل خطاء ماء")
            return redirect('request_detail', id=id)
        
        CompletionReport.objects.create(
                service_request=service_request,
                title='تقرير إنجاز لعمل خارجي',
                description=report_details,
                created_by=request.user
            )
        # log
        ServiceRequestLog.objects.create(
            service_request=service_request,
            comment='تم إنشاء تقرير إنجاز',
            created_by=request.user
        )
        service_request.status = 'in_progress'
        service_request.save()
        messages.success(request, 'تم إنشاء تقرير إنجاز بنجاح')
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
            # log
            ServiceRequestLog.objects.create(
                service_request=service_request,
                comment='تم إنشاء طلب شراء ',
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
            report.needs_outsourcing = True
            # log
            ServiceRequestLog.objects.create(
                service_request=service_request,
                comment='تم إنشاء طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء طلب مخزني بنجاح')
            return redirect('request_detail', id=id)
        else:
            messages.error(request, 'التقرير غير موجود')
            return redirect('request_detail', id=id)
        





def edit_completion_report(request,id):
    completion_report = CompletionReport.objects.get(id=id) 
    form = CompletionReportForm(instance=completion_report)
    if request.method == 'POST':
        form = CompletionReportForm(request.POST, instance=completion_report)
        if form.is_valid():
            form.save()
            # log
            ServiceRequestLog.objects.create(
                service_request=completion_report.service_request,
                comment='تم تعديل تقرير إنجاز',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل تقرير إنجاز بنجاح')
            return redirect('request_detail', id=completion_report.service_request.id)
    context = {
        'form': form
    }
    return render(request, 'write/edit_completion_report.html', context)


def purchase_order_mark_as_approved(request, id):
    
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    # log
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        comment='تم تعديل حالة طلب الشراء الى جاهز للشراء',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى جاهز للشراء')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_pending(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'approved'
    purchase_order.save()
    # log
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        comment='تم تعديل حالة طلب الشراء الى قيد الاعتماد',
        created_by=request.user
    )

    messages.success(request, 'تم تعديل حالة طلب الشراء الى قيد الاعتماد')
    return redirect('request_detail', id=purchase_order.report.service_request.id)


def purchase_order_mark_as_used(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    purchase_order.status = 'used'
    purchase_order.save()
    # log
    ServiceRequestLog.objects.create(
        service_request=purchase_order.report.service_request,
        comment='تم تعديل حالة طلب الشراء الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب الشراء الى تم الاستخدام')
    return redirect('request_detail', id=purchase_order.report.service_request.id)




def inventory_order_mark_as_approved(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'used'
    inventory_order.save()
    # log
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        comment='تم تعديل حالة طلب مخزني الى تم الاستخدام',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى تم الاستخدام')
    return redirect('request_detail', id=inventory_order.report.service_request.id)


def inventory_order_mark_as_pending(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    inventory_order.status = 'pending'
    inventory_order.save()
    # log
    ServiceRequestLog.objects.create(
        service_request=inventory_order.report.service_request,
        comment='تم تعديل حالة طلب مخزني الى قيد العمل',
        created_by=request.user
    )
    messages.success(request, 'تم تعديل حالة طلب مخزني الى قيد العمل')
    return redirect('request_detail', id=inventory_order.report.service_request.id)\
    



def edit_purchase_order(request, id):
    purchase_order = PurchaseOrder.objects.get(id=id)
    form = PurchaseOrderForm(instance=purchase_order)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            # log
            ServiceRequestLog.objects.create(
                service_request=purchase_order.report.service_request,
                comment='تم تعديل طلب الشراء',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب الشراء بنجاح')
            return redirect('request_detail', id=purchase_order.report.service_request.id)
    context = {
        'form': form
    }
    return render(request, 'write/edit_purchase_order.html', context)



def edit_inventory_order(request, id):
    inventory_order = InventoryOrder.objects.get(id=id)
    form = InventoryOrderForm(instance=inventory_order)
    if request.method == 'POST':
        form = InventoryOrderForm(request.POST, instance=inventory_order)
        if form.is_valid():
            form.save()
            # log
            ServiceRequestLog.objects.create(
                service_request=inventory_order.report.service_request,
                comment='تم تعديل طلب مخزني',
                created_by=request.user
            )
            messages.success(request, 'تم تعديل طلب مخزني بنجاح')
            return redirect('request_detail', id=inventory_order.report.service_request.id)
    context = {
        'form': form
    }
    return render(request, 'write/edit_inventory_order.html', context)



def mark_as_under_review(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    user_to_alart_phone = service_request.created_by.profile.phone
    # message with request details
    message = f'*نظام صيانة النادي الترفيهي الرياضي* \nتم اكمال طلبك بنجاح \n عنوان طلبك كان: {service_request.title} \n تفاصيل الطلب: {service_request.description}'
    # send message
    report = Report.objects.filter(service_request=service_request).first()
    completion_report = CompletionReport.objects.filter(service_request=service_request).first()

    if service_request.status == 'in_progress' and report and completion_report:
        service_request.status = 'under_review'
        service_request.save()
        send_message(user_to_alart_phone, message)


        purchase_order = PurchaseOrder.objects.filter(report=report).first()
        inventory_order = InventoryOrder.objects.filter(report=report).first()
        if purchase_order:
            purchase_order.status = 'used'
            purchase_order.save()
        if inventory_order:
            inventory_order.status = 'used'
            inventory_order.save()
        # log
        ServiceRequestLog.objects.create(
            service_request=service_request,
            comment='تم تعديل حالة الطلب الى قيد المراجعة',
            created_by=request.user
        )
        messages.success(request, 'تم تعديل حالة الطلب الى قيد المراجعة')
        return redirect('request_detail', id=id)
    else:
        messages.error(request, 'حالة الطلب لا تسمح بالمراجعة')
        return redirect('request_detail', id=id)



def mark_as_in_progress(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    if request.method == 'POST':
        form = ServiceRequestLogForm(request.POST)
        if form.is_valid():
            form.instance.service_request = service_request
            form.instance.created_by = request.user
            form.instance.comment = 'تم اعادة حالة الطلب الى قيد العمل: ' + form.instance.comment
            service_request.status = 'in_progress'
            message = f'*نظام صيانة النادي الترفيهي الرياضي* \nتم اعادة الطلب الي حيث وانه هناك مشكلة \n عنوان طلبك كان: {service_request.title} \n تفاصيل الطلب: {service_request.description}\n تفاصيل المشكلة: {form.instance.comment}'

            for user in service_provider.manager.all():
                user_to_alart_phone = user.profile.phone
                # send message
                send_message(user_to_alart_phone, message)
                

            service_request.save()
            form.save()            
            messages.success(request, 'تم اعادة حالة الطلب الى قيد العمل')
            return redirect('request_detail', id=id)
    context = {
        'form': ServiceRequestLogForm()
    }
    return render(request, 'write/mark_as_in_progress.html', context)
    

def mark_as_complete(request, id):
    service_request = ServiceRequest.objects.get(id=id)
    service_provider = service_request.service_provider
    
    service_request.status = 'completed'
    service_request.save()
    message = f'*نظام صيانة النادي الترفيهي الرياضي* \nتم استلام العمل من قبل قسم : {service_request.section.name} \n عنوان الطلب كان: {service_request.title} \n تفاصيل الطلب: {service_request.description}'

    for user in service_provider.manager.all():
        user_to_alart_phone = user.profile.phone
        # send message
        send_message(user_to_alart_phone, message)
    # log
    ServiceRequestLog.objects.create(
        service_request=service_request,
        comment='تم اكمال الطلب',
        created_by=request.user
    )
    messages.success(request, 'تم اكمال الطلب')
    return redirect(request.GET.get('next', 'home'))



from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Section, ServiceProvider, ServiceRequest, ServiceRequestLog

def create_service_request(request):
    sections = Section.objects.filter(manager=request.user)
    service_providers = ServiceProvider.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title').strip()
        description = request.POST.get('description').strip()
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

            # Create new request
            service_request = ServiceRequest.objects.create(
                title=title,
                description=description,
                section_id=section_id,
                service_provider_id=service_provider_id,
                created_by=request.user,
                updated_by=request.user
            )
            service_provider = service_request.service_provider

            message = f'*نظام صيانة النادي الترفيهي الرياضي* \nلديك طلب صيانة: {service_request.section.name} \n عنوان الطلب كان: {service_request.title} \n تفاصيل الطلب: {service_request.description}'

            for user in service_provider.manager.all():
                user_to_alart_phone = user.profile.phone
                # send message
                send_message(user_to_alart_phone, message)
            # Log creation
            ServiceRequestLog.objects.create(
                service_request=service_request,
                comment='تم إنشاء طلب جديد',
                created_by=request.user
            )

            messages.success(request, 'تم إنشاء الطلب بنجاح')
            return redirect('request_detail_sm', id=service_request.id)
        else:
            messages.error(request, 'الرجاء ملء جميع الحقول')
            return redirect('create_service_request')

    context = {
        'sections': sections,
        'service_providers': service_providers
    }
    return render(request, 'write/create_service_request.html', context)





def purchase_order_list(request):
    orders = PurchaseOrder.objects.filter(status__in=['approved', 'supplied']).order_by('-created_at')
    return render(request, 'read/purchase_orders.html', {'orders': orders})


from django.http import JsonResponse
from django.core.serializers import serialize
from .models import PurchaseOrder
from django.utils.dateformat import format as date_format

def purchase_order_list_api(request):
    status = request.GET.get('status', '')
    
    search = request.GET.get('search', '')
    orders = PurchaseOrder.objects.all()
    if status:
        print(status)
        orders = orders.filter(status__in=status.split(','))
    if search:
        print(search)
        orders = orders.filter(refrence_number__icontains=search)
    
    # Build a list of dictionaries with needed fields
    orders_data = []
    for order in orders:
        # Compute a Bootstrap badge class based on the status.
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



from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import PurchaseOrder

@require_POST
def update_order_status(request):
    order_id = request.POST.get('id')
    new_status = request.POST.get('status')
    order = get_object_or_404(PurchaseOrder, id=order_id)
    order.status = new_status
    order.save()

    

    # تحديد فئة البادج بناءً على الحالة
    if new_status == 'supplied':
        badge_class = "bg-success"
        service_providers = order.report.service_request.service_provider.manager.all()
        for service_provider in service_providers:
            message = f'*نظام صيانة النادي الترفيهي الرياضي* \nتم توريد الطلب الخاص بك \n عنوان الطلب كان: {order.report.service_request.title} \n تفاصيل الطلب: {order.report.service_request.description}'
            send_message(service_provider.profile.phone, message)
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





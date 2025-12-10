"""
Admin detail view functions - no external libraries, pure Django
"""
from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from .models import Section, ServiceProvider, Pipeline


def is_staff(user):
    """Check if user is staff"""
    return user.is_staff


@user_passes_test(is_staff)
def user_detail_view(request, pk):
    """Detail view for User model"""
    user = get_object_or_404(User, pk=pk)
    
    # Get related data
    user_profile = getattr(user, 'userprofile', None)
    created_requests = user.created_by.all()[:10]  # Last 10 created requests
    assigned_requests = user.assigned_to.all()[:10]  # Last 10 assigned requests
    sections_managed = Section.objects.filter(manager=user)
    service_providers_managed = ServiceProvider.objects.filter(manager=user)
    
    context = {
        'user': user,
        'user_profile': user_profile,
        'created_requests': created_requests,
        'assigned_requests': assigned_requests,
        'sections_managed': sections_managed,
        'service_providers_managed': service_providers_managed,
        'opts': User._meta,
        'has_view_permission': True,
        'has_add_permission': request.user.has_perm('auth.add_user'),
        'has_change_permission': request.user.has_perm('auth.change_user'),
        'has_delete_permission': request.user.has_perm('auth.delete_user'),
    }
    
    return render(request, 'admin/app1/user_detail.html', context)


@user_passes_test(is_staff)
def user_list_view(request):
    """List view for multiple selected users"""
    # Get selected user IDs from session or request
    user_ids = request.GET.getlist('ids', [])
    if not user_ids:
        # Try to get from POST data
        user_ids = request.POST.getlist('ids', [])
    
    users = User.objects.filter(pk__in=user_ids) if user_ids else User.objects.none()
    
    context = {
        'users': users,
        'opts': User._meta,
        'has_view_permission': True,
    }
    
    return render(request, 'admin/app1/user_list.html', context)


@user_passes_test(is_staff)
def section_detail_view(request, pk):
    """Detail view for Section model"""
    section = get_object_or_404(Section, pk=pk)
    
    # Get related data
    managers = section.manager.all()
    # Get pipelines that include this section (many-to-many relationship)
    pipelines = Pipeline.objects.filter(sections=section)
    service_requests = section.servicerequest_set.all()[:20]  # Last 20 requests
    
    context = {
        'section': section,
        'managers': managers,
        'pipelines': pipelines,
        'service_requests': service_requests,
        'opts': Section._meta,
        'has_view_permission': True,
        'has_add_permission': request.user.has_perm('app1.add_section'),
        'has_change_permission': request.user.has_perm('app1.change_section'),
        'has_delete_permission': request.user.has_perm('app1.delete_section'),
    }
    
    return render(request, 'admin/app1/section_detail.html', context)


@user_passes_test(is_staff)
def section_list_view(request):
    """List view for multiple selected sections"""
    section_ids = request.GET.getlist('ids', []) or request.POST.getlist('ids', [])
    sections = Section.objects.filter(pk__in=section_ids) if section_ids else Section.objects.none()
    
    context = {
        'sections': sections,
        'opts': Section._meta,
        'has_view_permission': True,
    }
    
    return render(request, 'admin/app1/section_list.html', context)


@user_passes_test(is_staff)
def serviceprovider_detail_view(request, pk):
    """Detail view for ServiceProvider model"""
    provider = get_object_or_404(ServiceProvider, pk=pk)
    
    # Get related data
    managers = provider.manager.all()
    service_requests = provider.servicerequest_set.all()[:20]  # Last 20 requests
    
    context = {
        'provider': provider,
        'managers': managers,
        'service_requests': service_requests,
        'opts': ServiceProvider._meta,
        'has_view_permission': True,
        'has_add_permission': request.user.has_perm('app1.add_serviceprovider'),
        'has_change_permission': request.user.has_perm('app1.change_serviceprovider'),
        'has_delete_permission': request.user.has_perm('app1.delete_serviceprovider'),
    }
    
    return render(request, 'admin/app1/serviceprovider_detail.html', context)


@user_passes_test(is_staff)
def serviceprovider_list_view(request):
    """List view for multiple selected service providers"""
    provider_ids = request.GET.getlist('ids', []) or request.POST.getlist('ids', [])
    providers = ServiceProvider.objects.filter(pk__in=provider_ids) if provider_ids else ServiceProvider.objects.none()
    
    context = {
        'providers': providers,
        'opts': ServiceProvider._meta,
        'has_view_permission': True,
    }
    
    return render(request, 'admin/app1/serviceprovider_list.html', context)


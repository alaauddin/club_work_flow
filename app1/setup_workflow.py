#!/usr/bin/env python3
"""
Migration Helper Script for Dynamic Station Workflow System
This script helps set up initial stations and pipelines after migration.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app1.models import Station, Pipeline, PipelineStation
from django.contrib.auth.models import User
from django.db import connection


def ensure_utf8mb4_connection():
    """Ensure database connection uses utf8mb4"""
    with connection.cursor() as cursor:
        try:
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
        except Exception as e:
            print(f"  ⚠ Warning: Could not set utf8mb4 connection: {e}")


def get_or_create_station(name, name_ar, is_initial=False, is_final=False, color='#4169E1', order=0):
    """Helper function to get or create a station"""
    # Ensure UTF-8 connection before creating
    ensure_utf8mb4_connection()
    
    station, created = Station.objects.get_or_create(
        name=name,
        defaults={
            'name_ar': name_ar,
            'is_initial': is_initial,
            'is_final': is_final,
            'color': color,
            'order': order
        }
    )
    if created:
        print(f"  ✓ Created station: {station.name} ({station.name_ar})")
    else:
        # Update existing station if needed
        if station.name_ar != name_ar:
            ensure_utf8mb4_connection()
            station.name_ar = name_ar
            station.save()
        print(f"  - Station already exists: {station.name} ({station.name_ar})")
    return station


def create_required_stations():
    """Create all required workflow stations"""
    print("Creating required stations...")
    
    stations = {}
    
    # Station 1: Enter Accounts
    stations['enter_accounts'] = get_or_create_station(
        name='Enter Accounts',
        name_ar='ادخال الحسابات',
        is_initial=True,
        is_final=False,
        color='#FFA500',
        order=1
    )
    
    # Station 2: Waiting for Purchases
    stations['waiting_purchases'] = get_or_create_station(
        name='Waiting for Purchases',
        name_ar='انتظار المشريات',
        is_initial=False,
        is_final=False,
        color='#FF6B6B',
        order=2
    )
    
    # Station 3: Receive Materials and Start Work
    stations['receive_materials'] = get_or_create_station(
        name='Receive Materials and Start Work',
        name_ar='استلام المواد والبداء بالعمل',
        is_initial=False,
        is_final=False,
        color='#4ECDC4',
        order=3
    )
    
    # Station 4: Under Review (already exists, but we'll ensure it's there)
    stations['under_review'] = get_or_create_station(
        name='Under Review',
        name_ar='قيد المراجعة',
        is_initial=False,
        is_final=False,
        color='#FFD700',
        order=4
    )
    
    # Station 5: In Progress (already exists, but we'll ensure it's there)
    stations['in_progress'] = get_or_create_station(
        name='In Progress',
        name_ar='قيد التنفيذ',
        is_initial=False,
        is_final=False,
        color='#4169E1',
        order=5
    )
    
    return stations


def create_pipeline_needs_materials(stations):
    """Create pipeline: يحتاج مواد (Needs Materials)"""
    print("\nCreating pipeline: يحتاج مواد (Needs Materials)...")
    
    # Ensure UTF-8 connection before creating
    ensure_utf8mb4_connection()
    
    pipeline, created = Pipeline.objects.get_or_create(
        name='Needs Materials',
        defaults={
            'name_ar': 'يحتاج مواد',
            'description': 'Workflow for requests that need materials',
            'is_active': True
        }
    )
    
    if created:
        print(f"  ✓ Created pipeline: {pipeline.name_ar}")
    else:
        print(f"  - Pipeline already exists: {pipeline.name_ar}")
    
    # Define stations in order
    pipeline_stations = [
        stations['enter_accounts'],      # 1. ادخال الحسابات
        stations['waiting_purchases'],   # 2. انتظار المشريات
        stations['receive_materials'],   # 3. استلام المواد والبداء بالعمل
        stations['under_review'],        # 4. المراجعة
    ]
    
    # Clear existing stations and add new ones
    PipelineStation.objects.filter(pipeline=pipeline).delete()
    print("\n  Adding stations to pipeline...")
    for idx, station in enumerate(pipeline_stations, start=1):
        ps, created = PipelineStation.objects.get_or_create(
            pipeline=pipeline,
            station=station,
            defaults={'order': idx, 'can_skip': False}
        )
        if created:
            print(f"    ✓ Added station {idx}: {station.name_ar}")
        else:
            print(f"    - Station {idx} already in pipeline: {station.name_ar}")
    
    return pipeline


def create_pipeline_completion_without_materials(stations):
    """Create pipeline: الانجاز بدون مواد (Completion without Materials)"""
    print("\nCreating pipeline: الانجاز بدون مواد (Completion without Materials)...")
    
    # Ensure UTF-8 connection before creating
    ensure_utf8mb4_connection()
    
    pipeline, created = Pipeline.objects.get_or_create(
        name='Completion without Materials',
        defaults={
            'name_ar': 'الانجاز بدون مواد',
            'description': 'Workflow for requests that don\'t need materials',
            'is_active': True
        }
    )
    
    if created:
        print(f"  ✓ Created pipeline: {pipeline.name_ar}")
    else:
        print(f"  - Pipeline already exists: {pipeline.name_ar}")
    
    # Define stations in order
    pipeline_stations = [
        stations['under_review'],  # قيد المراجعة
    ]
    
    # Clear existing stations and add new ones
    PipelineStation.objects.filter(pipeline=pipeline).delete()
    print("\n  Adding stations to pipeline...")
    for idx, station in enumerate(pipeline_stations, start=1):
        ps, created = PipelineStation.objects.get_or_create(
            pipeline=pipeline,
            station=station,
            defaults={'order': idx, 'can_skip': False}
        )
        if created:
            print(f"    ✓ Added station {idx}: {station.name_ar}")
        else:
            print(f"    - Station {idx} already in pipeline: {station.name_ar}")
    
    return pipeline


def create_pipeline_external_service(stations):
    """Create pipeline: خدمة خارجية (External Service)"""
    print("\nCreating pipeline: خدمة خارجية (External Service)...")
    
    # Ensure UTF-8 connection before creating
    ensure_utf8mb4_connection()
    
    pipeline, created = Pipeline.objects.get_or_create(
        name='External Service',
        defaults={
            'name_ar': 'خدمة خارجية',
            'description': 'Workflow for external service requests',
            'is_active': True
        }
    )
    
    if created:
        print(f"  ✓ Created pipeline: {pipeline.name_ar}")
    else:
        print(f"  - Pipeline already exists: {pipeline.name_ar}")
    
    # Define stations in order
    pipeline_stations = [
        stations['in_progress'],   # 1. قيد التنفيذ
        stations['under_review'],  # 2. قيد المراجعة
    ]
    
    # Clear existing stations and add new ones
    PipelineStation.objects.filter(pipeline=pipeline).delete()
    print("\n  Adding stations to pipeline...")
    for idx, station in enumerate(pipeline_stations, start=1):
        ps, created = PipelineStation.objects.get_or_create(
            pipeline=pipeline,
            station=station,
            defaults={'order': idx, 'can_skip': False}
        )
        if created:
            print(f"    ✓ Added station {idx}: {station.name_ar}")
        else:
            print(f"    - Station {idx} already in pipeline: {station.name_ar}")
    
    return pipeline


def main():
    print("=" * 60)
    print("Dynamic Station Workflow System - Initial Setup")
    print("=" * 60)
    print()
    
    # Create all required stations
    stations = create_required_stations()
    
    # Create the 3 pipelines
    pipeline1 = create_pipeline_needs_materials(stations)
    pipeline2 = create_pipeline_completion_without_materials(stations)
    pipeline3 = create_pipeline_external_service(stations)
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"\nCreated {len(stations)} stations and 3 pipelines:")
    print(f"  1. {pipeline1.name_ar} (يحتاج مواد)")
    print(f"  2. {pipeline2.name_ar} (الانجاز بدون مواد)")
    print(f"  3. {pipeline3.name_ar} (خدمة خارجية)")
    print("\nYou can now:")
    print("1. Access the Django admin to manage stations and pipelines")
    print("2. Create new service requests with the configured pipelines")
    print("3. Move service requests through workflow stations")
    print()


if __name__ == '__main__':
    main()

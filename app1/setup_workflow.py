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


def create_default_stations():
    """Create default workflow stations"""
    print("Creating default stations...")
    
    stations = [
        {
            'name': 'Pending',
            'name_ar': 'قيد الانتظار',
            'is_initial': True,
            'is_final': False,
            'color': '#FFA500',
            'order': 1
        },
        {
            'name': 'In Progress',
            'name_ar': 'قيد التنفيذ',
            'is_initial': False,
            'is_final': False,
            'color': '#4169E1',
            'order': 2
        },
        {
            'name': 'Under Review',
            'name_ar': 'قيد المراجعة',
            'is_initial': False,
            'is_final': False,
            'color': '#FFD700',
            'order': 3
        },
        {
            'name': 'Completed',
            'name_ar': 'مكتمل',
            'is_initial': False,
            'is_final': True,
            'color': '#32CD32',
            'order': 4
        },
    ]
    
    created_stations = []
    for station_data in stations:
        station, created = Station.objects.get_or_create(
            name=station_data['name'],
            defaults=station_data
        )
        if created:
            print(f"  ✓ Created station: {station.name} ({station.name_ar})")
        else:
            print(f"  - Station already exists: {station.name}")
        created_stations.append(station)
    
    return created_stations


def create_default_pipeline(stations):
    """Create a default workflow pipeline"""
    print("\nCreating default pipeline...")
    
    pipeline, created = Pipeline.objects.get_or_create(
        name='Standard Service Workflow',
        defaults={
            'name_ar': 'سير العمل القياسي',
            'description': 'Default workflow for service requests',
            'is_active': True
        }
    )
    
    if created:
        print(f"  ✓ Created pipeline: {pipeline.name}")
        
        # Add stations to pipeline
        print("\n  Adding stations to pipeline...")
        for idx, station in enumerate(stations, start=1):
            ps, created = PipelineStation.objects.get_or_create(
                pipeline=pipeline,
                station=station,
                defaults={'order': idx, 'can_skip': False}
            )
            if created:
                print(f"    ✓ Added station {idx}: {station.name}")
    else:
        print(f"  - Pipeline already exists: {pipeline.name}")
    
    return pipeline


def create_express_pipeline(stations):
    """Create an express workflow pipeline (skips review step)"""
    print("\nCreating express pipeline...")
    
    # Filter out the "Under Review" station
    express_stations = [s for s in stations if s.name != 'Under Review']
    
    pipeline, created = Pipeline.objects.get_or_create(
        name='Express Service Workflow',
        defaults={
            'name_ar': 'سير عمل سريع',
            'description': 'Expedited workflow for simple service requests',
            'is_active': True
        }
    )
    
    if created:
        print(f"  ✓ Created pipeline: {pipeline.name}")
        
        # Add stations to pipeline
        print("\n  Adding stations to pipeline...")
        for idx, station in enumerate(express_stations, start=1):
            ps, created = PipelineStation.objects.get_or_create(
                pipeline=pipeline,
                station=station,
                defaults={'order': idx, 'can_skip': False}
            )
            if created:
                print(f"    ✓ Added station {idx}: {station.name}")
    else:
        print(f"  - Pipeline already exists: {pipeline.name}")
    
    return pipeline


def main():
    print("=" * 60)
    print("Dynamic Station Workflow System - Initial Setup")
    print("=" * 60)
    print()
    
    # Create stations
    stations = create_default_stations()
    
    # Create pipelines
    default_pipeline = create_default_pipeline(stations)
    express_pipeline = create_express_pipeline(stations)
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"\nCreated {len(stations)} stations and 2 pipelines.")
    print("\nYou can now:")
    print("1. Access the Django admin to manage stations and pipelines")
    print("2. Create new service requests with the configured pipelines")
    print("3. Move service requests through workflow stations")
    print()


if __name__ == '__main__':
    main()

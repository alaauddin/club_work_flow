# Dynamic Station Workflow System

## Overview

This system transforms the ServiceRequest status from hardcoded choices to a dynamic, configurable workflow using:
- **Stations**: Individual workflow stages (e.g., Pending, In Progress, Completed)
- **Pipelines**: Workflow templates with ordered stations
- **PipelineStations**: Junction table defining station order within pipelines

## Features

### ✨ Dynamic Workflow Management
- Create and reorder workflow stations on the fly
- Define multiple pipelines with different station sequences
- Move ServiceRequests through stations using helper methods
- Automatic logging of all station transitions

### 🎛️ Admin Interface Features
- **Station Management**: Create stations with Arabic names, colors, and ordering
- **Pipeline Configuration**: Define workflow templates with inline station ordering
- **ServiceRequest Tracking**: View current station and progress percentage
- **Action Buttons**: Move requests to next station with a single click
- **Complete Audit Log**: Track all station changes with timestamps

## Installation

### 1. Run the Setup Script

```bash
cd /path/to/club_work_flow/club_work_flow
./setup_workflow.sh
```

This script will:
1. Create database migrations
2. Apply migrations
3. Create default stations (Pending, In Progress, Under Review, Completed)
4. Create two pipelines (Standard and Express workflows)

### 2. Manual Setup (Alternative)

If the script doesn't work, run these commands manually:

```bash
# Create migrations
python3 manage.py makemigrations app1

# Apply migrations
python3 manage.py migrate

# Setup initial workflow
python3 app1/setup_workflow.py
```

## Usage

### Creating a Station

```python
from app1.models import Station

station = Station.objects.create(
    name='Quality Check',
    name_ar='فحص الجودة',
    description='Quality assurance review',
    is_initial=False,
    is_final=False,
    color='#9370DB',
    order=5
)
```

### Creating a Pipeline

```python
from app1.models import Pipeline, PipelineStation, Station

# Create pipeline
pipeline = Pipeline.objects.create(
    name='QA Workflow',
    name_ar='سير عمل ضمان الجودة',
    is_active=True
)

# Add stations in order
stations = Station.objects.all().order_by('order')
for idx, station in enumerate(stations, start=1):
    PipelineStation.objects.create(
        pipeline=pipeline,
        station=station,
        order=idx,
        can_skip=False
    )
```

### Creating a ServiceRequest

```python
from app1.models import ServiceRequest, Pipeline

# Get a pipeline
pipeline = Pipeline.objects.get(name='Standard Service Workflow')

# Create service request
service_request = ServiceRequest.objects.create(
    title='Fix Air Conditioning',
    description='AC unit not cooling properly',
    section=section,
    service_provider=provider,
    pipeline=pipeline,
    current_station=pipeline.get_initial_station(),
    created_by=user,
    updated_by=user
)
```

### Moving Through Stations

```python
# Move to next station
success, message = service_request.move_to_next_station(
    user=request.user,
    comment='Inspection completed, moving to execution'
)

if success:
    print(message)  # "Successfully moved to In Progress"

# Move to specific station
station = Station.objects.get(name='Under Review')
success, message = service_request.move_to_station(
    station=station,
    user=request.user,
    comment='Sending for manager review'
)

# Check progress
progress = service_request.get_pipeline_progress()  # Returns percentage (0-100)

# Check if completed
if service_request.is_completed():
    print("Service request is complete!")
```

## Model Reference

### Station
- `name`: English name
- `name_ar`: Arabic name
- `description`: Optional description
- `is_initial`: Mark as starting station
- `is_final`: Mark as completion station
- `color`: Hex color code for UI
- `order`: Display order

### Pipeline
- `name`: English name
- `name_ar`: Arabic name
- `description`: What this pipeline is for
- `sections`: Which sections can use this pipeline
- `is_active`: Enable/disable pipeline
- `stations`: Related via PipelineStation

**Methods:**
- `get_ordered_stations()`: Returns stations in order
- `get_initial_station()`: Returns first station

### PipelineStation
- `pipeline`: FK to Pipeline
- `station`: FK to Station
- `order`: Station order in pipeline
- `can_skip`: Can this station be skipped?
- `required_role`: Group required to approve

### ServiceRequest
- `pipeline`: FK to Pipeline
- `current_station`: FK to Station
- `station_entered_at`: When entered current station

**Methods:**
- `get_next_station()`: Next station or None
- `get_previous_station()`: Previous station or None
- `can_move_to_next(user)`: Check if user can move forward
- `move_to_next_station(user, comment)`: Move forward
- `move_to_station(station, user, comment)`: Move to specific station
- `get_pipeline_progress()`: Get percentage complete
- `is_completed()`: Check if in final station

### ServiceRequestLog
Automatically created when stations change. Tracks:
- `from_station`: Where it came from
- `to_station`: Where it went
- `log_type`: Type of log (station_change, comment, etc.)
- `comment`: Description
- `created_by`: Who made the change
- `created_at`: When it happened

## Admin Interface

### Managing Stations
1. Go to Admin → Stations
2. Create new stations with Arabic names and colors
3. Reorder using the `order` field
4. Mark initial/final stations

### Managing Pipelines
1. Go to Admin → Pipelines
2. Create a new pipeline
3. Use the inline form to add stations in order
4. Set which sections can use this pipeline
5. Optionally set required roles for specific stations

### Managing Service Requests
1. View current station and progress percentage
2. Use "Move to Next Station" action for bulk operations
3. View complete history in the ServiceRequestLog inline

## Migration Notes

> [!WARNING]
> **Breaking Change**: The `status` field has been removed from ServiceRequest.

### For Existing ServiceRequests
After running migrations, existing ServiceRequest records will need:
1. Assignment to a pipeline
2. Setting of current_station

You can do this via Django admin or create a data migration script.

### Example Data Migration

```python
from app1.models import ServiceRequest, Pipeline, Station

# Get default pipeline
pipeline = Pipeline.objects.get(name='Standard Service Workflow')

# Map old status to stations
status_map = {
    'pending': 'Pending',
    'in_progress': 'In Progress',
    'under_review': 'Under Review',
    'completed': 'Completed',
}

# This would be in a proper data migration, but shown here for reference
# for request in ServiceRequest.objects.all():
#     request.pipeline = pipeline
#     station_name = status_map.get(request.status, 'Pending')
#     request.current_station = Station.objects.get(name=station_name)
#     request.save()
```

## Default Workflows

### Standard Service Workflow
1. Pending (قيد الانتظار)
2. In Progress (قيد التنفيذ)
3. Under Review (قيد المراجعة)
4. Completed (مكتمل)

### Express Service Workflow
1. Pending (قيد الانتظار)
2. In Progress (قيد التنفيذ)
3. Completed (مكتمل)

## Customization

### Adding Custom Stations
Create stations for your specific workflow needs:
- Approval Pending
- Budget Review
- Waiting for Parts
- On Hold
- Cancelled
- etc.

### Creating Department-Specific Pipelines
Different departments can have different workflows:
- IT Support Pipeline
- Facilities Maintenance Pipeline
- HR Request Pipeline

### Role-Based Approvals
Set `required_role` on PipelineStation to restrict who can approve transitions.

## Troubleshooting

### Django Not Found
Make sure you're in the correct virtual environment:
```bash
source venv/bin/activate  # or your virtualenv path
pip install django
```

### Migrations Fail
If migrations fail, try:
```bash
python3 manage.py makemigrations --empty app1
# Then manually edit the migration file
python3 manage.py migrate
```

### Existing Data Issues
If you have existing ServiceRequest data, you'll need to:
1. Back up your database
2. Run migrations
3. Assign pipelines and stations to existing requests

## Support

For issues or questions, refer to:
- [Django Documentation](https://docs.djangoproject.com/)
- [models.py](app1/models.py) - All model definitions
- [admin.py](app1/admin.py) - Admin configuration

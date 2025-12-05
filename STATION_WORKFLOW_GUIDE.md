# Quick Reference: Using the Station Workflow System

## For Administrators

### Creating Stations
1. Go to Django Admin → Stations
2. Add new station with:
   - Name (English) and Name AR (Arabic)
   - Color (hex code like #FF5733)
   - Order number
   - Mark as is_initial or is_final if needed
   - Add allowed_users if you want to restrict access

### Creating Pipelines
1. Go to Django Admin → Pipelines
2. Create pipeline with name
3. Use inline form to add stations in order
4. Assign to sections if needed

## For Users

### Creating Service Requests
1. Fill in title and description
2. Select section and service provider
3. **NEW**: Select a pipeline (workflow path)
4. Request automatically starts at initial station

### Moving Through Stations
Two ways to move:

**Option 1: Next Button**
- Click the green "الانتقال إلى" button
- Automatically moves to next station in sequence

**Option 2: Manual Selection**
- Use dropdown "الانتقال إلى محطة محددة"
- Jump to any station you have access to
- Useful for sending back to previous stages

### Understanding Progress
- **Progress Bar**: Shows completion percentage
- **Station Timeline**: All stations with current one highlighted
- **Station Badge**: Color-coded current station

## Permissions

### allowed_users Field
- Empty = anyone can use this station
- Populated = only listed users can move TO or FROM this station
- Configured per station in admin

## Common Workflows

### Standard Flow
1. Pending → 2. In Progress → 3. Under Review → 4. Completed

### Express Flow
1. Pending → 2. In Progress → 3. Completed

### Custom Department Flows
Create your own pipelines with custom stations!

## API Endpoints

```
/move_to_next/<id>/          - Move to next station
/move_to_station/<id>/<station_id>/  - Move to specific station
```

## Tips

- Use colors to distinguish station types (pending=orange, progress=blue, review=yellow, complete=green)
- Set allowed_users on critical stations (like final approval)
- Create multiple pipelines for different service types
- Monitor progress with the timeline view

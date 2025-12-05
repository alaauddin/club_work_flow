# Template Updates Guide

## ✅ Completed Updates

### 1. `request_detail.html` - **FULLY UPDATED**
- ✅ Replaced status badge with station-based badge showing `current_station.name_ar`
- ✅ Added station workflow component (`{% include 'includes/station_workflow.html' %}`)
- ✅ Changed status checks to `is_completed()` method
- ✅ Updated legacy button visibility to use `current_station.name`

###2. `create_service_request.html` - **FULLY UPDATED**
- ✅ Added pipeline selection dropdown in Step 2
- ✅ Updated JavaScript validation to include pipeline
- ✅ Added pipeline review in Step 3

### 3. New Templates Created
- ✅ `move_to_next_station.html` - UI for moving to next station
- ✅ `move_to_station.html` - UI for manual station selection
- ✅ `includes/station_workflow.html` - Reusable workflow component

---

## 🔧 Manual Updates Required

### Template: `my_request.html`
**Location:** Lines 255-267 and 282-295

**Find and replace ALL status checks with station checks:**

```html
<!-- OLD STATUS CODE (lines 255-267 in table) -->
{% if request.status == 'pending' %}
  <span class="badge bg-warning"><i class="fas fa-hourglass-half"></i> قيد الانتظار</span>
{% elif request.status == 'in_progress' %}
  <span class="badge bg-info text-dark"><i class="fas fa-spinner"></i> قيد التنفيذ</span>
{% elif request.status == 'completed' %}
  <span class="badge bg-success"><i class="fas fa-check-circle"></i> مكتمل</span>
{% elif request.status == 'under_review' %}
  <span class="badge bg-primary"><i class="fas fa-eye"></i> قيد المراجعة</span>
{% else %}
  <span class="badge bg-light text-dark">{{ request.status }}</span>
{% endif %}

<!-- NEW STATION CODE -->
<span class="badge" style="background-color: {{ request.current_station.color}}; color: #fff;">
  <i class="fas fa-circle"></i> {{ request.current_station.name_ar }}
</span>
```

**DO THE SAME for mobile cards section (lines 282-295)**

---

### Template: `requests_to_me.html`  
**Location:** Lines 278-287 and 318-327

**Replace status badges with station badges (same pattern as above):**

```html
<!-- Replace both table and mobile card status sections -->
<span class="badge" style="background-color: {{ request.current_station.color}}; color: #fff;">
  <i class="fas fa-circle"></i> {{ request.current_station.name_ar }}
</span>
```

---

### Template: `request_detail_sm.html`
**Location:** Lines 27-36, 53-57, 132-141

**1. Replace status badge (lines 27-36):**
```html
<!-- OLD -->
{% if service_request.status == '...' %}

<!-- NEW -->
<span class="badge" style="background-color: {{ service_request.current_station.color}}; color: #fff;">
  <i class="fas fa-circle ms-1"></i> {{ service_request.current_station.name_ar }}
</span>
{% if service_request.is_completed %}
  <span class="badge bg-success ms-2"><i class="fas fa-check-circle"></i> مكتمل</span>
{% endif %}
```

**2. Replace action buttons logic (lines 53-57):**
```html
<!-- OLD -->
{% if service_request.status == 'pending' or service_request.status == 'in_progress' %}

<!-- NEW -->
{% if not service_request.is_completed %}
```

**3. Add station workflow component AFTER header section:**
```html
<!-- Add this after the hero/header card -->
{% include 'includes/station_workflow.html' %}
```

---

## 📝 Quick Find & Replace Guide

For ALL templates, use these replacements:

| **Find** | **Replace With** |
|----------|------------------|
| `service_request.status ==` | `service_request.current_station.name ==` (for specific stations) |
| `service_request.status == 'pending' or service_request.status == 'in_progress'` | `not service_request.is_completed` |
| `{% if service_request.status == 'under_review' %}` | `{% if service_request.current_station.name == 'Under Review' %}` |
| Status badge blocks | Station badge: `<span class="badge" style="background-color: {{ request.current_station.color}}; color: #fff;"><i class="fas fa-circle"></i> {{ request.current_station.name_ar }}</span>` |

---

## 🎨 Station Badge Template

**For list views (my_request, requests_to_me):**
```html
<span class="badge" style="background-color: {{ request.current_station.color}}; color: #fff;">
  <i class="fas fa-circle"></i> {{ request.current_station.name_ar }}
</span>
```

**For detail views (request_detail, request_detail_sm):**
```html
<span class="badge rounded-pill px-3 py-2" style="background-color: {{ service_request.current_station.color }}; color: #fff;">
  <i class="fas fa-circle ms-1"></i> {{ service_request.current_station.name_ar }}
</span>
{% if service_request.is_completed %}
  <span class="badge bg-success rounded-pill px-2 py-1 ms-2">
    <i class="fas fa-check-circle ms-1"></i> مكتمل
  </span>
{% endif %}
```

---

## ✅ Verification Checklist

After making the changes, verify:

- [ ] No more references to `request.status` or `service_request.status` in templates
- [ ] All badges show station colors dynamically  
- [ ] Station workflow component appears in detail views
- [ ] Progress bar shows correctly
- [ ] Next/Previous station buttons work
- [ ] Manual station dropdown populated correctly
- [ ] Completed requests show check mark badge
- [ ] Dashboard/list views show colored station badges

---

## 🚀 Test Flow

1. Create a new service request with pipeline selection
2. View it in detail - should show station workflow component
3. Click "Move to Next" - transitions to next station
4. View my_request list - should show colored badge
5. Move through all stations to completion
6. Verify completed badge appears

---

## 📂 Files to Update Manually

1. `/home/alauddin/Documents/alauddin/club_work_flow/club_work_flow/app1/templates/read/my_request.html`
2. `/home/alauddin/Documents/alauddin/club_work_flow/club_work_flow/app1/templates/read/requests_to_me.html`
3. `/home/alauddin/Documents/alauddin/club_work_flow/club_work_flow/app1/templates/read/request_detail_sm.html`

Use VS Code Find & Replace (Ctrl+H) for bulk changes!

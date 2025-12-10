#!/usr/bin/env python3
"""
Data Import Script for Club Work Flow
Imports Users, UserProfiles, Sections, and ServiceProviders from JSON/CSV files
"""

import os
import sys
import django
import json
import csv
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from app1.models import UserProfile, Section, ServiceProvider


def import_users_from_csv(csv_file_path):
    """Import users from CSV file"""
    print("=" * 60)
    print("Importing Users from CSV...")
    print("=" * 60)
    
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found: {csv_file_path}")
        return
    
    created_count = 0
    updated_count = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get('username', '').strip()
            if not username:
                print(f"  ⚠ Skipping row with empty username")
                continue
            
            # Parse boolean fields
            is_staff = row.get('is_staff', '0').strip() in ('1', 'True', 'true')
            is_active = row.get('is_active', '1').strip() in ('1', 'True', 'true')
            is_superuser = row.get('is_superuser', '0').strip() in ('1', 'True', 'true')
            
            # Parse dates
            date_joined = None
            if row.get('date_joined'):
                try:
                    date_joined = datetime.strptime(row['date_joined'].strip(), '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        date_joined = datetime.strptime(row['date_joined'].strip(), '%Y-%m-%d')
                    except:
                        pass
            
            last_login = None
            if row.get('last_login'):
                try:
                    last_login = datetime.strptime(row['last_login'].strip(), '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        last_login = datetime.strptime(row['last_login'].strip(), '%Y-%m-%d')
                    except:
                        pass
            
            # Get or create user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': row.get('first_name', '').strip(),
                    'last_name': row.get('last_name', '').strip(),
                    'email': row.get('email', '').strip() or '',
                    'is_staff': is_staff,
                    'is_active': is_active,
                    'is_superuser': is_superuser,
                }
            )
            
            if not created:
                # Update existing user
                user.first_name = row.get('first_name', '').strip()
                user.last_name = row.get('last_name', '').strip()
                user.email = row.get('email', '').strip() or ''
                user.is_staff = is_staff
                user.is_active = is_active
                user.is_superuser = is_superuser
                user.save()
                updated_count += 1
                print(f"  ✓ Updated user: {username}")
            else:
                created_count += 1
                print(f"  ✓ Created user: {username}")
            
            # Set password to '123' for all users
            user.set_password('123')
            user.save()
            
            # Set dates if provided
            if date_joined:
                user.date_joined = date_joined
                user.save(update_fields=['date_joined'])
            if last_login:
                user.last_login = last_login
                user.save(update_fields=['last_login'])
    
    print(f"\nUsers: {created_count} created, {updated_count} updated")
    print()


def import_user_profiles_from_json(json_file_path):
    """Import user profiles from JSON file"""
    print("=" * 60)
    print("Importing User Profiles from JSON...")
    print("=" * 60)
    
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file not found: {json_file_path}")
        return
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        for item in data:
            user_id = item.get('user')
            phone = item.get('phone', '').strip()
            
            if not user_id:
                print(f"  ⚠ Skipping profile with no user ID")
                error_count += 1
                continue
            
            try:
                user = User.objects.get(pk=int(user_id))
            except User.DoesNotExist:
                print(f"  ✗ User with ID {user_id} not found, skipping profile")
                error_count += 1
                continue
            except ValueError:
                print(f"  ✗ Invalid user ID: {user_id}, skipping profile")
                error_count += 1
                continue
            
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'phone': phone}
            )
            
            if not created:
                profile.phone = phone
                profile.save()
                updated_count += 1
                print(f"  ✓ Updated profile for user: {user.username}")
            else:
                created_count += 1
                print(f"  ✓ Created profile for user: {user.username}")
    
    print(f"\nUser Profiles: {created_count} created, {updated_count} updated, {error_count} errors")
    print()


def import_sections_from_json(json_file_path):
    """Import sections from JSON file"""
    print("=" * 60)
    print("Importing Sections from JSON...")
    print("=" * 60)
    
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file not found: {json_file_path}")
        return
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        for item in data:
            name = item.get('name', '').strip()
            manager_ids_str = item.get('manager', '')
            
            if not name:
                print(f"  ⚠ Skipping section with no name")
                error_count += 1
                continue
            
            # Get or create section
            section, created = Section.objects.get_or_create(
                name=name,
                defaults={}
            )
            
            if not created:
                updated_count += 1
                print(f"  ✓ Updated section: {name}")
            else:
                created_count += 1
                print(f"  ✓ Created section: {name}")
            
            # Handle managers (comma-separated user IDs)
            if manager_ids_str:
                manager_ids = [mid.strip() for mid in str(manager_ids_str).split(',') if mid.strip()]
                managers = []
                
                for manager_id in manager_ids:
                    try:
                        manager = User.objects.get(pk=int(manager_id))
                        managers.append(manager)
                    except User.DoesNotExist:
                        print(f"    ⚠ User with ID {manager_id} not found, skipping")
                    except ValueError:
                        print(f"    ⚠ Invalid user ID: {manager_id}, skipping")
                
                section.manager.set(managers)
                if managers:
                    print(f"    → Set {len(managers)} manager(s)")
    
    print(f"\nSections: {created_count} created, {updated_count} updated, {error_count} errors")
    print()


def import_service_providers_from_json(json_file_path):
    """Import service providers from JSON file"""
    print("=" * 60)
    print("Importing Service Providers from JSON...")
    print("=" * 60)
    
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file not found: {json_file_path}")
        return
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        for item in data:
            name = item.get('name', '').strip()
            manager_ids_str = item.get('manager', '')
            
            if not name:
                print(f"  ⚠ Skipping service provider with no name")
                error_count += 1
                continue
            
            # Get or create service provider
            provider, created = ServiceProvider.objects.get_or_create(
                name=name,
                defaults={}
            )
            
            if not created:
                updated_count += 1
                print(f"  ✓ Updated service provider: {name}")
            else:
                created_count += 1
                print(f"  ✓ Created service provider: {name}")
            
            # Handle managers (comma-separated user IDs)
            if manager_ids_str:
                manager_ids = [mid.strip() for mid in str(manager_ids_str).split(',') if mid.strip()]
                managers = []
                
                for manager_id in manager_ids:
                    try:
                        manager = User.objects.get(pk=int(manager_id))
                        managers.append(manager)
                    except User.DoesNotExist:
                        print(f"    ⚠ User with ID {manager_id} not found, skipping")
                    except ValueError:
                        print(f"    ⚠ Invalid user ID: {manager_id}, skipping")
                
                provider.manager.set(managers)
                if managers:
                    print(f"    → Set {len(managers)} manager(s)")
    
    print(f"\nService Providers: {created_count} created, {updated_count} updated, {error_count} errors")
    print()


def main():
    """Main import function"""
    print("=" * 60)
    print("Club Work Flow - Data Import Script")
    print("=" * 60)
    print()
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Define file paths (assuming files are in project root)
    user_csv = os.path.join(project_root, 'User-2025-12-10.csv')
    userprofile_json = os.path.join(project_root, 'UserProfile-2025-12-10.json')
    section_json = os.path.join(project_root, 'Section-2025-12-10.json')
    serviceprovider_json = os.path.join(project_root, 'ServiceProvider-2025-12-10.json')
    
    # Check if files exist
    files_to_check = {
        'Users CSV': user_csv,
        'User Profiles JSON': userprofile_json,
        'Sections JSON': section_json,
        'Service Providers JSON': serviceprovider_json,
    }
    
    print("Checking for import files...")
    all_files_exist = True
    for file_type, file_path in files_to_check.items():
        if os.path.exists(file_path):
            print(f"  ✓ {file_type}: {file_path}")
        else:
            print(f"  ✗ {file_type}: {file_path} (NOT FOUND)")
            all_files_exist = False
    print()
    
    if not all_files_exist:
        print("Warning: Some files are missing. Continuing with available files...")
        print()
    
    # Import in order: Users first (required for other imports)
    if os.path.exists(user_csv):
        import_users_from_csv(user_csv)
    else:
        print("Warning: User CSV file not found. Skipping user import.")
        print("Note: User profiles, sections, and service providers require users to exist first.")
        print()
    
    # Import user profiles (requires users)
    if os.path.exists(userprofile_json):
        import_user_profiles_from_json(userprofile_json)
    
    # Import sections (requires users for managers)
    if os.path.exists(section_json):
        import_sections_from_json(section_json)
    
    # Import service providers (requires users for managers)
    if os.path.exists(serviceprovider_json):
        import_service_providers_from_json(serviceprovider_json)
    
    print("=" * 60)
    print("Import Complete!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Users imported from: {user_csv if os.path.exists(user_csv) else 'N/A'}")
    print(f"  - User Profiles imported from: {userprofile_json if os.path.exists(userprofile_json) else 'N/A'}")
    print(f"  - Sections imported from: {section_json if os.path.exists(section_json) else 'N/A'}")
    print(f"  - Service Providers imported from: {serviceprovider_json if os.path.exists(serviceprovider_json) else 'N/A'}")
    print()
    print("Note: All imported users have password set to '123'")
    print()


if __name__ == '__main__':
    main()


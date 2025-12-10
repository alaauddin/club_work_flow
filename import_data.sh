#!/bin/bash
# Data Import Script for Club Work Flow
# Imports Users, UserProfiles, Sections, and ServiceProviders from JSON/CSV files

echo "======================================"
echo "Club Work Flow - Data Import"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the project root."
    exit 1
fi

# Check if required files exist
echo "Checking for import files..."
FILES_EXIST=true

if [ ! -f "User-2025-12-10.csv" ]; then
    echo "  ✗ User-2025-12-10.csv (NOT FOUND)"
    FILES_EXIST=false
else
    echo "  ✓ User-2025-12-10.csv"
fi

if [ ! -f "UserProfile-2025-12-10.json" ]; then
    echo "  ✗ UserProfile-2025-12-10.json (NOT FOUND)"
    FILES_EXIST=false
else
    echo "  ✓ UserProfile-2025-12-10.json"
fi

if [ ! -f "Section-2025-12-10.json" ]; then
    echo "  ✗ Section-2025-12-10.json (NOT FOUND)"
    FILES_EXIST=false
else
    echo "  ✓ Section-2025-12-10.json"
fi

if [ ! -f "ServiceProvider-2025-12-10.json" ]; then
    echo "  ✗ ServiceProvider-2025-12-10.json (NOT FOUND)"
    FILES_EXIST=false
else
    echo "  ✓ ServiceProvider-2025-12-10.json"
fi

echo ""

if [ "$FILES_EXIST" = false ]; then
    echo "Warning: Some files are missing. The script will continue with available files."
    echo ""
fi

# Run the import script
echo "Running import script..."
echo ""
python3 app1/import_data.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Import failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "======================================"
echo "Import Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Verify the imported data in Django admin"
echo "2. Check that all users have profiles"
echo "3. Verify sections and service providers have managers assigned"
echo "4. Note: All imported users have password set to '123'"
echo ""


#!/bin/bash
# Migration and Setup Script for Dynamic Station Workflow System

echo "======================================"
echo "Dynamic Station Workflow Setup"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the project root."
    exit 1
fi

# Step 1: Make migrations
echo "Step 1: Creating migrations..."
python3 manage.py makemigrations app1
if [ $? -ne 0 ]; then
    echo "Error: Failed to create migrations"
    exit 1
fi
echo ""

# Step 2: Apply migrations
echo "Step 2: Applying migrations..."
python3 manage.py migrate
if [ $? -ne 0 ]; then
    echo "Error: Failed to apply migrations"
    exit 1
fi
echo ""

# Step 3: Setup initial stations and pipelines
echo "Step 3: Setting up initial stations and pipelines..."
python3 app1/setup_workflow.py
if [ $? -ne 0 ]; then
    echo "Error: Failed to setup workflow"
    exit 1
fi
echo ""

echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Run the development server: python3 manage.py runserver"
echo "2. Access Django admin to manage workflows"
echo "3. Note: Existing ServiceRequests will need manual pipeline assignment"
echo ""

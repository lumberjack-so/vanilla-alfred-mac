#!/usr/bin/env python3
"""
Plane PM Initial Setup Script

Creates the default workspace structure for Alfred:
- Workspace: (user-provided name)
- Projects: Household, Alfred, Business, Backlog
- Alfred user (optional, if email provided)
- Default states for workflows

Usage:
    python3 plane-setup.py --workspace "my-workspace" --email "user@example.com" --alfred-email "alfred@example.com"
    python3 plane-setup.py --workspace "my-workspace" --email "user@example.com" --skip-alfred-user
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, List

# =============================================================================
# CONFIGURATION
# =============================================================================

HOME_DIR = os.path.expanduser("~")
API_KEY_FILE = f"{HOME_DIR}/.config/plane/api_key"
PLANE_URL = os.environ.get("PLANE_URL", "http://localhost:8080")
API_BASE = f"{PLANE_URL}/api/v1"

# Default projects to create
DEFAULT_PROJECTS = [
    {
        "name": "Household",
        "identifier": "HSH",
        "description": "Family, home, and personal projects"
    },
    {
        "name": "Alfred",
        "identifier": "A",
        "description": "AI butler infrastructure, tools, and capabilities"
    },
    {
        "name": "Business",
        "identifier": "BIZ",
        "description": "Business, products, and content"
    },
    {
        "name": "Backlog",
        "identifier": "BKL",
        "description": "Inbound requests for review"
    }
]

# Default states for issue workflows
DEFAULT_STATES = [
    {"name": "Backlog", "group": "backlog", "color": "#a3a3a3"},
    {"name": "Todo", "group": "started", "color": "#3a3a3a"},
    {"name": "In Progress", "group": "started", "color": "#f59e0b"},
    {"name": "Done", "group": "completed", "color": "#16a34a"},
    {"name": "Cancelled", "group": "cancelled", "color": "#dc2626"}
]

# =============================================================================
# PLANE API CLIENT
# =============================================================================

def load_api_key() -> str:
    """Load Plane API key from config file."""
    if not os.path.exists(API_KEY_FILE):
        raise FileNotFoundError(f"API key not found at {API_KEY_FILE}. Please create it first.")
    with open(API_KEY_FILE) as f:
        return f.read().strip()


def make_request(method: str, endpoint: str, data: Optional[Dict] = None, api_key: Optional[str] = None) -> Dict:
    """Make a request to Plane API."""
    if not api_key:
        api_key = load_api_key()
    
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)

# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

def get_or_create_workspace(workspace_slug: str, owner_email: str, api_key: str) -> Dict:
    """Get existing workspace or create a new one."""
    print(f"🔍 Checking for workspace: {workspace_slug}")
    
    # List workspaces
    workspaces = make_request("GET", "workspaces/", api_key=api_key)
    
    for ws in workspaces:
        if ws.get("slug") == workspace_slug:
            print(f"✓ Workspace '{workspace_slug}' already exists")
            return ws
    
    print(f"📝 Creating workspace: {workspace_slug}")
    workspace = make_request("POST", "workspaces/", data={
        "name": workspace_slug.replace("-", " ").title(),
        "slug": workspace_slug
    }, api_key=api_key)
    
    print(f"✓ Workspace created: {workspace['name']}")
    return workspace


def create_project(workspace_slug: str, project_data: Dict, api_key: str) -> Dict:
    """Create a project in the workspace."""
    print(f"📦 Creating project: {project_data['name']} ({project_data['identifier']})")
    
    project = make_request(
        "POST",
        f"workspaces/{workspace_slug}/projects/",
        data=project_data,
        api_key=api_key
    )
    
    print(f"   ✓ Project created: {project['name']}")
    return project


def get_existing_projects(workspace_slug: str, api_key: str) -> List[Dict]:
    """Get list of existing projects in workspace."""
    return make_request("GET", f"workspaces/{workspace_slug}/projects/", api_key=api_key)


def invite_alfred_user(workspace_slug: str, alfred_email: str, api_key: str) -> Optional[Dict]:
    """Invite Alfred user to the workspace."""
    print(f"👤 Inviting Alfred user: {alfred_email}")
    
    try:
        # Invite as member
        result = make_request(
            "POST",
            f"workspaces/{workspace_slug}/members/add/",
            data={
                "emails": [alfred_email],
                "role": 10  # Member role
            },
            api_key=api_key
        )
        print(f"   ✓ Alfred user invited")
        return result
    except Exception as e:
        print(f"   ⚠️  Failed to invite Alfred user: {e}")
        print(f"   You may need to manually add {alfred_email} to the workspace")
        return None


def setup_states(workspace_slug: str, project_id: str, api_key: str):
    """Set up default states for a project."""
    print(f"🔧 Setting up default states...")
    
    # Get existing states
    try:
        states = make_request("GET", f"workspaces/{workspace_slug}/projects/{project_id}/states/", api_key=api_key)
        if len(states) > 0:
            print("   ℹ️  States already exist, skipping")
            return
    except Exception:
        pass
    
    # Create default states
    for state_data in DEFAULT_STATES:
        try:
            make_request(
                "POST",
                f"workspaces/{workspace_slug}/projects/{project_id}/states/",
                data=state_data,
                api_key=api_key
            )
        except Exception as e:
            print(f"   ⚠️  Failed to create state '{state_data['name']}': {e}")
    
    print("   ✓ States configured")

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Set up Plane PM for Alfred")
    parser.add_argument("--workspace", required=True, help="Workspace slug (e.g., 'my-workspace')")
    parser.add_argument("--email", required=True, help="Owner email address")
    parser.add_argument("--alfred-email", help="Alfred's email address (optional)")
    parser.add_argument("--skip-alfred-user", action="store_true", help="Skip creating Alfred user")
    parser.add_argument("--api-key-file", default=API_KEY_FILE, help="Path to API key file")
    
    args = parser.parse_args()
    
    # Update API key file path if provided
    global API_KEY_FILE
    API_KEY_FILE = args.api_key_file
    
    # Load API key
    try:
        api_key = load_api_key()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"\nTo get an API key:")
        print(f"1. Log in to Plane at {PLANE_URL}")
        print(f"2. Go to Settings → API Tokens")
        print(f"3. Create a new token")
        print(f"4. Save it to {API_KEY_FILE}")
        sys.exit(1)
    
    print("=" * 70)
    print("Plane PM Setup for Alfred")
    print("=" * 70)
    
    # 1. Get or create workspace
    workspace = get_or_create_workspace(args.workspace, args.email, api_key)
    workspace_slug = workspace["slug"]
    
    # 2. Get existing projects
    existing_projects = get_existing_projects(workspace_slug, api_key)
    existing_identifiers = {p.get("identifier") for p in existing_projects}
    
    # 3. Create default projects
    print("\n📋 Setting up default projects...")
    created_projects = []
    for project_data in DEFAULT_PROJECTS:
        if project_data["identifier"] in existing_identifiers:
            print(f"   ℹ️  Project '{project_data['name']}' already exists, skipping")
            # Find the existing project
            existing = next((p for p in existing_projects if p.get("identifier") == project_data["identifier"]), None)
            if existing:
                created_projects.append(existing)
        else:
            project = create_project(workspace_slug, project_data, api_key)
            created_projects.append(project)
    
    # 4. Set up states for each project
    print("\n🔧 Configuring project states...")
    for project in created_projects:
        setup_states(workspace_slug, project["id"], api_key)
    
    # 5. Invite Alfred user (optional)
    if not args.skip_alfred_user and args.alfred_email:
        print()
        invite_alfred_user(workspace_slug, args.alfred_email, api_key)
    
    # 6. Summary
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print(f"\nWorkspace: {workspace['name']}")
    print(f"URL: {PLANE_URL}")
    print(f"\nProjects created:")
    for project in created_projects:
        print(f"  • {project['name']} ({project.get('identifier', 'N/A')})")
    
    if not args.skip_alfred_user and args.alfred_email:
        print(f"\nAlfred user: {args.alfred_email}")
        print("  (Check email for invitation link)")
    
    print(f"\nNext steps:")
    print(f"1. Visit {PLANE_URL} and log in")
    print(f"2. Explore your projects")
    print(f"3. Configure OpenClaw to use this Plane instance")
    print()


if __name__ == "__main__":
    main()

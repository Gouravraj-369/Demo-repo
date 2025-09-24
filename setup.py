#!/usr/bin/env python3
"""
Setup script for Trivy Security Verification Automation

This script helps set up the virtual environment and install dependencies
for the Trivy verification automation tool.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(command, description):
    """
    Run a shell command and handle errors
    
    Args:
        command (str): Command to execute
        description (str): Description of what the command does
    """
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None


def create_virtual_environment():
    """
    Create a Python virtual environment
    """
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("📁 Virtual environment already exists")
        return True
    
    print("📁 Creating virtual environment...")
    try:
        venv.create(venv_path, with_pip=True)
        print("✅ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False


def install_dependencies():
    """
    Install Python dependencies from requirements.txt
    """
    # Determine the correct pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = ".venv/Scripts/pip"
        python_path = ".venv/Scripts/python"
    else:  # Unix-like systems
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"
    
    # Upgrade pip first
    upgrade_result = run_command(
        f"{python_path} -m pip install --upgrade pip",
        "Upgrading pip"
    )
    
    if not upgrade_result:
        return False
    
    # Install dependencies
    install_result = run_command(
        f"{pip_path} install -r requirements.txt",
        "Installing dependencies"
    )
    
    return install_result is not None


def create_environment_file():
    """
    Create a .env file template for environment variables
    """
    env_file = Path(".env")
    
    if env_file.exists():
        print("📄 .env file already exists")
        return True
    
    env_template = """# Trivy Security Verification Automation Environment Variables
# Copy this file and update the values as needed

# GitLab Configuration
GITLAB_TOKEN=your_gitlab_access_token_here
GITLAB_BASE_URL=https://gitlab.com
GITLAB_GROUP_ID=ccm

# Optional: Slack Notifications
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# Optional: Email Notifications
SMTP_SERVER=your_smtp_server_here
SMTP_PORT=587
SMTP_USERNAME=your_email_username_here
SMTP_PASSWORD=your_email_password_here
EMAIL_FROM=your_email@company.com
EMAIL_TO=recipient@company.com

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=trivy_verification.log

# Performance Settings
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY=0.1
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_template)
        print("✅ .env template file created")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def create_gitignore():
    """
    Create a .gitignore file to exclude sensitive files
    """
    gitignore_file = Path(".gitignore")
    
    if gitignore_file.exists():
        print("📄 .gitignore file already exists")
        return True
    
    gitignore_content = """# Virtual Environment
.venv/
venv/
env/

# Environment Variables
.env
.env.local
.env.production

# Logs
*.log
logs/

# Reports
reports/
*.json
*.html
*.csv
*.xlsx

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
.cache/
"""
    
    try:
        with open(gitignore_file, 'w') as f:
            f.write(gitignore_content)
        print("✅ .gitignore file created")
        return True
    except Exception as e:
        print(f"❌ Failed to create .gitignore file: {e}")
        return False


def create_run_script():
    """
    Create a convenient run script for the automation
    """
    if os.name == 'nt':  # Windows
        script_name = "run_verification.bat"
        script_content = """@echo off
REM Trivy Security Verification Automation Runner
REM This script runs the verification automation in the virtual environment

echo Starting Trivy Security Verification Automation...

REM Activate virtual environment
call .venv\\Scripts\\activate.bat

REM Run the verification script
python trivy_verification_automation.py %*

REM Deactivate virtual environment
deactivate

echo Verification completed.
pause
"""
    else:  # Unix-like systems
        script_name = "run_verification.sh"
        script_content = """#!/bin/bash
# Trivy Security Verification Automation Runner
# This script runs the verification automation in the virtual environment

echo "Starting Trivy Security Verification Automation..."

# Activate virtual environment
source .venv/bin/activate

# Run the verification script
python trivy_verification_automation.py "$@"

# Deactivate virtual environment
deactivate

echo "Verification completed."
"""
    
    script_path = Path(script_name)
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make the script executable on Unix-like systems
        if os.name != 'nt':
            os.chmod(script_path, 0o755)
        
        print(f"✅ {script_name} created")
        return True
    except Exception as e:
        print(f"❌ Failed to create {script_name}: {e}")
        return False


def main():
    """
    Main setup function
    """
    print("🚀 Setting up Trivy Security Verification Automation")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create supporting files
    create_environment_file()
    create_gitignore()
    create_run_script()
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Copy .env file and update with your GitLab token:")
    print("   cp .env .env.local")
    print("   # Edit .env.local with your actual values")
    print("\n2. Run the verification:")
    if os.name == 'nt':
        print("   run_verification.bat --group-id ccm --token YOUR_TOKEN")
    else:
        print("   ./run_verification.sh --group-id ccm --token YOUR_TOKEN")
    print("\n3. Or run directly:")
    print("   .venv/bin/python trivy_verification_automation.py --group-id ccm --token YOUR_TOKEN")
    print("\nFor more options, run:")
    print("   .venv/bin/python trivy_verification_automation.py --help")


if __name__ == "__main__":
    main()
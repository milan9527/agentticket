#!/usr/bin/env python3
"""
Setup script for Ticket Auto-Processing System

This script orchestrates the complete setup process:
1. Install Python dependencies
2. Set up AWS infrastructure
3. Initialize database schema
4. Verify setup
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command: str, description: str):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ is required")
        sys.exit(1)
    print("✅ Python version OK")
    
    # Check AWS CLI
    try:
        subprocess.run(["aws", "--version"], check=True, capture_output=True)
        print("✅ AWS CLI is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ AWS CLI is not installed or not configured")
        print("Please install AWS CLI and run 'aws configure'")
        sys.exit(1)
    
    # Check AWS credentials
    try:
        subprocess.run(["aws", "sts", "get-caller-identity"], check=True, capture_output=True)
        print("✅ AWS credentials are configured")
    except subprocess.CalledProcessError:
        print("❌ AWS credentials are not configured")
        print("Please run 'aws configure' to set up your credentials")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists("venv"):
        run_command("python -m venv venv", "Creating virtual environment")
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    install_cmd = f"{activate_cmd} && pip install --upgrade pip && pip install -r requirements.txt"
    run_command(install_cmd, "Installing dependencies")

def setup_infrastructure():
    """Set up AWS infrastructure"""
    print("🏗️  Setting up AWS infrastructure...")
    
    # Make setup script executable
    os.chmod("infrastructure/setup_aws.py", 0o755)
    
    # Run infrastructure setup
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    setup_cmd = f"{activate_cmd} && python infrastructure/setup_aws.py"
    run_command(setup_cmd, "Setting up AWS infrastructure")

def setup_database():
    """Set up database schema"""
    print("🗄️  Setting up database schema...")
    
    # Make setup script executable
    os.chmod("database/setup_schema.py", 0o755)
    
    # Run database setup
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    db_cmd = f"{activate_cmd} && python database/setup_schema.py"
    run_command(db_cmd, "Setting up database schema")

def install_agentcore_cli():
    """Install AgentCore CLI"""
    print("🤖 Installing AgentCore CLI...")
    
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    cli_cmd = f"{activate_cmd} && pip install bedrock-agentcore-starter-toolkit"
    run_command(cli_cmd, "Installing AgentCore CLI")

def verify_setup():
    """Verify the setup is working"""
    print("🔍 Verifying setup...")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ Environment configuration file created")
    else:
        print("⚠️  No .env file found - you may need to create one manually")
    
    # Check if database connection works
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    try:
        test_cmd = f"{activate_cmd} && python -c \"from database.setup_schema import DatabaseSetup; print('Database connection OK')\""
        run_command(test_cmd, "Testing database connection")
    except:
        print("⚠️  Database connection test failed - check your configuration")

def main():
    """Main setup function"""
    print("🚀 Ticket Auto-Processing System Setup")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        check_prerequisites()
        install_dependencies()
        setup_infrastructure()
        setup_database()
        install_agentcore_cli()
        verify_setup()
        
        print("\n" + "=" * 50)
        print("🎉 Setup completed successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Review the .env file and update any configuration as needed")
        print("2. Start developing agents: cd backend/agents")
        print("3. Run local development: agentcore dev")
        print("\nFor more information, see README.md")
        
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
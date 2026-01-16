#!/usr/bin/env python3
"""
Project Git Updater for services deployed on EC2 Instances

This script:
1. SSH into EC2 instances with the instance_name
2. Checks out the provided project branch if exists for the given project name
3. If branch option is not provided, script will attempt to checkout master branch if exists
4. If neither branch options exist, then throw error
5. Pulls the latest changes from provided or default branch on the given project_name
6. If project name not provided, it prompts to run updates for all projects inside the projects directory
7. The projects that have updates on the deployed branch will be restarted (docker compose down and up) to apply the changes
8. Align with unified resource management script in using instance name instead of sequence number

Usage:
    python update_project_directory.py --instance-name <instance_name> --project <project_name> [--branch <branch_name>]
"""

import boto3
import re
import argparse
import subprocess
import time
from botocore.exceptions import ClientError, NoCredentialsError
import sys
import os

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class ProjectDirectoryUpdater:
    def __init__(self, region_name='af-south-1', aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        """Initialize AWS clients with credentials."""
        try:
            # Create session with credentials if provided
            if aws_access_key_id and aws_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                    region_name=region_name
                )
            else:
                # Use default credential chain
                session = boto3.Session(region_name=region_name)
            
            # Initialize AWS clients
            self.ec2_client = session.client('ec2')
            self.region = region_name
            
            print(f"✅ Connected to AWS in region: {region_name}")
            
        except NoCredentialsError:
            print("❌ AWS credentials not found. Please configure your AWS credentials.")
            raise
        except Exception as e:
            print(f"❌ Error connecting to AWS: {e}")
            raise

    def find_instance_by_name(self, instance_name):
        """Find EC2 instance by instance name."""
        print(f"🔍 Looking for instance: {instance_name}")
        
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [instance_name]},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            if not response['Reservations']:
                print(f"❌ No running EC2 instance found with name: {instance_name}")
                return None
            
            instance = response['Reservations'][0]['Instances'][0]
            instance_info = {
                'id': instance['InstanceId'],
                'name': instance_name,
                'state': instance['State']['Name'],
                'public_ip': instance.get('PublicIpAddress'),
                'private_ip': instance.get('PrivateIpAddress')
            }
            
            # Get Elastic IP if associated
            try:
                addresses = self.ec2_client.describe_addresses()
                for address in addresses['Addresses']:
                    if address.get('InstanceId') == instance['InstanceId']:
                        instance_info['elastic_ip'] = address['PublicIp']
                        break
            except Exception as e:
                print(f"⚠️  Could not check for Elastic IP: {e}")
            
            print(f"✅ Found instance: {instance_info['id']} (State: {instance_info['state']})")
            return instance_info
            
        except Exception as e:
            print(f"❌ Error finding instance: {e}")
            raise

    def check_ssh_key_exists(self, instance_name):
        """Check if SSH key file exists locally."""
        key_file = f"{instance_name}.pem"
        
        # First check in the aws-handler/pems directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up to aws-handler-master directory
        pems_dir = os.path.join(project_dir, "pems")
        key_path = os.path.join(pems_dir, key_file)
        
        if os.path.exists(key_path):
            print(f"✅ Found SSH key: {key_path}")
            return key_path
        
        # Fallback: check in current directory
        key_path = os.path.join(os.getcwd(), key_file)
        if os.path.exists(key_path):
            print(f"✅ Found SSH key: {key_path}")
            return key_path
        
        # If not found in either location
        print(f"❌ SSH key not found in pems/ or current directory: {key_file}")
        print("💡 Make sure you have the key file from the infrastructure creation")
        print(f"   Expected locations:")
        print(f"   - {os.path.join(pems_dir, key_file)}")
        print(f"   - {os.path.join(os.getcwd(), key_file)}")
        return None

    def load_github_token(self, pac_name=None, pac_filename=None):
        """Load GitHub Personal Access Token from file.
        
        Args:
            pac_name: Name to use for constructing token filename (e.g., 'project-name' -> 'project-name-pac.txt')
            pac_filename: Specific PAC filename to use (e.g., 'my-token-pac.txt')
                          If not provided and pac_name is not provided, uses first file in pacs directory.
        
        Returns:
            GitHub token string or None if not found
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up to aws-handler-master directory
        pacs_dir = os.path.join(project_dir, "pacs")
        
        # Determine which token file to use
        if pac_filename:
            # Use specific filename provided
            token_file = os.path.join(pacs_dir, pac_filename)
        elif pac_name:
            # Construct filename from pac_name
            token_file = os.path.join(pacs_dir, f"{pac_name}-pac.txt")
        else:
            # Find first file in pacs directory
            try:
                if not os.path.exists(pacs_dir):
                    print(f"❌ PACs directory not found: {pacs_dir}")
                    return None
                
                pac_files = [f for f in os.listdir(pacs_dir) if os.path.isfile(os.path.join(pacs_dir, f))]
                if not pac_files:
                    print(f"❌ No PAC files found in directory: {pacs_dir}")
                    return None
                
                # Use first file found
                token_file = os.path.join(pacs_dir, pac_files[0])
                print(f"📋 Using first PAC file found: {pac_files[0]}")
            except Exception as e:
                print(f"❌ Error listing PAC files: {e}")
                return None
        
        try:
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                if token:
                    print(f"✅ Loaded GitHub token from: {token_file}")
                    return token
                else:
                    print(f"⚠️  GitHub token file is empty: {token_file}")
                    return None
            else:
                print(f"⚠️  GitHub token file not found: {token_file}")
                return None
        except Exception as e:
            print(f"❌ Error reading GitHub token file: {e}")
            return None

    def test_ssh_connection(self, instance_info, key_path):
        """Test SSH connection to the instance."""
        ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
        if not ip_address:
            print("❌ No public IP address found for the instance")
            return False
        
        print(f"🔗 Testing SSH connection to {ip_address}...")
        
        # Test SSH connection
        ssh_test_command = [
            'ssh', '-i', key_path, '-o', 'ConnectTimeout=10', 
            '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
            f'ec2-user@{ip_address}', 'echo "SSH connection successful"'
        ]
        
        try:
            result = subprocess.run(ssh_test_command, capture_output=True, text=True, 
                                  encoding='utf-8', errors='replace', timeout=30)
            
            if result.returncode == 0:
                print("✅ SSH connection successful!")
                return True
            else:
                print(f"❌ SSH connection failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ SSH connection timed out")
            return False
        except Exception as e:
            print(f"❌ SSH connection error: {e}")
            return False

    def run_ssh_command(self, instance_info, key_path, command, description=""):
        """Run SSH command on the instance."""
        ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
        
        if description:
            print(f"🔧 {description}")
        
        ssh_command = [
            'ssh', '-i', key_path, '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
            f'ec2-user@{ip_address}', command
        ]
        
        try:
            result = subprocess.run(ssh_command, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=120)
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_project_directory_exists(self, instance_info, key_path, project_name):
        """Check if project directory exists on the instance."""
        print(f"📁 Checking if project directory exists: {project_name}")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        check_command = f"test -d {project_path} && echo 'exists' || echo 'not found'"
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            check_command,
            f"Checking project directory: {project_path}"
        )
        
        if success and 'exists' in output:
            print(f"✅ Project directory found: {project_path}")
            return True
        else:
            print(f"❌ Project directory not found: {project_path}")
            print("💡 You may need to run the create_project_repository.py script first")
            return False
    
    def list_all_projects(self, instance_info, key_path):
        """List all projects in the projects directory."""
        print("📁 Listing all projects...")
        
        list_command = "ls -d /home/ec2-user/projects/*/ 2>/dev/null | xargs -n1 basename"
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            list_command,
            "Listing all projects"
        )
        
        if success and output.strip():
            projects = [p.strip() for p in output.strip().split('\n') if p.strip()]
            print(f"✅ Found {len(projects)} project(s):")
            for project in projects:
                print(f"  - {project}")
            return projects
        else:
            print("ℹ️  No projects found in /home/ec2-user/projects/")
            return []

    def checkout_branch(self, instance_info, key_path, project_name, branch_name):
        """Checkout a specific branch, or try master if branch doesn't exist."""
        project_path = f"/home/ec2-user/projects/{project_name}"
        
        # First, fetch to get latest branch information
        fetch_command = f"cd {project_path} && git fetch origin"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            fetch_command,
            f"Fetching latest branch information for {project_name}"
        )
        
        if not success:
            print(f"⚠️  Failed to fetch branches for {project_name}")
        
        # Check if the provided branch exists
        if branch_name:
            check_branch_command = f"cd {project_path} && git ls-remote --heads origin {branch_name} | grep -q {branch_name} && echo 'exists' || echo 'not found'"
            success, output = self.run_ssh_command(
                instance_info, key_path,
                check_branch_command,
                f"Checking if branch '{branch_name}' exists"
            )
            
            if success and 'exists' in output:
                # Checkout the provided branch
                checkout_command = f"cd {project_path} && git checkout {branch_name}"
                success, output = self.run_ssh_command(
                    instance_info, key_path,
                    checkout_command,
                    f"Checking out branch '{branch_name}'"
                )
                if success:
                    print(f"✅ Checked out branch '{branch_name}' for {project_name}")
                    return branch_name
                else:
                    print(f"❌ Failed to checkout branch '{branch_name}': {output}")
                    return None
            else:
                print(f"⚠️  Branch '{branch_name}' not found, trying master...")
        
        # Try master branch
        check_master_command = f"cd {project_path} && git ls-remote --heads origin master | grep -q master && echo 'exists' || echo 'not found'"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            check_master_command,
            f"Checking if branch 'master' exists"
        )
        
        if success and 'exists' in output:
            checkout_command = f"cd {project_path} && git checkout master"
            success, output = self.run_ssh_command(
                instance_info, key_path,
                checkout_command,
                f"Checking out branch 'master'"
            )
            if success:
                print(f"✅ Checked out branch 'master' for {project_name}")
                return 'master'
            else:
                print(f"❌ Failed to checkout branch 'master': {output}")
                return None
        else:
            print(f"❌ Neither branch '{branch_name}' nor 'master' exists for {project_name}")
            return None
    
    def pull_latest_changes(self, instance_info, key_path, project_name, branch_name):
        """Pull latest changes from remote repository."""
        print(f"📥 Pulling latest changes for {project_name} on branch '{branch_name}'...")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        
        # Check current branch
        branch_command = f"cd {project_path} && git branch --show-current"
        success, current_branch = self.run_ssh_command(
            instance_info, key_path,
            branch_command,
            "Checking current branch"
        )
        
        if success:
            print(f"📍 Current branch: {current_branch.strip()}")
        
        # Fetch latest changes
        fetch_command = f"cd {project_path} && git fetch origin"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            fetch_command,
            "Fetching latest changes"
        )
        
        if not success:
            print(f"❌ Failed to fetch changes for {project_name}: {output}")
            return False, False  # (success, has_updates)
        
        # Check if there are updates
        check_updates_command = f"cd {project_path} && git rev-list HEAD..origin/{branch_name} --count"
        success, update_count = self.run_ssh_command(
            instance_info, key_path,
            check_updates_command,
            "Checking for updates"
        )
        
        has_updates = False
        if success:
            try:
                count = int(update_count.strip())
                if count > 0:
                    has_updates = True
                    print(f"📊 Found {count} new commit(s) to pull")
                else:
                    print(f"ℹ️  No new updates available")
            except ValueError:
                pass
        
        # Pull latest changes
        pull_command = f"cd {project_path} && git pull origin {branch_name}"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            pull_command,
            f"Pulling latest changes from '{branch_name}'"
        )
        
        if success:
            print(f"✅ {project_name} updated successfully")
            return True, has_updates
        else:
            print(f"❌ Failed to update {project_name}: {output}")
            return False, False

    def restart_docker_compose(self, instance_info, key_path, project_name):
        """Restart docker compose services for a project."""
        print(f"🔄 Restarting Docker Compose services for {project_name}...")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        
        # Docker compose down
        down_command = f"cd {project_path} && docker-compose down"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            down_command,
            f"Stopping Docker Compose services for {project_name}"
        )
        
        if not success:
            print(f"⚠️  Failed to stop Docker Compose services: {output}")
            return False
        
        # Docker compose up
        up_command = f"cd {project_path} && docker-compose up -d"
        success, output = self.run_ssh_command(
            instance_info, key_path,
            up_command,
            f"Starting Docker Compose services for {project_name}"
        )
        
        if success:
            print(f"✅ Docker Compose services restarted for {project_name}")
            return True
        else:
            print(f"❌ Failed to restart Docker Compose services: {output}")
            return False
    
    def update_project(self, instance_info, key_path, project_name, branch_name=None):
        """Update a single project: checkout branch, pull changes, and restart if needed."""
        print(f"\n{'='*70}")
        print(f"🔄 Updating project: {project_name}")
        print(f"{'='*70}")
        
        # Check if project directory exists
        if not self.check_project_directory_exists(instance_info, key_path, project_name):
            return False
        
        # Checkout branch (provided branch, or master, or error)
        actual_branch = self.checkout_branch(instance_info, key_path, project_name, branch_name)
        if not actual_branch:
            print(f"❌ Failed to checkout branch for {project_name}")
            return False
        
        # Pull latest changes
        success, has_updates = self.pull_latest_changes(instance_info, key_path, project_name, actual_branch)
        
        if not success:
            return False
        
        # Restart docker compose if there were updates
        if has_updates:
            print(f"🔄 Updates detected, restarting Docker Compose services...")
            self.restart_docker_compose(instance_info, key_path, project_name)
        else:
            print(f"ℹ️  No updates, skipping Docker Compose restart")
        
        return True
    
    def update_all_projects(self, instance_info, key_path, branch_name=None):
        """Update all projects in the projects directory."""
        print("🔄 Updating all projects...")
        
        projects = self.list_all_projects(instance_info, key_path)
        
        if not projects:
            print("❌ No projects found to update")
            return False
        
        all_success = True
        updated_projects = []
        failed_projects = []
        
        for project_name in projects:
            if self.update_project(instance_info, key_path, project_name, branch_name):
                updated_projects.append(project_name)
            else:
                failed_projects.append(project_name)
                all_success = False
        
        # Summary
        print(f"\n{'='*70}")
        print("📊 Update Summary")
        print(f"{'='*70}")
        print(f"✅ Successfully updated: {len(updated_projects)} project(s)")
        if updated_projects:
            for project in updated_projects:
                print(f"  - {project}")
        print(f"❌ Failed to update: {len(failed_projects)} project(s)")
        if failed_projects:
            for project in failed_projects:
                print(f"  - {project}")
        print(f"{'='*70}")
        
        return all_success

    def update_instance_projects(self, instance_name, project_name=None, branch_name=None, github_token=None, pac_name=None, pac_filename=None):
        """Update project(s) on the specified instance."""
        print(f"🔄 Updating projects on instance: {instance_name}")
        if project_name:
            print(f"📦 Project: {project_name}")
        if branch_name:
            print(f"🌿 Branch: {branch_name}")
        print("=" * 70)
        
        # Load GitHub token if not provided
        if not github_token:
            github_token = self.load_github_token(pac_name=pac_name, pac_filename=pac_filename)
            if github_token:
                print("🔑 Using GitHub token from file for repository access")
            else:
                print("⚠️  No GitHub token available - repositories must be public")
        
        try:
            # Step 1: Find the instance
            instance_info = self.find_instance_by_name(instance_name)
            if not instance_info:
                print(f"❌ Cannot update projects: Instance not found: {instance_name}")
                return False
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(instance_name)
            if not key_path:
                return False
            
            # Step 3: Test SSH connection
            if not self.test_ssh_connection(instance_info, key_path):
                return False
            
            # Step 4: Update project(s)
            if project_name:
                # Update specific project
                success = self.update_project(instance_info, key_path, project_name, branch_name)
            else:
                # Update all projects
                print("📋 No project name provided, updating all projects...")
                success = self.update_all_projects(instance_info, key_path, branch_name)
            
            if not success:
                print(f"❌ Failed to update projects on instance {instance_name}")
                return False
            
            # Success summary
            print("\n" + "=" * 70)
            print("🎉 PROJECT UPDATE COMPLETE!")
            print("=" * 70)
            print(f"🖥️  Instance ID: {instance_info['id']}")
            print(f"📋 Instance Name: {instance_info['name']}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
            print(f"🔗 SSH Command: ssh -i {key_path} ec2-user@{ip_address}")
            
            print("\n✅ Project(s) have been updated successfully!")
            print("💡 The project(s) are now up to date with the latest changes")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating projects: {e}")
            return False

    def list_all_instances(self, filter_pattern=None):
        """List all EC2 instances with their statuses."""
        print("🔍 Listing EC2 instances...")
        print("=" * 80)
        
        try:
            # Get all instances
            response = self.ec2_client.describe_instances()
            
            all_instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    all_instances.append(instance)
            
            if not all_instances:
                print("ℹ️  No EC2 instances found in this region.")
                return []
            
            # Filter instances if pattern is provided
            if filter_pattern:
                filtered_instances = []
                for instance in all_instances:
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name' and filter_pattern.lower() in tag['Value'].lower():
                                filtered_instances.append(instance)
                                break
                all_instances = filtered_instances
                if not all_instances:
                    print(f"ℹ️  No EC2 instances found matching pattern: {filter_pattern}")
                    return []
            
            # Sort instances by name
            def get_instance_name(instance):
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            return tag['Value']
                return 'Unnamed'
            
            all_instances.sort(key=get_instance_name)
            
            # Print header
            print(f"{'Instance Name':<25} {'Instance ID':<20} {'State':<12} {'Type':<12} {'Public IP':<15} {'Private IP':<15}")
            print("-" * 110)
            
            # Print each instance
            instance_list = []
            for instance in all_instances:
                # Get instance name
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                
                # Get instance details
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                instance_type = instance.get('InstanceType', 'N/A')
                public_ip = instance.get('PublicIpAddress', 'N/A')
                private_ip = instance.get('PrivateIpAddress', 'N/A')
                
                # Print instance info
                print(f"{instance_name:<25} {instance_id:<20} {state:<12} {instance_type:<12} {public_ip:<15} {private_ip:<15}")
                
                instance_list.append({
                    'name': instance_name,
                    'id': instance_id,
                    'state': state,
                    'type': instance_type,
                    'public_ip': public_ip,
                    'private_ip': private_ip
                })
            
            print(f"\nTotal instances: {len(instance_list)}")
            return instance_list
            
        except Exception as e:
            print(f"❌ Error listing instances: {e}")
            return []


def main():
    """Main function to update project repositories."""
    
    parser = argparse.ArgumentParser(description='Update Project Repositories on EC2 Instance(s)')
    parser.add_argument('--instance-name', '-i', type=str, help='EC2 instance name (e.g., jalusi-db-1)')
    parser.add_argument('--project', '-p', type=str, help='Project name to update. If not provided, updates all projects in /home/ec2-user/projects/')
    parser.add_argument('--branch', '-b', type=str, help='Branch name to checkout and pull. If not provided, will try master branch.')
    parser.add_argument('--list', '-l', action='store_true', help='List all available instances')
    parser.add_argument('--filter', '-f', type=str, help='Filter instances by name pattern (used with --list)')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    parser.add_argument('--github-token', '-t', help='GitHub Personal Access Token for private repositories (optional, will load from file if not provided)')
    parser.add_argument('--pac-name', help='PAC name for token file (e.g., jalusi-pac)')
    parser.add_argument('--pac-filename', help='Specific PAC filename (e.g., jalusi-pac.txt)')
    parser.add_argument('--aws-access-key-id', help='AWS Access Key ID')
    parser.add_argument('--aws-secret-access-key', help='AWS Secret Access Key')
    parser.add_argument('--aws-session-token', help='AWS Session Token')
    
    args = parser.parse_args()
    
    # AWS Credentials: Try environment variables first, then credential directories
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN')  # Optional, for temporary credentials
    
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        print("🔑 Using AWS credentials from environment variables")
    else:
        # Try reading from credential directories
        try:
            # Get project root directory (go up from services/manage_project_version_control/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up to aws-handler-master directory
            
            access_key_file = os.path.join(project_dir, 'aws_access_key_id', 'aws-handler.txt')
            secret_key_file = os.path.join(project_dir, 'aws_secret_access_key', 'aws-handler.txt')
            
            if os.path.exists(access_key_file) and os.path.exists(secret_key_file):
                with open(access_key_file, 'r') as f:
                    AWS_ACCESS_KEY_ID = f.read().strip()
                with open(secret_key_file, 'r') as f:
                    AWS_SECRET_ACCESS_KEY = f.read().strip()
                
                if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
                    print("🔑 Using AWS credentials from credential directories")
                else:
                    print("⚠️  Credential files exist but are empty")
            else:
                print("⚠️  Credential files not found in credential directories")
        except Exception as e:
            print(f"⚠️  Error reading credential files: {e}")
    
    print("🔄 Project Repository Updater")
    print("=" * 60)
    print("⚠️  WARNING: This is for development/testing only!")
    print("   Never commit real AWS credentials to version control.")
    print("=" * 60)
    
    # Validate credentials
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("❌ AWS credentials not found!")
        print("   Please set one of the following:")
        print("   1. Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("   2. Credential files: aws_access_key_id/aws-handler.txt and aws_secret_access_key/aws-handler.txt")
        return
    
    try:
        # Initialize project directory updater
        updater = ProjectDirectoryUpdater(
            region_name=args.region,
            aws_access_key_id=args.aws_access_key_id or AWS_ACCESS_KEY_ID,
            aws_secret_access_key=args.aws_secret_access_key or AWS_SECRET_ACCESS_KEY,
            aws_session_token=args.aws_session_token or AWS_SESSION_TOKEN
        )
        
        if args.list:
            # List all instances
            updater.list_all_instances(filter_pattern=args.filter)
        elif args.instance_name:
            # Update projects on specific instance
            success = updater.update_instance_projects(
                instance_name=args.instance_name,
                project_name=args.project,
                branch_name=args.branch,
                github_token=args.github_token,
                pac_name=args.pac_name,
                pac_filename=args.pac_filename
            )
            if success:
                print(f"\n✅ Projects updated successfully on instance {args.instance_name}!")
            else:
                print(f"\n❌ Failed to update projects on instance {args.instance_name}")
                sys.exit(1)
        else:
            # Instance name is required
            print("❌ --instance-name is required (use --list to see available instances)")
            parser.print_help()
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

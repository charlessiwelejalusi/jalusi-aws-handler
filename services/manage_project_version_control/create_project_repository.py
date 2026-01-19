#!/usr/bin/env python3
"""
Project Directory Creator for EC2 Instances

⚠️  WARNING: This is for development/testing purposes only!
    Never commit real AWS credentials to version control.
    Use environment variables or AWS CLI configuration in production.

This script SSH into EC2 instances with the naming pattern:
- <instance_name>

And creates the project directory structure by cloning from GitHub:
- <project_name>

Replace find_instance_by_sequence with find_instance_by_name

load_github_token should set token_file to <project_name>-pac.txt

create_project_repository should use the project_name to create the project directory 

pulling the git repo should use the project_name to pull the repository into the project directory ()
e.g. 
project_path = f"/home/ec2-user/projects/{project_name}"
cd project_path
git clone https://github.com/<github_username>/<project_name>.git .

list_all_sequences should be replaced with list_all_instances

GitHub Repositories:
- https://github.com/<github_username>/<project_name>.git
"""

import boto3
import re
import argparse
import subprocess
import time
import urllib.parse
from botocore.exceptions import ClientError, NoCredentialsError
import sys
import os

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class ProjectDirectoryCreator:
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
            # If pac_name already ends with -pac or .txt, use it as-is, otherwise add -pac.txt
            if pac_name.endswith('-pac.txt') or pac_name.endswith('.txt'):
                token_file = os.path.join(pacs_dir, pac_name)
            elif pac_name.endswith('-pac'):
                token_file = os.path.join(pacs_dir, f"{pac_name}.txt")
            else:
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
                print(f"❌ GitHub token file not found: {token_file}")
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

    def check_git_installation(self, instance_info, key_path):
        """Check if Git is installed."""
        print("📦 Checking Git installation...")
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "git --version",
            "Checking Git version"
        )
        
        if success:
            print(f"✅ Git is installed: {output}")
            return True
        else:
            print("❌ Git is not installed")
            return False

    def install_git(self, instance_info, key_path):
        """Install Git on the instance."""
        print("📦 Installing Git...")
        
        # Update system packages
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "sudo yum update -y",
            "Updating system packages"
        )
        
        if not success:
            print(f"❌ Failed to update packages: {output}")
            return False
        
        # Install Git
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "sudo yum install -y git",
            "Installing Git"
        )
        
        if success:
            print("✅ Git installation completed")
            return True
        else:
            print(f"❌ Failed to install Git: {output}")
            return False

    def configure_git_for_https(self, instance_info, key_path):
        """Configure Git to work with HTTPS and GitHub."""
        print("🔧 Configuring Git for HTTPS access...")
        
        # Configure Git with basic settings
        git_config_commands = [
            "git config --global user.name \"Jalusi Deployer\"",
            "git config --global user.email \"deployer@jalusitech.co.za\"",
            "git config --global credential.helper store"
        ]
        
        for cmd in git_config_commands:
            success, output = self.run_ssh_command(
                instance_info, key_path,
                cmd,
                f"Configuring Git: {cmd}"
            )
            if not success:
                print(f"⚠️  Warning: Git config command failed: {output}")
        
        print("✅ Git HTTPS configuration completed")
        print("⚠️  Note: For private repositories, you may need to provide credentials during cloning")
        return True

    def create_project_repository(self, instance_info, key_path, project_name):
        """Create the project directory structure."""
        print(f"📁 Creating project directory structure for: {project_name}")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        
        # Clean up existing directory if it exists
        success, output = self.run_ssh_command(
            instance_info, key_path,
            f"rm -rf {project_path}",
            f"Cleaning up existing directory: {project_path}"
        )
        if not success:
            print(f"⚠️  Warning: Cleanup command failed: {output}")
        
        # Create base directory
        success, output = self.run_ssh_command(
            instance_info, key_path,
            f"mkdir -p {project_path} && cd {project_path} && pwd",
            f"Creating project directory: {project_path}"
        )
        
        if not success:
            print(f"❌ Failed to create project directory: {output}")
            return False
        
        print(f"✅ Project directory created: {output}")
        return True

    def clone_repository(self, instance_info, key_path, project_name, github_username, github_token=None):
        """Clone a repository into the project directory."""
        print(f"📥 Cloning {project_name} repository...")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        repo_url = f"https://github.com/{github_username}/{project_name}.git"
        
        # If GitHub token is provided, use it in the URL for authentication
        if github_token:
            # Use token in URL: https://token@github.com/username/repo.git
            # URL encode the token to handle special characters
            encoded_token = urllib.parse.quote(github_token, safe='')
            auth_url = repo_url.replace('https://', f'https://{encoded_token}@')
            print("🔑 Using GitHub token for authentication")
        else:
            auth_url = repo_url
            print("⚠️  No GitHub token provided - will attempt public repository access")
        
        # Clone into the project directory using dot (.) to clone directly into the directory
        # Use GIT_TERMINAL_PROMPT=0 to prevent interactive prompts
        clone_command = f"cd {project_path} && GIT_TERMINAL_PROMPT=0 git clone {auth_url} . 2>&1"
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            clone_command,
            f"Cloning {project_name} repository into {project_path}"
        )
        
        if success:
            print(f"✅ {project_name} cloned successfully into {project_path}")
            return True
        else:
            print(f"❌ Failed to clone {project_name}: {output}")
            if "Authentication failed" in output or "Permission denied" in output or "could not read Username" in output:
                print("💡 This might be a private repository. Consider providing a GitHub Personal Access Token.")
                print("💡 You can provide it via:")
                print("   1. --github-token <token>")
                print("   2. --pac-name <name> (loads from pacs/<name>-pac.txt)")
                print("   3. --pac-filename <filename> (loads from pacs/<filename>)")
            elif "Repository not found" in output or "404" in output:
                print("💡 Repository might not exist or you don't have access to it.")
                print(f"💡 Check: https://github.com/{github_username}/{project_name}")
            return False

    def setup_project_structure(self, instance_info, key_path, project_name, github_username, github_token=None):
        """Set up the complete project structure."""
        print(f"🏗️  Setting up project structure for: {project_name}")
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        
        # Clone the repository into the project directory
        if not self.clone_repository(instance_info, key_path, project_name, github_username, github_token):
            return False
        
        # Verify directory structure
        success, output = self.run_ssh_command(
            instance_info, key_path,
            f"cd {project_path} && ls -la",
            "Verifying directory structure"
        )
        
        if success:
            print("📋 Directory structure:")
            print(output)
            return True
        else:
            print(f"❌ Failed to verify directory structure: {output}")
            return False

    def create_project_repository_structure(self, instance_name, project_name, github_username, github_token=None, pac_name=None, pac_filename=None):
        """Create complete project directory structure on the specified instance."""
        print(f"📁 Creating project directory structure")
        print("=" * 70)
        print(f"Instance: {instance_name}")
        print(f"Project: {project_name}")
        print(f"GitHub User: {github_username}")
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
                print(f"❌ Cannot create project directory: Instance not found: {instance_name}")
                return False
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(instance_name)
            if not key_path:
                return False
            
            # Step 3: Test SSH connection
            if not self.test_ssh_connection(instance_info, key_path):
                return False
            
            # Step 4: Check Git installation
            git_installed = self.check_git_installation(instance_info, key_path)
            if not git_installed:
                print("📦 Installing Git...")
                if not self.install_git(instance_info, key_path):
                    return False
            
            # Step 5: Configure Git for HTTPS access
            if not self.configure_git_for_https(instance_info, key_path):
                return False
            
            # Step 6: Create project directory
            if not self.create_project_repository(instance_info, key_path, project_name):
                return False
            
            # Step 7: Set up project structure
            if not self.setup_project_structure(instance_info, key_path, project_name, github_username, github_token):
                return False
            
            # Step 8: Final verification
            print("🔍 Final verification...")
            
            project_path = f"/home/ec2-user/projects/{project_name}"
            success, output = self.run_ssh_command(
                instance_info, key_path,
                f"cd {project_path} && find . -maxdepth 1 -type f -o -type d | sort",
                "Final directory structure verification"
            )
            
            if not success:
                print(f"❌ Final verification failed: {output}")
                return False
            
            print("📋 Final directory structure:")
            print(output)
            
            # Success summary
            print("\n" + "=" * 70)
            print("🎉 PROJECT DIRECTORY CREATION COMPLETE!")
            print("=" * 70)
            print(f"🖥️  Instance ID: {instance_info['id']}")
            print(f"📋 Instance Name: {instance_info['name']}")
            print(f"📁 Project Name: {project_name}")
            print(f"📂 Project Path: {project_path}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
            print(f"🔗 SSH Command: ssh -i {key_path} ec2-user@{ip_address}")
            
            print(f"\n📁 Project Structure Created:")
            print(f"{project_path}/")
            print(f"└── (repository contents from https://github.com/{github_username}/{project_name}.git)")
            
            print("\n✅ Project directory is ready for development!")
            print("💡 You can now SSH into the instance and start working on the project")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating project directory structure: {e}")
            return False

    def list_all_instances(self, filter_pattern=None):
        """List all available EC2 instances."""
        print("🔍 Scanning for all EC2 instances...")
        
        instances = []
        
        try:
            response = self.ec2_client.describe_instances()
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                instance_name = tag['Value']
                                # Apply filter if provided
                                if filter_pattern and filter_pattern.lower() not in instance_name.lower():
                                    continue
                                
                                    instances.append({
                                        'id': instance['InstanceId'],
                                    'name': instance_name,
                                        'state': instance['State']['Name'],
                                        'public_ip': instance.get('PublicIpAddress'),
                                        'private_ip': instance.get('PrivateIpAddress')
                                    })
                                break
            
            if instances:
                print("📊 Found EC2 instances:")
                for instance in sorted(instances, key=lambda x: x['name']):
                    status_emoji = "🟢" if instance['state'] == 'running' else "🔴" if instance['state'] == 'stopped' else "🟡"
                    print(f"  {status_emoji} {instance['name']} (ID: {instance['id']}, State: {instance['state']})")
                
                running_instances = [inst['name'] for inst in instances if inst['state'] == 'running']
                if running_instances:
                    print("\n📊 Available running instances:")
                    for name in sorted(running_instances):
                        print(f"  - {name}")
            else:
                print("ℹ️  No EC2 instances found")
                if filter_pattern:
                    print(f"   (filtered by: {filter_pattern})")
            
            return sorted([inst['name'] for inst in instances])
            
        except Exception as e:
            print(f"❌ Error scanning instances: {e}")
            raise


def main():
    """Main function to create project directory structure."""
    
    parser = argparse.ArgumentParser(description='Create Project Directory Structure on EC2 Instance')
    parser.add_argument('--instance_name', '-i', type=str, help='Instance name (e.g., jalusi-db-1)')
    parser.add_argument('--project_name', '-p', type=str, help='Project name (e.g., test-project)')
    parser.add_argument('--github_username', '-u', type=str, help='GitHub username (e.g., charlessiwele)')
    parser.add_argument('--list', '-l', action='store_true', help='List all available instances')
    parser.add_argument('--filter', '-f', type=str, help='Filter instances by name pattern (for --list)')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    parser.add_argument('--github-token', '-t', help='GitHub Personal Access Token for private repositories (optional, will load from file if not provided)')
    parser.add_argument('--pac-name', type=str, help='PAC name to construct token filename (e.g., project-name -> project-name-pac.txt)')
    parser.add_argument('--pac-filename', type=str, help='Specific PAC filename to use (e.g., my-token-pac.txt). If not provided and pac-name not provided, uses first file in pacs directory.')
    
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
    
    print("📁 Project Directory Creator for EC2 Instances")
    print("=" * 60)
    print("⚠️  WARNING: This is for development/testing only!")
    print("   Never commit real AWS credentials to version control.")
    print("=" * 60)
    
    # Validate credentials
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("❌ AWS credentials not found. Please set environment variables or provide credential files.")
        return
    
    try:
        # Initialize project directory creator
        creator = ProjectDirectoryCreator(
            region_name=args.region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN
        )
        
        if args.list:
            # List all instances
            creator.list_all_instances(filter_pattern=args.filter)
        elif args.instance_name and args.project_name and args.github_username:
            # Create project directory structure
            docker_compose_project_names = args.project_name.split(',')
            for docker_compose_project_name in docker_compose_project_names:
                print(f"📁 Creating project directory structure for {docker_compose_project_name}")
                success = creator.create_project_repository_structure(
                    args.instance_name, 
                    docker_compose_project_name, 
                    args.github_username,
                    args.github_token,
                    pac_name=args.pac_name,
                    pac_filename=args.pac_filename
                )
                if not success:
                    print(f"❌ Failed to create project directory structure for {docker_compose_project_name}")
                    break
                print(f"✅ Project directory structure created successfully for {docker_compose_project_name}")
        else:
            # Show usage
            print("❌ Please specify either --list or provide --instance_name, --project_name, and --github_username")
            print("\nExamples:")
            print("  python create_project_repository.py --list")
            print("  python create_project_repository.py --list --filter jalusi")
            print("  python create_project_repository.py --instance_name jalusi-db-1 --project_name test-project --github_username charlessiwele")
            print("  python create_project_repository.py -i jalusi-db-1 -p test-project -u charlessiwele --github-token YOUR_TOKEN_HERE")
            print("  python create_project_repository.py -i jalusi-db-1 -p test-project -u charlessiwele --pac-name myproject")
            print("  python create_project_repository.py -i jalusi-db-1 -p test-project -u charlessiwele --pac-filename my-token-pac.txt")
            print("\n💡 Note: GitHub token will be automatically loaded:")
            print("   - From pacs/<pac-name>-pac.txt if --pac-name is provided")
            print("   - From pacs/<pac-filename> if --pac-filename is provided")
            print("   - From first file in pacs/ directory if neither is provided")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Project Directory Updater for Learnly Production EC2 Instances

⚠️  WARNING: This is for development/testing purposes only!
    Never commit real AWS credentials to version control.
    Use environment variables or AWS CLI configuration in production.

This script SSH into EC2 instances with the naming pattern:
- learnly-prod-<sequence_number>

And pulls the latest master from remote repositories:
- learnly-project (main project)
- learnly-api (submodule)
- learnly-web (submodule)

GitHub Repositories:
- https://github.com/charlessiwele/learnly-project.git
- https://github.com/charlessiwele/learnly-api.git
- https://github.com/charlessiwele/learnly-web.git

Usage:
- With sequence number: Updates specific instance
- Without sequence number: Updates all running instances
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
            
            # GitHub repository URLs (using HTTPS format for automation)
            # Note: For private repositories, you'll need to provide a Personal Access Token
            self.repositories = {
                'learnly-project': 'https://github.com/charlessiwele/learnly-project.git',
                'learnly-api': 'https://github.com/charlessiwele/learnly-api.git',
                'learnly-web': 'https://github.com/charlessiwele/learnly-web.git'
            }
            
            print(f"✅ Connected to AWS in region: {region_name}")
            
        except NoCredentialsError:
            print("❌ AWS credentials not found. Please configure your AWS credentials.")
            raise
        except Exception as e:
            print(f"❌ Error connecting to AWS: {e}")
            raise

    def find_instance_by_sequence(self, sequence_number):
        """Find EC2 instance by sequence number."""
        instance_name = f"learnly-prod-{sequence_number}"
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
                'sequence': sequence_number,
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

    def check_ssh_key_exists(self, sequence_number):
        """Check if SSH key file exists locally."""
        key_file = f"learnly-prod-{sequence_number}.pem"
        
        # First check in the aws-handler/pems directory
        aws_handler_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        pems_dir = os.path.join(aws_handler_dir, "pems")
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
        print(f"❌ SSH key not found in aws-handler/pems/ or current directory: {key_file}")
        print("💡 Make sure you have the key file from the infrastructure creation")
        print(f"   Expected locations:")
        print(f"   - {os.path.join(pems_dir, key_file)}")
        print(f"   - {os.path.join(os.getcwd(), key_file)}")
        return None

    def load_github_token(self):
        """Load GitHub Personal Access Token from file."""
        # Path to the token file
        aws_handler_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        pacs_dir = os.path.join(aws_handler_dir, "pacs")
        token_file = os.path.join(pacs_dir, "learnly-pac.txt")
        
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

    def check_project_directories_exist(self, instance_info, key_path):
        """Check if project directories exist on the instance."""
        print("📁 Checking if project directories exist...")
        
        check_command = "ls -la ~/learnly-project/"
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            check_command,
            "Checking project directories"
        )
        
        if success:
            print("✅ Project directories found:")
            print(output)
            return True
        else:
            print("❌ Project directories not found")
            print("💡 You may need to run the create_project_repository.py script first")
            return False

    def pull_latest_changes(self, instance_info, key_path, repo_name, repo_path, github_token=None):
        """Pull latest changes from remote repository."""
        print(f"📥 Pulling latest changes for {repo_name}...")
        
        # Navigate to the repository directory
        cd_command = f"cd ~/learnly-project/{repo_path}"
        
        # Check current branch
        branch_command = "git branch --show-current"
        
        # Fetch latest changes
        fetch_command = "git fetch origin"
        
        # Pull latest changes from master
        pull_command = "git pull origin master"
        
        # Execute commands in sequence
        command = cd_command + " && " + branch_command + " && " + fetch_command + " && " + pull_command
        msg = "Checking current branch, Fetching latest changes, Pulling latest master"
        commands = [
            (command, f"Navigating to {repo_name} directory. {msg}"),
        ]
        for command, description in commands:
            success, output = self.run_ssh_command(
                instance_info, key_path,
                command,
                description
            )
            
            if not success:
                print(f"❌ Failed to update {repo_name}: {output}")
                return False
            
            if "branch" in description.lower():
                print(f"📍 Current branch: {output}")
            elif "pull" in description.lower():
                print(f"✅ {repo_name} updated successfully")
        
        return True

    def update_all_repositories(self, instance_info, key_path, github_token=None):
        """Update all repositories on the instance."""
        print("🔄 Updating all repositories...")
        
        repositories_to_update = [
            ('learnly-project', 'learnly-project'),
            ('learnly-api', 'learnly-api'),
            ('learnly-web', 'learnly-web')
        ]
        
        all_success = True
        
        for repo_name, repo_path in repositories_to_update:
            if not self.pull_latest_changes(instance_info, key_path, repo_name, repo_path, github_token):
                all_success = False
                print(f"⚠️  Failed to update {repo_name}, continuing with others...")
        
        return all_success

    def update_project_repositories(self, sequence_number, github_token=None):
        """Update project repositories on the specified instance."""
        print(f"🔄 Updating project repositories for sequence: {sequence_number}")
        print("=" * 70)
        
        # Load GitHub token if not provided
        if not github_token:
            github_token = self.load_github_token()
            if github_token:
                print("🔑 Using GitHub token from file for repository access")
            else:
                print("⚠️  No GitHub token available - repositories must be public")
        
        try:
            # Step 1: Find the instance
            instance_info = self.find_instance_by_sequence(sequence_number)
            if not instance_info:
                print(f"❌ Cannot update repositories: Instance not found for sequence {sequence_number}")
                return False
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(sequence_number)
            if not key_path:
                return False
            
            # Step 3: Test SSH connection
            if not self.test_ssh_connection(instance_info, key_path):
                return False
            
            # Step 4: Check if project directories exist
            if not self.check_project_directories_exist(instance_info, key_path):
                print(f"❌ Project directories not found for sequence {sequence_number}")
                print("💡 Please run create_project_repository.py first to set up the initial structure")
                return False
            
            # Step 5: Update all repositories
            if not self.update_all_repositories(instance_info, key_path, github_token):
                print(f"❌ Failed to update some repositories for sequence {sequence_number}")
                return False
            
            # Success summary
            print("\n" + "=" * 70)
            print("🎉 PROJECT REPOSITORIES UPDATE COMPLETE!")
            print("=" * 70)
            print(f"📋 Sequence Number: {sequence_number}")
            print(f"🖥️  Instance ID: {instance_info['id']}")
            print(f"📋 Instance Name: {instance_info['name']}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
            print(f"🔗 SSH Command: ssh -i {key_path} ec2-user@{ip_address}")
            
            print("\n✅ All repositories have been updated to latest master!")
            print("💡 The project is now up to date with the latest changes")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating project repositories: {e}")
            return False

    def update_all_instances(self, github_token=None):
        """Update repositories on all running instances."""
        print("🔄 Updating repositories on all running instances...")
        print("=" * 70)
        
        # Load GitHub token if not provided
        if not github_token:
            github_token = self.load_github_token()
            if github_token:
                print("🔑 Using GitHub token from file for repository access")
            else:
                print("⚠️  No GitHub token available - repositories must be public")
        
        # Get all running instances
        instances = self.get_all_running_instances()
        
        if not instances:
            print("❌ No running instances found")
            return False
        
        print(f"📊 Found {len(instances)} running instances to update")
        
        success_count = 0
        failed_instances = []
        
        for instance in instances:
            sequence_number = instance['sequence']
            print(f"\n🔄 Updating instance {sequence_number} ({instance['name']})...")
            
            try:
                if self.update_project_repositories(sequence_number, github_token):
                    success_count += 1
                    print(f"✅ Instance {sequence_number} updated successfully")
                else:
                    failed_instances.append(sequence_number)
                    print(f"❌ Instance {sequence_number} update failed")
            except Exception as e:
                failed_instances.append(sequence_number)
                print(f"❌ Error updating instance {sequence_number}: {e}")
        
        # Summary
        print("\n" + "=" * 70)
        print("🎉 BULK UPDATE COMPLETE!")
        print("=" * 70)
        print(f"📊 Total instances: {len(instances)}")
        print(f"✅ Successful updates: {success_count}")
        print(f"❌ Failed updates: {len(failed_instances)}")
        
        if failed_instances:
            print(f"📋 Failed instances: {', '.join(map(str, failed_instances))}")
        
        print("=" * 70)
        
        return len(failed_instances) == 0

    def get_all_running_instances(self):
        """Get all running instances that follow the naming convention."""
        print("🔍 Scanning for all running learnly-prod instances...")
        
        instances = []
        pattern = r'learnly-prod-(\d+)'
        
        try:
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                match = re.search(pattern, tag['Value'])
                                if match:
                                    instances.append({
                                        'id': instance['InstanceId'],
                                        'name': tag['Value'],
                                        'state': instance['State']['Name'],
                                        'sequence': int(match.group(1)),
                                        'public_ip': instance.get('PublicIpAddress'),
                                        'private_ip': instance.get('PrivateIpAddress')
                                    })
                                    break
            
            # Sort by sequence number
            instances.sort(key=lambda x: x['sequence'])
            
            if instances:
                print(f"📊 Found {len(instances)} running instances:")
                for instance in instances:
                    print(f"  🟢 {instance['name']} (ID: {instance['id']}, Sequence: {instance['sequence']})")
            else:
                print("ℹ️  No running learnly-prod instances found")
            
            return instances
            
        except Exception as e:
            print(f"❌ Error scanning instances: {e}")
            return []

    def list_all_sequences(self):
        """List all available sequence numbers."""
        print("🔍 Scanning for all learnly-prod instances...")
        
        instances = []
        pattern = r'learnly-prod-(\d+)'
        
        try:
            response = self.ec2_client.describe_instances()
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                match = re.search(pattern, tag['Value'])
                                if match:
                                    instances.append({
                                        'id': instance['InstanceId'],
                                        'name': tag['Value'],
                                        'state': instance['State']['Name'],
                                        'sequence': int(match.group(1)),
                                        'public_ip': instance.get('PublicIpAddress'),
                                        'private_ip': instance.get('PrivateIpAddress')
                                    })
            
            if instances:
                print("📊 Found learnly-prod instances:")
                for instance in sorted(instances, key=lambda x: x['sequence']):
                    status_emoji = "🟢" if instance['state'] == 'running' else "🔴" if instance['state'] == 'stopped' else "🟡"
                    print(f"  {status_emoji} {instance['name']} (ID: {instance['id']}, State: {instance['state']})")
                
                print("\n📊 Available sequence numbers:")
                sequences = [instance['sequence'] for instance in instances if instance['state'] == 'running']
                for seq in sorted(sequences):
                    print(f"  - learnly-prod-{seq}")
            else:
                print("ℹ️  No learnly-prod instances found")
            
            return sorted(sequences)
            
        except Exception as e:
            print(f"❌ Error scanning instances: {e}")
            raise


def main():
    """Main function to update project repositories."""
    
    parser = argparse.ArgumentParser(description='Update Project Repositories on Learnly Production EC2 Instance(s)')
    parser.add_argument('--sequence', '-s', type=int, help='Sequence number to update (e.g., 1 for learnly-prod-1). If not provided, updates all running instances.')
    parser.add_argument('--list', '-l', action='store_true', help='List all available sequence numbers')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    parser.add_argument('--github-token', '-t', help='GitHub Personal Access Token for private repositories (optional, will load from file if not provided)')
    
    args = parser.parse_args()
    
    # ⚠️  WARNING: Replace these with your actual AWS credentials
    # ⚠️  NEVER commit real credentials to version control!
    # Read credentials from files
    try:
        with open('/home/charles/Documents/projects/aws-handler-master/aws_access_key_id/aws-handler.txt', 'r') as f:
            AWS_ACCESS_KEY_ID = f.read().strip()
        with open('/home/charles/Documents/projects/aws-handler-master/aws_secret_access_key/aws-handler.txt', 'r') as f:
            AWS_SECRET_ACCESS_KEY = f.read().strip()
    except FileNotFoundError as e:
        print(f"❌ Error: Credential file not found: {e}")
        AWS_ACCESS_KEY_ID = None
        AWS_SECRET_ACCESS_KEY = None
    AWS_SESSION_TOKEN = None  # Optional, for temporary credentials
    
    print("🔄 Project Repository Updater for Learnly Production")
    print("=" * 60)
    print("⚠️  WARNING: This is for development/testing only!")
    print("   Never commit real AWS credentials to version control.")
    print("=" * 60)
    
    # Check if credentials are set
    if AWS_ACCESS_KEY_ID == "YOUR_ACCESS_KEY_ID_HERE":
        print("❌ Please update the credentials in this file before running.")
        print("   Replace 'YOUR_ACCESS_KEY_ID_HERE' with your actual AWS Access Key ID")
        print("   Replace 'YOUR_SECRET_ACCESS_KEY_HERE' with your actual AWS Secret Access Key")
        return
    
    try:
        # Initialize project directory updater
        updater = ProjectDirectoryUpdater(
            region_name=args.region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN
        )
        
        if args.list:
            # List all sequences
            updater.list_all_sequences()
        elif args.sequence is not None:
            # Update specific sequence
            print(f"🔄 Updating repositories for sequence: {args.sequence}")
            success = updater.update_project_repositories(args.sequence, args.github_token)
            if success:
                print(f"\n✅ Repositories updated successfully for sequence {args.sequence}!")
            else:
                print(f"\n❌ Failed to update repositories for sequence {args.sequence}")
        else:
            # Update all running instances
            print("🔄 Updating repositories on all running instances...")
            success = updater.update_all_instances(args.github_token)
            if success:
                print(f"\n✅ All repositories updated successfully!")
            else:
                print(f"\n❌ Some repositories failed to update")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()

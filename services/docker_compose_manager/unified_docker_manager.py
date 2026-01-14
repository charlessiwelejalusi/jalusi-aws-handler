#!/usr/bin/env python3
"""
Unified Docker and Docker Compose Manager for Generic EC2 Instances

⚠️  WARNING: This is for development/testing purposes only!
    Never commit real AWS credentials to version control.
    Use environment variables or AWS CLI configuration in production.

This script provides comprehensive Docker and Docker Compose management functionality:

1. Docker Environment Management:
   - Build and setup Docker environment on EC2 instances
   - Install Docker and Docker Compose
   - Configure Docker daemon settings

2. Docker Compose Operations:
   - Start/Stop/Restart services
   - Build and deploy services
   - View logs and status
   - Scale services

3. Docker Cleanup and Maintenance:
   - Clean up unused containers, images, volumes
   - Monitor disk usage
   - Prune Docker system resources

4. Service Management:
   - Manage individual services
   - View service status
   - Execute commands in containers

Usage Examples:
    # Environment setup
    python unified_docker_manager.py --action build-env --instance_name jalusi-db-1
    
    # Docker Compose operations
    python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project
    
    # Service-specific operations
    python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project --service api
    python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --service db
    
    # Cleanup operations
    python unified_docker_manager.py --action cleanup --instance_name jalusi-db-1
    python unified_docker_manager.py --action cleanup --instance_name jalusi-db-1 --aggressive
    
    # System information
    python unified_docker_manager.py --action info --instance_name jalusi-db-1
    python unified_docker_manager.py --action disk-usage --instance_name jalusi-db-1
"""
# 

import boto3
import re
import argparse
import subprocess
import time
import sys
import os
from botocore.exceptions import ClientError, NoCredentialsError

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class UnifiedDockerManager:
    """Unified Docker and Docker Compose management for EC2 instances."""
    
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
        pems_dir = os.path.join(project_dir, 'pems')
        key_path = os.path.join(pems_dir, key_file)
        
        if os.path.exists(key_path):
            print(f"✅ Found SSH key: {key_path}")
            return key_path
        
        # Check in current directory
        if os.path.exists(key_file):
            print(f"✅ Found SSH key: {key_file}")
            return key_file
        
        # Check in parent directories
        for i in range(1, 5):  # Check up to 5 levels up
            parent_dir = os.path.join(os.path.dirname(__file__), *(['..'] * i))
            potential_path = os.path.join(parent_dir, 'pems', key_file)
            if os.path.exists(potential_path):
                print(f"✅ Found SSH key: {potential_path}")
                return potential_path
        
        print(f"❌ SSH key file not found: {key_file}")
        print("💡 Please ensure the key file exists in one of these locations:")
        print(f"   - {pems_dir}/{key_file}")
        print(f"   - {os.getcwd()}/{key_file}")
        print(f"   - Any parent directory's pems/{key_file}")
        return None

    def execute_ssh_command(self, instance_info, key_path, command, timeout=300):
        """Execute SSH command on EC2 instance."""
        if not instance_info or not key_path:
            return False
        
        # Use Elastic IP if available, otherwise use public IP
        ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
        if not ip_address:
            print("❌ No IP address available for SSH connection")
            return False
        
        ssh_command = [
            'ssh',
            '-i', key_path,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'ConnectTimeout=30',
            f'ec2-user@{ip_address}',
            command
        ]
        
        print(f"🔗 Executing SSH command on {ip_address}: {command}")
        
        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                print("✅ SSH command executed successfully")
                if result.stdout.strip():
                    print("📤 Output:")
                    print(result.stdout)
                return True, result.stdout, result.stderr
            else:
                print(f"❌ SSH command failed with return code: {result.returncode}")
                if result.stderr.strip():
                    print("📤 Error output:")
                    print(result.stderr)
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            print(f"❌ SSH command timed out after {timeout} seconds")
            return False, "", "Command timed out"
        except Exception as e:
            print(f"❌ Error executing SSH command: {e}")
            return False, "", str(e)

    def build_docker_environment(self, instance_name):
        """Build and setup Docker environment on EC2 instance."""
        print(f"🔧 Building Docker environment for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Docker installation commands
        docker_install_commands = [
            # Update system
            "sudo yum update -y",
            
            # Install Docker
            "sudo yum install -y docker",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
            "sudo usermod -a -G docker ec2-user",
            
            # Install Docker Compose
            "sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose",
            "sudo chmod +x /usr/local/bin/docker-compose",
            
            # Create symbolic link for docker-compose
            "sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose",
            
            # Configure Docker daemon for better performance
            "sudo mkdir -p /etc/docker",
            "echo '{\"log-driver\": \"json-file\", \"log-opts\": {\"max-size\": \"10m\", \"max-file\": \"3\"}}' | sudo tee /etc/docker/daemon.json",
            "sudo systemctl restart docker",
            
            # Verify installations
            "docker --version",
            "docker-compose --version",
            "docker system info"
        ]
        
        print("🚀 Installing Docker and Docker Compose...")
        
        for i, command in enumerate(docker_install_commands, 1):
            print(f"📋 Step {i}/{len(docker_install_commands)}: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if not success:
                print(f"❌ Failed at step {i}: {command}")
                return False
            
            # Add delay between commands to ensure proper execution
            time.sleep(2)
        
        print("✅ Docker environment setup completed successfully!")
        return True

    def docker_compose_up(self, instance_name, project_name, build=False, service=None):
        """Start Docker Compose services."""
        print(f"🚀 Starting Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Navigate to project directory and run docker-compose up
        project_path = f"/home/ec2-user/projects/{project_name}"
        command = f"cd {project_path} && docker-compose up -d"
        if build:
            command += " --build"
        if service:
            command += f" {service}"
        
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
        
        if success:
            print("✅ Docker Compose services started successfully!")
            return True
        else:
            print("❌ Failed to start Docker Compose services")
            return False

    def docker_compose_down(self, instance_name, project_name, service=None):
        """Stop Docker Compose services."""
        print(f"🛑 Stopping Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        command = f"cd {project_path} && docker-compose down"
        if service:
            command += f" {service}"
        
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
        
        if success:
            print("✅ Docker Compose services stopped successfully!")
            return True
        else:
            print("❌ Failed to stop Docker Compose services")
            return False

    def docker_compose_restart(self, instance_name, project_name, service=None):
        """Restart Docker Compose services."""
        print(f"🔄 Restarting Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        if service:
            command = f"cd {project_path} && docker-compose restart {service}"
        else:
            command = f"cd {project_path} && docker-compose restart"
        
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
        
        if success:
            print("✅ Docker Compose services restarted successfully!")
            return True
        else:
            print("❌ Failed to restart Docker Compose services")
            return False

    def docker_compose_logs(self, instance_name, project_name, service=None, follow=False, tail=100):
        """View Docker Compose logs with streaming support."""
        print(f"📋 Viewing Docker Compose logs for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        # Build command - add -f flag only if following
        if follow:
            command = f"cd {project_path} && docker-compose logs -f --tail={tail}"
        else:
            command = f"cd {project_path} && docker-compose logs --tail={tail}"
        
        if service:
            command += f" {service}"
        
        if follow:
            # For streaming logs, we need to execute without capture_output
            # Use the IP address directly
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            if not ip_address:
                print("❌ No IP address available for SSH connection")
                return False
            
            ssh_command = [
                'ssh',
                '-i', key_path,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=30',
                f'ec2-user@{ip_address}',
                command
            ]
            
            print(f"🔗 Streaming logs from {ip_address} (Press Ctrl+C to stop)...")
            try:
                # Execute in real-time without capturing output
                subprocess.run(ssh_command, timeout=None)
                return True
            except KeyboardInterrupt:
                print("\n⏹️  Log streaming stopped by user")
                return True
            except Exception as e:
                print(f"❌ Error streaming logs: {e}")
                return False
        else:
            # For non-streaming, use the existing execute_ssh_command
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if success:
                print("📤 Logs:")
                print(stdout)
                return True
            else:
                print("❌ Failed to retrieve logs")
                return False

    def docker_compose_status(self, instance_name, project_name):
        """Show Docker Compose service status."""
        print(f"📊 Checking Docker Compose status for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        project_path = f"/home/ec2-user/projects/{project_name}"
        commands = [
            f"cd {project_path} && docker-compose ps",
            f"cd {project_path} && docker-compose top",
            "docker system df"
        ]
        
        for command in commands:
            print(f"🔍 Executing: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if success:
                print("📤 Output:")
                print(stdout)
            else:
                print(f"❌ Failed to execute: {command}")
        
        return True

    def docker_cleanup(self, instance_name, aggressive=False):
        """Clean up Docker resources."""
        print(f"🧹 Cleaning up Docker resources for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Show disk usage before cleanup
        print("📊 Disk usage before cleanup:")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "df -h")
        if success:
            print(stdout)
        
        # Docker system info
        print("🐳 Docker system info:")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "docker system df")
        if success:
            print(stdout)
        
        # Cleanup commands
        cleanup_commands = [
            # Stop all containers
            "docker stop $(docker ps -aq) 2>/dev/null || true",
            
            # Remove stopped containers
            "docker container prune -f",
            
            # Remove unused images
            "docker image prune -f",
            
            # Remove unused volumes
            "docker volume prune -f",
            
            # Remove unused networks
            "docker network prune -f",
            
            # System prune (removes all unused data)
            "docker system prune -f"
        ]
        
        if aggressive:
            cleanup_commands.extend([
                # Remove all containers (including running ones)
                "docker rm -f $(docker ps -aq) 2>/dev/null || true",
                
                # Remove all images
                "docker rmi -f $(docker images -aq) 2>/dev/null || true",
                
                # Remove all volumes
                "docker volume rm $(docker volume ls -q) 2>/dev/null || true",
                
                # Remove all networks (except default ones)
                "docker network rm $(docker network ls -q | grep -v bridge | grep -v host | grep -v none) 2>/dev/null || true"
            ])
        
        print("🧹 Executing cleanup commands...")
        for command in cleanup_commands:
            print(f"🔧 Executing: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if success:
                print("✅ Cleanup command executed successfully")
            else:
                print(f"⚠️  Cleanup command had issues: {stderr}")
        
        # Show disk usage after cleanup
        print("📊 Disk usage after cleanup:")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "df -h")
        if success:
            print(stdout)
        
        print("✅ Docker cleanup completed!")
        return True

    def docker_info(self, instance_name):
        """Show Docker system information."""
        print(f"ℹ️  Getting Docker system information for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        info_commands = [
            "docker --version",
            "docker-compose --version",
            "docker system info",
            "docker system df",
            "docker ps -a",
            "docker images",
            "docker volume ls",
            "docker network ls"
        ]
        
        for command in info_commands:
            print(f"🔍 {command}:")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if success:
                print(stdout)
            else:
                print(f"❌ Failed: {stderr}")
            print("-" * 50)
        
        return True

    def disk_usage(self, instance_name):
        """Show disk usage information."""
        print(f"💾 Checking disk usage for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        disk_commands = [
            "df -h",
            "du -sh /var/lib/docker/* 2>/dev/null || echo 'Docker directory not found'",
            "ls -la /var/lib/docker/ 2>/dev/null || echo 'Docker directory not found'"
        ]
        
        for command in disk_commands:
            print(f"🔍 {command}:")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if success:
                print(stdout)
            else:
                print(f"❌ Failed: {stderr}")
            print("-" * 50)
        
        return True


def main():
    """Main function to manage Docker and Docker Compose."""
    
    parser = argparse.ArgumentParser(description='Unified Docker and Docker Compose Manager')
    parser.add_argument('--action', '-a', required=True,
                       choices=['build-env', 'up', 'down', 'restart', 'logs', 'status', 
                               'cleanup', 'info', 'disk-usage'],
                       help='Action to perform')
    parser.add_argument('--instance_name', '-i', type=str, required=True,
                       help='Instance name (e.g., jalusi-db-1)')
    parser.add_argument('--project_name', '-p', type=str,
                       help='Project name to append to /home/ec2-user/projects/ (e.g., learnly-project)')
    parser.add_argument('--region', '-r', default='af-south-1',
                       help='AWS region (default: af-south-1)')
    parser.add_argument('--service', type=str,
                       help='Specific service name for targeted operations')
    parser.add_argument('--build', action='store_true',
                       help='Build images when starting services (for up action)')
    parser.add_argument('--follow', '-f', action='store_true',
                       help='Follow logs in real-time (for logs action)')
    parser.add_argument('--tail', type=int, default=100,
                       help='Number of log lines to show (for logs action)')
    parser.add_argument('--aggressive', action='store_true',
                       help='Perform aggressive cleanup (for cleanup action)')
    
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
            # Get project root directory (go up from services/docker_compose_manager/)
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
    
    print("🐳 Unified Docker and Docker Compose Manager")
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
        # Initialize manager
        manager = UnifiedDockerManager(
            region_name=args.region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN
        )

        # Validate project_name for actions that require it
        actions_requiring_project = ['up', 'down', 'restart', 'logs', 'status']
        if args.action in actions_requiring_project and not args.project_name:
            print(f"❌ --project_name is required for action: {args.action}")
            print("   Example: --project_name learnly-project")
            return
        
        # Execute requested action
        if args.action == 'build-env':
            manager.build_docker_environment(args.instance_name)
        
        elif args.action == 'up':
            manager.docker_compose_up(args.instance_name, args.project_name, build=args.build, service=args.service)
        
        elif args.action == 'down':
            manager.docker_compose_down(args.instance_name, args.project_name, service=args.service)
        
        elif args.action == 'restart':
            manager.docker_compose_restart(args.instance_name, args.project_name, service=args.service)
        
        elif args.action == 'logs':
            manager.docker_compose_logs(args.instance_name, args.project_name, service=args.service, follow=args.follow, tail=args.tail)
        
        elif args.action == 'status':
            manager.docker_compose_status(args.instance_name, args.project_name)
        
        elif args.action == 'cleanup':
            manager.docker_cleanup(args.instance_name, aggressive=args.aggressive)
        
        elif args.action == 'info':
            manager.docker_info(args.instance_name)
        
        elif args.action == 'disk-usage':
            manager.disk_usage(args.instance_name)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()

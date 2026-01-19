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
    
    # Install/upgrade Docker Buildx (fixes "compose build requires buildx 0.17 or later" error)
    python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1
    
    # Restart Docker daemon
    python unified_docker_manager.py --action restart-docker --instance_name jalusi-db-1
    
    # Docker Compose operations
    python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project
    python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project
    
    # Docker Compose operations with custom path
    python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
    python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /opt/myapp
    
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
            
            # Install Docker Buildx (required for compose build) - improved installation
            "mkdir -p ~/.docker/cli-plugins",
            "sudo mkdir -p /root/.docker/cli-plugins",
            "sudo mkdir -p /usr/local/lib/docker/cli-plugins",
            "sudo mkdir -p /usr/lib/docker/cli-plugins",
            
            # Determine architecture first and map to Docker Buildx naming convention
            "ARCH=$(uname -m) && OS=$(uname -s | tr '[:upper:]' '[:lower:]') && case $ARCH in x86_64) BUILDX_ARCH=amd64;; aarch64|arm64) BUILDX_ARCH=arm64;; armv7l|armv6l) BUILDX_ARCH=arm-v7;; armv5l) BUILDX_ARCH=arm-v6;; *) BUILDX_ARCH=$ARCH;; esac && echo \"Detected: OS=$OS, ARCH=$ARCH -> BUILDX_ARCH=$BUILDX_ARCH\"",
            
            # Download Buildx with multiple fallback URLs and proper error handling
            "ARCH=$(uname -m) && OS=$(uname -s | tr '[:upper:]' '[:lower:]') && case $ARCH in x86_64) BUILDX_ARCH=amd64;; aarch64|arm64) BUILDX_ARCH=arm64;; armv7l|armv6l) BUILDX_ARCH=arm-v7;; armv5l) BUILDX_ARCH=arm-v6;; *) BUILDX_ARCH=$ARCH;; esac && BUILDX_URL=\"https://github.com/docker/buildx/releases/latest/download/buildx-${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1 || { BUILDX_URL=\"https://github.com/docker/buildx/releases/download/v0.17.0/buildx-v0.17.0.${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1; } || { BUILDX_URL=\"https://github.com/docker/buildx/releases/download/v0.12.1/buildx-v0.12.1.${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1; } || { echo 'All download attempts failed'; exit 1; }",
            
            # Verify download was successful - file should be > 1MB (actual binary is ~30MB)
            "if [ ! -f /tmp/docker-buildx ]; then echo 'ERROR: File does not exist after download'; exit 1; fi",
            "FILE_SIZE=$(stat -c%s /tmp/docker-buildx 2>/dev/null || stat -f%z /tmp/docker-buildx 2>/dev/null || echo 0) && if [ $FILE_SIZE -lt 1000000 ]; then echo \"ERROR: File too small ($FILE_SIZE bytes), likely download failed. Content:\"; head -5 /tmp/docker-buildx; exit 1; else echo \"Download successful: $FILE_SIZE bytes\"; fi",
            
            # Make executable
            "chmod +x /tmp/docker-buildx",
            
            # Verify it's actually an executable binary (not a text file with error message)
            "file /tmp/docker-buildx 2>/dev/null | grep -qE '(executable|ELF|binary)' && echo 'File is executable binary' || { echo 'ERROR: File is not a valid executable binary'; head -10 /tmp/docker-buildx; exit 1; }",
            
            # Install to user location
            "cp /tmp/docker-buildx ~/.docker/cli-plugins/docker-buildx",
            "chmod +x ~/.docker/cli-plugins/docker-buildx",
            
            # Install to root location
            "sudo cp /tmp/docker-buildx /root/.docker/cli-plugins/docker-buildx",
            "sudo chmod +x /root/.docker/cli-plugins/docker-buildx",
            
            # Install to system-wide locations (Docker will find it here)
            "sudo cp /tmp/docker-buildx /usr/local/lib/docker/cli-plugins/docker-buildx",
            "sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx",
            "sudo cp /tmp/docker-buildx /usr/lib/docker/cli-plugins/docker-buildx",
            "sudo chmod +x /usr/lib/docker/cli-plugins/docker-buildx",
            
            # Also install as standalone binary in PATH (fallback method)
            "sudo cp /tmp/docker-buildx /usr/local/bin/docker-buildx",
            "sudo chmod +x /usr/local/bin/docker-buildx",
            
            # Set DOCKER_BUILDKIT=1 to enable buildkit
            "echo 'export DOCKER_BUILDKIT=1' | sudo tee -a /etc/environment",
            
            # Clean up temp file
            "rm -f /tmp/docker-buildx",
            
            # Restart Docker daemon to recognize the plugin and apply daemon config
            "sudo systemctl restart docker",
            
            # Wait for Docker to fully restart
            "sleep 5",
            
            # Set up buildx builder (after Docker restart)
            "docker buildx create --name builder --use 2>/dev/null || /usr/local/bin/docker-buildx create --name builder --use 2>/dev/null || true",
            "docker buildx inspect --bootstrap 2>/dev/null || /usr/local/bin/docker-buildx inspect --bootstrap 2>/dev/null || true",
            
            # Verify installations
            "docker --version",
            "docker-compose --version",
            "docker buildx version 2>/dev/null || /usr/local/bin/docker-buildx version || echo 'Buildx verification skipped'",
            "docker system info"
        ]
        
        print("🚀 Installing Docker, Docker Compose, and Docker Buildx...")
        
        for i, command in enumerate(docker_install_commands, 1):
            print(f"📋 Step {i}/{len(docker_install_commands)}: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if not success:
                # Check if it's a critical download/verification step for Buildx
                if any(keyword in command for keyword in ["curl", "Download", "FILE_SIZE", "executable binary", "stat -c%s", "stat -f%z", "file /tmp/docker-buildx"]):
                    print(f"❌ Critical failure at step {i}: Buildx download/verification failed")
                    print(f"   Command: {command}")
                    print(f"   Error: {stderr}")
                    print(f"   Output: {stdout}")
                    print("💡 The Buildx binary download or verification failed.")
                    print("💡 This could be due to:")
                    print("   - Network connectivity issues")
                    print("   - GitHub API rate limiting")
                    print("   - Incorrect architecture detection")
                    return False
                else:
                    print(f"❌ Failed at step {i}: {command}")
                    print(f"   Error: {stderr}")
                    return False
            
            # Add delay between commands to ensure proper execution
            time.sleep(2)
        
        # Final verification of Buildx
        print("✅ Verifying Buildx installation...")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "docker buildx version")
        if not success:
            # Try standalone binary
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "/usr/local/bin/docker-buildx version")
            if success:
                print("✅ Docker Buildx is accessible as standalone binary!")
                print(f"📤 Buildx version: {stdout.strip()}")
            else:
                print("⚠️  Buildx verification failed, but installation may still be functional")
                print("💡 Docker Compose should still work as it can use buildx directly")
        else:
            print("✅ Docker Buildx is accessible as plugin!")
            print(f"📤 Buildx version: {stdout.strip()}")
        
        print("✅ Docker environment setup completed successfully!")
        print("💡 Docker, Docker Compose, and Docker Buildx are now installed and configured")
        return True

    def install_docker_buildx(self, instance_name):
        """Install or upgrade Docker Buildx on EC2 instance."""
        print(f"🔧 Installing/upgrading Docker Buildx for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Check Docker version first
        print("🔍 Checking Docker version...")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "docker --version")
        if success:
            print(f"📤 Docker version: {stdout.strip()}")
        else:
            print("⚠️  Could not determine Docker version")
        
        # Buildx installation commands
        buildx_install_commands = [
            # Create directories for buildx plugin (user and system-wide)
            "mkdir -p ~/.docker/cli-plugins",
            "sudo mkdir -p /root/.docker/cli-plugins",
            "sudo mkdir -p /usr/local/lib/docker/cli-plugins",
            "sudo mkdir -p /usr/lib/docker/cli-plugins",
            
            # Determine architecture first and map to Docker Buildx naming convention
            "ARCH=$(uname -m) && OS=$(uname -s | tr '[:upper:]' '[:lower:]') && case $ARCH in x86_64) BUILDX_ARCH=amd64;; aarch64|arm64) BUILDX_ARCH=arm64;; armv7l|armv6l) BUILDX_ARCH=arm-v7;; armv5l) BUILDX_ARCH=arm-v6;; *) BUILDX_ARCH=$ARCH;; esac && echo \"Detected: OS=$OS, ARCH=$ARCH -> BUILDX_ARCH=$BUILDX_ARCH\"",
            
            # Download Buildx with multiple fallback URLs and proper error handling
            "ARCH=$(uname -m) && OS=$(uname -s | tr '[:upper:]' '[:lower:]') && case $ARCH in x86_64) BUILDX_ARCH=amd64;; aarch64|arm64) BUILDX_ARCH=arm64;; armv7l|armv6l) BUILDX_ARCH=arm-v7;; armv5l) BUILDX_ARCH=arm-v6;; *) BUILDX_ARCH=$ARCH;; esac && BUILDX_URL=\"https://github.com/docker/buildx/releases/latest/download/buildx-${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1 || { BUILDX_URL=\"https://github.com/docker/buildx/releases/download/v0.17.0/buildx-v0.17.0.${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1; } || { BUILDX_URL=\"https://github.com/docker/buildx/releases/download/v0.12.1/buildx-v0.12.1.${OS}-${BUILDX_ARCH}\" && curl -Lf \"$BUILDX_URL\" -o /tmp/docker-buildx 2>&1; } || { echo 'All download attempts failed'; exit 1; }",
            
            # Verify download was successful - file should be > 1MB (actual binary is ~30MB)
            "if [ ! -f /tmp/docker-buildx ]; then echo 'ERROR: File does not exist after download'; exit 1; fi",
            "FILE_SIZE=$(stat -c%s /tmp/docker-buildx 2>/dev/null || stat -f%z /tmp/docker-buildx 2>/dev/null || echo 0) && if [ $FILE_SIZE -lt 1000000 ]; then echo \"ERROR: File too small ($FILE_SIZE bytes), likely download failed. Content:\"; head -5 /tmp/docker-buildx; exit 1; else echo \"Download successful: $FILE_SIZE bytes\"; fi",
            
            # Make executable
            "chmod +x /tmp/docker-buildx",
            
            # Verify it's actually an executable binary (not a text file with error message)
            "file /tmp/docker-buildx 2>/dev/null | grep -qE '(executable|ELF|binary)' && echo 'File is executable binary' || { echo 'ERROR: File is not a valid executable binary'; head -10 /tmp/docker-buildx; exit 1; }",
            
            # Install to user location
            "cp /tmp/docker-buildx ~/.docker/cli-plugins/docker-buildx",
            "chmod +x ~/.docker/cli-plugins/docker-buildx",
            
            # Install to root location
            "sudo cp /tmp/docker-buildx /root/.docker/cli-plugins/docker-buildx",
            "sudo chmod +x /root/.docker/cli-plugins/docker-buildx",
            
            # Install to system-wide locations (Docker will find it here)
            "sudo cp /tmp/docker-buildx /usr/local/lib/docker/cli-plugins/docker-buildx",
            "sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx",
            "sudo cp /tmp/docker-buildx /usr/lib/docker/cli-plugins/docker-buildx",
            "sudo chmod +x /usr/lib/docker/cli-plugins/docker-buildx",
            
            # Also install as standalone binary in PATH (fallback method)
            "sudo cp /tmp/docker-buildx /usr/local/bin/docker-buildx",
            "sudo chmod +x /usr/local/bin/docker-buildx",
            
            # Create wrapper script for docker buildx command (workaround for plugin system issues)
            "echo '#!/bin/bash\n/usr/local/bin/docker-buildx \"$@\"' | sudo tee /usr/local/bin/docker-buildx-wrapper",
            "sudo chmod +x /usr/local/bin/docker-buildx-wrapper",
            
            # Create alias in bashrc for current user (as fallback)
            "grep -q 'alias docker-buildx' ~/.bashrc || echo 'alias docker-buildx=\"/usr/local/bin/docker-buildx\"' >> ~/.bashrc",
            
            # Clean up temp file
            "rm -f /tmp/docker-buildx",
            
            # Verify files exist
            "ls -la ~/.docker/cli-plugins/docker-buildx /usr/local/lib/docker/cli-plugins/docker-buildx /usr/local/bin/docker-buildx 2>/dev/null | head -3",
        ]
        
        print("🚀 Installing Docker Buildx...")
        
        for i, command in enumerate(buildx_install_commands, 1):
            print(f"📋 Step {i}/{len(buildx_install_commands)}: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if not success:
                # Check if it's a critical download/verification step
                if any(keyword in command for keyword in ["curl", "Download", "FILE_SIZE", "executable binary", "stat -c%s", "stat -f%z", "file /tmp/docker-buildx"]):
                    print(f"❌ Critical failure at step {i}: Download/verification failed")
                    print(f"   Command: {command}")
                    print(f"   Error: {stderr}")
                    print(f"   Output: {stdout}")
                    print("💡 The Buildx binary download or verification failed.")
                    print("💡 This could be due to:")
                    print("   - Network connectivity issues")
                    print("   - GitHub API rate limiting")
                    print("   - Incorrect architecture detection")
                    print("   - Download returned an error page instead of binary")
                    return False
                else:
                    print(f"⚠️  Warning at step {i}: {command}")
                    if stderr:
                        print(f"   Error: {stderr}")
                    # Continue for non-critical steps
            
            # Add delay between commands to ensure proper execution
            time.sleep(1)
        
        # Create wrapper script to make 'docker buildx' work even if plugin system fails
        print("🔧 Creating Docker Buildx wrapper...")
        wrapper_script = '''#!/bin/bash
# Docker Buildx wrapper - makes 'docker buildx' work when plugin system doesn't recognize it
if [ "$1" = "buildx" ]; then
    shift
    /usr/local/bin/docker-buildx "$@"
else
    /usr/bin/docker "$@"
fi
'''
        # Save wrapper script
        success, stdout, stderr = self.execute_ssh_command(
            instance_info, key_path,
            f"echo '{wrapper_script}' | sudo tee /usr/local/bin/docker-wrapper && sudo chmod +x /usr/local/bin/docker-wrapper"
        )
        
        # Also set DOCKER_BUILDKIT=1 to enable buildkit
        print("🔧 Configuring Docker BuildKit...")
        self.execute_ssh_command(
            instance_info, key_path,
            "echo 'export DOCKER_BUILDKIT=1' | sudo tee -a /etc/environment"
        )
        
        # Restart Docker daemon to recognize the plugin
        print("🔄 Restarting Docker daemon...")
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "sudo systemctl restart docker")
        if not success:
            print(f"⚠️  Warning: Docker restart had issues: {stderr}")
        
        # Wait for Docker to fully restart
        print("⏳ Waiting for Docker to restart...")
        time.sleep(5)
        
        # Try multiple verification methods
        print("✅ Verifying Buildx installation...")
        
        # Method 1: Try as plugin
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "docker buildx version")
        if success:
            print("✅ Docker Buildx is accessible as plugin!")
            print(f"📤 Buildx version: {stdout.strip()}")
        else:
            # Method 2: Try as standalone binary
            print("⚠️  Plugin method failed, trying standalone binary...")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "/usr/local/bin/docker-buildx version")
            if success:
                print("✅ Docker Buildx is accessible as standalone binary!")
                print(f"📤 Buildx version: {stdout.strip()}")
                print("💡 Note: Buildx is installed but Docker plugin system doesn't recognize it.")
                print("💡 Docker Compose should still work as it can use buildx directly.")
                print("💡 You can use '/usr/local/bin/docker-buildx' directly if needed.")
            else:
                # Method 3: Check if file exists and has correct permissions
                print("⚠️  Both methods failed, checking installation...")
                success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, "ls -la ~/.docker/cli-plugins/docker-buildx /usr/local/lib/docker/cli-plugins/docker-buildx /usr/local/bin/docker-buildx 2>&1")
                if success:
                    print(f"📤 File locations:\n{stdout}")
                
                print("❌ Docker Buildx installation completed but verification failed!")
                print(f"   Error: {stderr}")
                print("💡 Troubleshooting:")
                print("   1. Try restarting Docker: sudo systemctl restart docker")
                print("   2. Check Docker version: docker --version")
                print("   3. Verify plugin location: ls -la ~/.docker/cli-plugins/")
                print("   4. Try using: /usr/local/bin/docker-buildx version")
                return False
        
        # Set up buildx builder (after Docker restart)
        print("🔧 Setting up Buildx builder...")
        builder_commands = [
            "docker buildx create --name builder --use 2>/dev/null || /usr/local/bin/docker-buildx create --name builder --use 2>/dev/null || true",
            "docker buildx inspect --bootstrap 2>/dev/null || /usr/local/bin/docker-buildx inspect --bootstrap 2>/dev/null || true"
        ]
        
        for command in builder_commands:
            print(f"📋 Executing: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            if not success:
                print(f"⚠️  Warning: {command}")
                if stderr:
                    print(f"   Error: {stderr}")
        
        print("✅ Docker Buildx installation completed successfully!")
        return True

    def docker_compose_up(self, instance_name, project_name, build=False, service=None, docker_compose_file_path=None):
        """Start Docker Compose services."""
        print(f"🚀 Starting Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Determine the path to use for docker-compose
        compose_path = docker_compose_file_path if docker_compose_file_path else f"/home/ec2-user/projects/{project_name}"
        
        # Navigate to project directory and run docker-compose up
        command = f"cd {compose_path} && docker-compose up -d"
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

    def docker_compose_down(self, instance_name, project_name, service=None, docker_compose_file_path=None):
        """Stop Docker Compose services."""
        print(f"🛑 Stopping Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Determine the path to use for docker-compose
        compose_path = docker_compose_file_path if docker_compose_file_path else f"/home/ec2-user/projects/{project_name}"
        
        # Check if docker-compose.yml file exists
        print(f"🔍 Checking for docker-compose.yml in {compose_path}...")
        check_command = f"test -f {compose_path}/docker-compose.yml && echo 'Found' || test -f {compose_path}/compose.yml && echo 'Found (compose.yml)' || echo 'Not found'"
        success_check, stdout_check, stderr_check = self.execute_ssh_command(instance_info, key_path, check_command)
        
        if stdout_check and "Not found" in stdout_check:
            print(f"❌ Docker Compose configuration file not found in {compose_path}")
            print(f"💡 Use --docker_compose_file_path to specify the correct path")
            return False
        
        command = f"cd {compose_path} && docker-compose down"
        if service:
            command += f" {service}"
        
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
        
        if success:
            print("✅ Docker Compose services stopped successfully!")
            return True
        else:
            print("❌ Failed to stop Docker Compose services")
            return False

    def docker_compose_restart(self, instance_name, project_name, service=None, docker_compose_file_path=None):
        """Restart Docker Compose services."""
        print(f"🔄 Restarting Docker Compose services for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Determine the path to use for docker-compose
        compose_path = docker_compose_file_path if docker_compose_file_path else f"/home/ec2-user/projects/{project_name}"
        
        # Check if docker-compose.yml file exists
        print(f"🔍 Checking for docker-compose.yml in {compose_path}...")
        check_command = f"test -f {compose_path}/docker-compose.yml && echo 'Found' || test -f {compose_path}/compose.yml && echo 'Found (compose.yml)' || echo 'Not found'"
        success_check, stdout_check, stderr_check = self.execute_ssh_command(instance_info, key_path, check_command)
        
        if stdout_check and "Not found" in stdout_check:
            print(f"❌ Docker Compose configuration file not found in {compose_path}")
            print(f"💡 Use --docker_compose_file_path to specify the correct path")
            return False
        
        if service:
            command = f"cd {compose_path} && docker-compose restart {service}"
        else:
            command = f"cd {compose_path} && docker-compose restart"
        
        success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
        
        if success:
            print("✅ Docker Compose services restarted successfully!")
            return True
        else:
            print("❌ Failed to restart Docker Compose services")
            return False

    def docker_compose_logs(self, instance_name, project_name, service=None, follow=False, tail=100, docker_compose_file_path=None):
        """View Docker Compose logs with streaming support."""
        print(f"📋 Viewing Docker Compose logs for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Determine the path to use for docker-compose
        compose_path = docker_compose_file_path if docker_compose_file_path else f"/home/ec2-user/projects/{project_name}"
        
        # Check if docker-compose.yml file exists
        print(f"🔍 Checking for docker-compose.yml in {compose_path}...")
        check_command = f"test -f {compose_path}/docker-compose.yml && echo 'Found' || test -f {compose_path}/compose.yml && echo 'Found (compose.yml)' || echo 'Not found'"
        success_check, stdout_check, stderr_check = self.execute_ssh_command(instance_info, key_path, check_command)
        
        if stdout_check and "Not found" in stdout_check:
            print(f"❌ Docker Compose configuration file not found in {compose_path}")
            print(f"💡 Looking for: docker-compose.yml or compose.yml")
            print(f"💡 Suggestions:")
            print(f"   1. Check if the path is correct: {compose_path}")
            print(f"   2. Use --docker_compose_file_path to specify the correct path")
            print(f"   3. Verify the docker-compose.yml file exists on the instance")
            
            # Try to find docker-compose files in subdirectories
            find_command = f"find {compose_path} -name 'docker-compose.yml' -o -name 'compose.yml' 2>/dev/null | head -5"
            success_find, stdout_find, stderr_find = self.execute_ssh_command(instance_info, key_path, find_command)
            if success_find and stdout_find.strip():
                print(f"💡 Found docker-compose files in subdirectories:")
                for line in stdout_find.strip().split('\n'):
                    if line.strip():
                        print(f"   - {line.strip()}")
            
            return False
        
        # Build command - add -f flag only if following
        if follow:
            command = f"cd {compose_path} && docker-compose logs -f --tail={tail}"
        else:
            command = f"cd {compose_path} && docker-compose logs --tail={tail}"
        
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

    def docker_compose_status(self, instance_name, project_name, docker_compose_file_path=None):
        """Show Docker Compose service status."""
        print(f"📊 Checking Docker Compose status for instance: {instance_name}, project: {project_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        # Determine the path to use for docker-compose
        compose_path = docker_compose_file_path if docker_compose_file_path else f"/home/ec2-user/projects/{project_name}"
        
        # Check if docker-compose.yml file exists
        print(f"🔍 Checking for docker-compose.yml in {compose_path}...")
        check_command = f"test -f {compose_path}/docker-compose.yml && echo 'Found' || test -f {compose_path}/compose.yml && echo 'Found (compose.yml)' || echo 'Not found'"
        success_check, stdout_check, stderr_check = self.execute_ssh_command(instance_info, key_path, check_command)
        
        if stdout_check and "Not found" in stdout_check:
            print(f"❌ Docker Compose configuration file not found in {compose_path}")
            print(f"💡 Use --docker_compose_file_path to specify the correct path")
            return False
        
        commands = [
            f"cd {compose_path} && docker-compose ps",
            f"cd {compose_path} && docker-compose top",
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

    def restart_docker(self, instance_name):
        """Restart Docker daemon on EC2 instance."""
        print(f"🔄 Restarting Docker daemon for instance: {instance_name}")
        
        instance_info = self.find_instance_by_name(instance_name)
        if not instance_info:
            return False
        
        key_path = self.check_ssh_key_exists(instance_name)
        if not key_path:
            return False
        
        restart_commands = [
            # Check Docker status before restart
            "sudo systemctl status docker | head -5 || true",
            
            # Restart Docker daemon
            "sudo systemctl restart docker",
            
            # Wait for Docker to restart
            "sleep 3",
            
            # Verify Docker is running
            "sudo systemctl status docker | head -5",
            "docker --version",
            "docker info | head -10"
        ]
        
        print("🔄 Restarting Docker daemon...")
        
        for i, command in enumerate(restart_commands, 1):
            print(f"📋 Step {i}/{len(restart_commands)}: {command}")
            success, stdout, stderr = self.execute_ssh_command(instance_info, key_path, command)
            
            if not success:
                # Status commands might fail, but restart should succeed
                if "restart" in command.lower():
                    print(f"❌ Failed to restart Docker at step {i}: {command}")
                    print(f"   Error: {stderr}")
                    return False
                else:
                    print(f"⚠️  Warning at step {i}: {command}")
                    print(f"   Error: {stderr}")
            
            # Add delay between commands
            time.sleep(1)
        
        print("✅ Docker daemon restarted successfully!")
        return True


def main():
    """Main function to manage Docker and Docker Compose."""
    
    parser = argparse.ArgumentParser(description='Unified Docker and Docker Compose Manager')
    parser.add_argument('--action', '-a', required=True,
                       choices=['build-env', 'install-buildx', 'restart-docker', 'up', 'down', 'restart', 'logs', 'status',
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
    parser.add_argument('--docker_compose_file_path', type=str,
                       help='Custom path to docker-compose file directory (if not provided, uses /home/ec2-user/projects/{project_name})')
    
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
        if args.docker_compose_file_path:
            docker_compose_file_paths = args.docker_compose_file_path.split(',')
        else:
            docker_compose_file_paths = []

        # Execute requested action
        if args.action == 'build-env':
            manager.build_docker_environment(args.instance_name)
        
        elif args.action == 'install-buildx':
            manager.install_docker_buildx(args.instance_name)
        
        elif args.action == 'restart-docker':
            manager.restart_docker(args.instance_name)
        
        elif args.action == 'up':
            if len(docker_compose_file_paths) > 1:
                for docker_compose_file_path in docker_compose_file_paths:
                    manager.docker_compose_up(args.instance_name, args.project_name, build=args.build, service=args.service, docker_compose_file_path=docker_compose_file_path)
            else:
                manager.docker_compose_up(args.instance_name, args.project_name, build=args.build, service=args.service, docker_compose_file_path=docker_compose_file_paths[0])
        
        elif args.action == 'down':
            if len(docker_compose_file_paths) > 1:
                for docker_compose_file_path in docker_compose_file_paths:
                    manager.docker_compose_down(args.instance_name, args.project_name, service=args.service, docker_compose_file_path=docker_compose_file_path)
            else:
                manager.docker_compose_down(args.instance_name, args.project_name, service=args.service, docker_compose_file_path=docker_compose_file_paths[0])
        
        elif args.action == 'restart':
            if len(docker_compose_file_paths) > 1:
                for docker_compose_file_path in docker_compose_file_paths:
                    manager.docker_compose_restart(args.instance_name, args.project_name, service=args.service, docker_compose_file_path=docker_compose_file_path)
            else:
                manager.docker_compose_restart(args.instance_name, args.project_name, service=args.service, docker_compose_file_path=docker_compose_file_paths[0])
        
        elif args.action == 'logs':
            if len(docker_compose_file_paths) > 1:
                for docker_compose_file_path in docker_compose_file_paths:
                    manager.docker_compose_logs(args.instance_name, args.project_name, service=args.service, follow=args.follow, tail=args.tail, docker_compose_file_path=docker_compose_file_path)
            else:
                manager.docker_compose_logs(args.instance_name, args.project_name, service=args.service, follow=args.follow, tail=args.tail, docker_compose_file_path=docker_compose_file_paths[0])
        
        elif args.action == 'status':
            if len(docker_compose_file_paths) > 1:
                for docker_compose_file_path in docker_compose_file_paths:
                    manager.docker_compose_status(args.instance_name, args.project_name, docker_compose_file_path=docker_compose_file_path)
            else:
                manager.docker_compose_status(args.instance_name, args.project_name, docker_compose_file_path=docker_compose_file_paths[0])
        
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

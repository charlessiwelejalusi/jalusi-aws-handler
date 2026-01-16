#!/usr/bin/env python3
"""
Nginx Configuration File Replacer for services deployed on EC2 Instances
This script SSH into EC2 instances with the instance_name
This script replaces the nginx configuration file on the instance with the updated config file in the nginx.conf directory
- Updated IP address from the EC2 instance
- Deploys the new configuration to the instance and restarts nginx

"""

import boto3
import re
import argparse
import subprocess
import time
import shutil
import tempfile
from botocore.exceptions import ClientError, NoCredentialsError
import sys
import os

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class NginxConfigReplacer:
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
        
        # First check in the pems directory
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
        
        # Check in parent directories
        for i in range(1, 5):  # Check up to 5 levels up
            parent_dir = os.path.join(os.path.dirname(__file__), *(['..'] * i))
            potential_path = os.path.join(parent_dir, 'pems', key_file)
            if os.path.exists(potential_path):
                print(f"✅ Found SSH key: {potential_path}")
                return potential_path
        
        # If not found in any location
        print(f"❌ SSH key file not found: {key_file}")
        print("💡 Please ensure the key file exists in one of these locations:")
        print(f"   - {pems_dir}/{key_file}")
        print(f"   - {os.getcwd()}/{key_file}")
        print(f"   - Any parent directory's pems/{key_file}")
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

    def copy_nginx_config_file(self, instance_info, config_filename="nginx_http.conf"):
        """Copy the nginx configuration file and replace the IP address."""
        print("📋 Copying nginx configuration file...")
        
        # Source file path
        source_file = os.path.join(os.path.dirname(__file__), "nginx.conf", config_filename)
        
        if not os.path.exists(source_file):
            print(f"❌ Source nginx configuration file not found: {source_file}")
            print(f"💡 Available config files:")
            nginx_conf_dir = os.path.join(os.path.dirname(__file__), "nginx.conf")
            if os.path.exists(nginx_conf_dir):
                for f in os.listdir(nginx_conf_dir):
                    if f.endswith('.conf'):
                        print(f"   - {f}")
            return None
        
        # Create a temporary file for the modified configuration
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
        content = None

        try:
            # Read the source file
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Get the IP address from instance info
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            if not ip_address:
                print("❌ No public IP address found for the instance")
                return None
            
            # Find and replace IP addresses in the config file
            # Look for common IP patterns (IPv4 addresses)
            import re
            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            
            # Find all IP addresses in the file
            found_ips = re.findall(ip_pattern, content)
            unique_ips = list(set(found_ips))
            
            # Replace all found IPs with the instance IP (except localhost/127.0.0.1)
            modified_content = content
            replaced_count = 0
            for old_ip in unique_ips:
                if old_ip not in ['127.0.0.1', '0.0.0.0', 'localhost'] and old_ip != ip_address:
                    modified_content = modified_content.replace(old_ip, ip_address)
                    replaced_count += 1
                    print(f"   Replaced IP: {old_ip} -> {ip_address}")
            
            if replaced_count == 0:
                print(f"⚠️  No IP addresses found to replace in config file")
                print(f"💡 Using instance IP: {ip_address}")
            
            # Replace Docker service names with localhost (for non-Docker deployments)
            # Common service names that might be in the config
            service_replacements = {
                'web-service': '127.0.0.1',
                'api-service': '127.0.0.1',
            }
            
            service_replaced_count = 0
            for service_name, replacement in service_replacements.items():
                # Replace in proxy_pass directives: http://service-name:port -> http://127.0.0.1:port
                # Handle cases with and without paths: http://service-name:5000 or http://service-name:5000/health
                pattern = rf'http://{re.escape(service_name)}:(\d+)(/[^\s;]*)?'
                def replace_service(match):
                    port = match.group(1)
                    path = match.group(2) or ''
                    return f'http://{replacement}:{port}{path}'
                
                new_content = re.sub(pattern, replace_service, modified_content)
                if new_content != modified_content:
                    service_replaced_count += modified_content.count(f'http://{service_name}:')
                    modified_content = new_content
                    print(f"   Replaced service references: {service_name} -> {replacement}")
            
            # Replace upstream blocks that reference Docker service names
            # Pattern: upstream service-name { server hostname:port; }
            upstream_pattern = r'upstream\s+(\w+)\s*\{[^}]*server\s+([^\s:;]+)(?::\d+)?;[^}]*\}'
            upstream_matches = list(re.finditer(upstream_pattern, modified_content, re.MULTILINE | re.DOTALL))
            for match in reversed(upstream_matches):  # Reverse to avoid position issues
                upstream_name = match.group(1)
                server_name = match.group(2)
                if server_name in service_replacements:
                    # Replace the upstream server with 127.0.0.1
                    old_upstream = match.group(0)
                    new_upstream = re.sub(
                        rf'server\s+{re.escape(server_name)}(?::\d+)?',
                        f'server {service_replacements[server_name]}\\1',
                        old_upstream
                    )
                    modified_content = modified_content[:match.start()] + new_upstream + modified_content[match.end():]
                    print(f"   Updated upstream block: {upstream_name}")
            
            # Also check for any standalone references to service names that might cause issues
            # (e.g., in server_name directives or other contexts)
            if service_replaced_count == 0:
                print("💡 No Docker service names found to replace in proxy_pass directives")
            
            # Check if the config needs to be wrapped in http block
            # If it contains server blocks but no http block, wrap it
            has_http_block = re.search(r'^\s*http\s*{', modified_content, re.MULTILINE)
            has_server_block = re.search(r'^\s*server\s*{', modified_content, re.MULTILINE)
            
            if has_server_block and not has_http_block:
                print("🔧 Wrapping configuration in http block for nginx.conf compatibility...")
                # Create a complete nginx.conf structure
                nginx_conf_structure = f"""user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

{modified_content}

}}
"""
                modified_content = nginx_conf_structure
            
            # Write the modified content to the temporary file
            temp_file.write(modified_content)
            temp_file.close()
            
            print(f"✅ Nginx configuration file copied and IP updated:")
            print(f"   Instance IP: {ip_address}")
            print(f"   IPs replaced: {replaced_count}")
            print(f"   Temporary file: {temp_file.name}")
            
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Error copying nginx configuration file: {e}")
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None

    def check_nginx_installation(self, instance_info, key_path):
        """Check if Nginx is installed on the instance."""
        print("📦 Checking Nginx installation...")
        
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "nginx -v",
            "Checking Nginx version"
        )
        
        if success:
            print(f"✅ Nginx is installed: {output}")
            return True
        else:
            print("❌ Nginx is not installed")
            return False

    def install_nginx(self, instance_info, key_path):
        """Install Nginx on the instance."""
        print("📦 Installing Nginx...")
        
        # Update system packages
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "sudo yum update -y",
            "Updating system packages"
        )
        
        if not success:
            print(f"❌ Failed to update packages: {output}")
            return False
        
        # Install Nginx
        success, output = self.run_ssh_command(
            instance_info, key_path,
            "sudo yum install -y nginx",
            "Installing Nginx"
        )
        
        if success:
            print("✅ Nginx installation completed")
            return True
        else:
            print(f"❌ Failed to install Nginx: {output}")
            return False

    def deploy_nginx_config(self, instance_info, key_path, config_file_path):
        """Deploy the nginx configuration file to the instance."""
        print("🚀 Deploying nginx configuration...")
        
        ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
        
        # Copy the configuration file to the instance
        scp_command = [
            'scp', '-i', key_path, '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
            config_file_path, f'ec2-user@{ip_address}:/tmp/nginx_http.conf'
        ]
        
        try:
            result = subprocess.run(scp_command, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=60)
            
            if result.returncode != 0:
                print(f"❌ Failed to copy configuration file: {result.stderr}")
                return False
            
            print("✅ Configuration file copied to instance")
            
            # Determine nginx config directory (common locations)
            # Try to find where nginx config should go
            success, nginx_config_dir = self.run_ssh_command(
                instance_info, key_path,
                "nginx -t 2>&1 | grep -oP 'file \K[^ ]+' | head -1 || echo '/etc/nginx'",
                "Finding nginx configuration directory"
            )
            
            # Default to /etc/nginx if detection fails
            if not nginx_config_dir or nginx_config_dir.strip() == '':
                nginx_config_dir = '/etc/nginx'
            else:
                nginx_config_dir = os.path.dirname(nginx_config_dir.strip())
            
            print(f"📁 Nginx config directory: {nginx_config_dir}")
            
            # Move the file to the nginx configuration directory
            target_path = f"{nginx_config_dir}/nginx.conf"
            success, output = self.run_ssh_command(
                instance_info, key_path,
                f"sudo cp /tmp/nginx_http.conf {target_path}",
                f"Copying configuration file to {target_path}"
            )
            
            if not success:
                print(f"❌ Failed to copy configuration file: {output}")
                return False
            
            print(f"✅ Configuration file copied to {target_path}")
            
            # Test nginx configuration
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo nginx -t",
                "Testing nginx configuration"
            )
            
            if not success:
                print(f"❌ Nginx configuration test failed: {output}")
                print("💡 The configuration file has been copied but nginx test failed.")
                print("💡 Please check the configuration manually before restarting nginx.")
                return False
            
            print("✅ Nginx configuration test passed")
            
            # Restart nginx to apply changes
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo systemctl restart nginx",
                "Restarting nginx service"
            )
            
            if not success:
                print(f"⚠️  Failed to restart nginx: {output}")
                print("💡 Configuration is deployed but nginx restart failed.")
                print("💡 You may need to restart nginx manually.")
                return False
            
            # Verify nginx is running
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo systemctl is-active nginx",
                "Verifying nginx is running"
            )
            
            if success and output.strip() == 'active':
                print("✅ Nginx is running successfully!")
            else:
                print("⚠️  Warning: Nginx status check returned unexpected result")
            
            print("✅ Nginx configuration file deployed and nginx restarted successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying nginx configuration: {e}")
            return False

    def restart_nginx(self, instance_name):
        """Restart nginx service on the specified instance."""
        print(f"🔄 Restarting nginx service for instance: {instance_name}")
        print("=" * 70)
        
        try:
            # Step 1: Find the instance
            instance_info = self.find_instance_by_name(instance_name)
            if not instance_info:
                print(f"❌ Cannot restart nginx: Instance not found: {instance_name}")
                return False
            print(f"✅ EC2 instance found: {instance_name}")
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(instance_name)
            if not key_path:
                print(f"❌ SSH key not found for instance: {instance_name}")
                return False
            print(f"✅ SSH key found for instance: {instance_name}")

            # Step 3: Test SSH connection
            if not self.test_ssh_connection(instance_info, key_path):
                print(f"❌ SSH connection failed for instance: {instance_name}")
                return False
            print(f"✅ SSH connection successful for instance: {instance_name}")

            # Step 4: Check Nginx installation
            print(f"🔧 Checking Nginx installation for instance: {instance_name}")
            nginx_installed = self.check_nginx_installation(instance_info, key_path)

            if not nginx_installed:
                print(f"❌ Nginx is not installed on instance: {instance_name}")
                print("💡 Please install Nginx first or use the replace-config option")
                return False
            else:
                print(f"✅ Nginx is installed for instance: {instance_name}")

            # Step 5: Test nginx configuration before restart
            print(f"🔧 Testing nginx configuration before restart...")
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo nginx -t",
                "Testing nginx configuration"
            )
            
            if not success:
                print(f"⚠️  Nginx configuration test failed: {output}")
                print("⚠️  Configuration has errors, but proceeding with restart...")
                print("💡 If restart fails, check the configuration manually")

            # Step 6: Restart nginx
            print(f"🔄 Restarting nginx service...")
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo systemctl restart nginx",
                "Restarting nginx service"
            )
            
            if not success:
                print(f"❌ Failed to restart nginx: {output}")
                return False

            # Step 7: Verify nginx is running
            print(f"✅ Verifying nginx is running...")
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo systemctl is-active nginx",
                "Verifying nginx status"
            )
            
            if success and output.strip() == 'active':
                print("✅ Nginx is running successfully!")
            else:
                print("⚠️  Warning: Nginx status check returned unexpected result")
                print(f"   Output: {output}")
                return False

            # Success summary
            print("\n" + "=" * 70)
            print("🎉 NGINX RESTART COMPLETE!")
            print("=" * 70)
            print(f"📋 Instance Name: {instance_name}")
            print(f"🖥️  Instance ID: {instance_info['id']}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
            print(f"🔗 SSH Command: ssh -i {key_path} ec2-user@{ip_address}")
            
            print("\n✅ Nginx service has been restarted successfully!")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error restarting nginx: {e}")
            return False

    def replace_nginx_config(self, instance_name, config_filename="nginx_http.conf"):
        """Replace nginx configuration file for the specified instance."""
        print(f"🔧 Replacing nginx configuration for instance: {instance_name}")
        print("=" * 70)
        
        try:
            # Step 1: Find the instance
            instance_info = self.find_instance_by_name(instance_name)
            if not instance_info:
                print(f"❌ Cannot replace nginx config: Instance not found: {instance_name}")
                return False
            print(f"✅ EC2 instance found: {instance_name}")
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(instance_name)
            if not key_path:
                print(f"❌ SSH key not found for instance: {instance_name}")
                return False
            print(f"✅ SSH key found for instance: {instance_name}")

            # Step 3: Test SSH connection
            if not self.test_ssh_connection(instance_info, key_path):
                print(f"❌ SSH connection failed for instance: {instance_name}")
                return False
            print(f"✅ SSH connection successful for instance: {instance_name}")

            # Step 4: Check Nginx installation
            print(f"🔧 Checking Nginx installation for instance: {instance_name}")
            nginx_installed = self.check_nginx_installation(instance_info, key_path)

            if not nginx_installed:
                print("📦 Installing Nginx...")
                if not self.install_nginx(instance_info, key_path):
                    print(f"❌ Nginx installation failed for instance: {instance_name}")
                    return False
                print(f"✅ Nginx installation successful for instance: {instance_name}")
            else:
                print(f"✅ Nginx is already installed for instance: {instance_name}")

            # Step 5: Copy and modify nginx configuration file
            print(f"🔧 Copying nginx configuration file for instance: {instance_name}")
            config_file_path = self.copy_nginx_config_file(instance_info, config_filename)
            if not config_file_path:
                print(f"❌ Failed to copy nginx configuration file for instance: {instance_name}")
                return False
            print(f"✅ Nginx configuration file copied and IP updated for instance: {instance_name}")
            
            # Step 6: Deploy the configuration
            print(f"🔧 Deploying nginx configuration for instance: {instance_name}")
            if not self.deploy_nginx_config(instance_info, key_path, config_file_path):
                print(f"❌ Failed to deploy nginx configuration for instance: {instance_name}")
                return False
            print(f"✅ Nginx configuration file deployed successfully for instance: {instance_name}")

            # Step 7: Clean up temporary file
            try:
                print(f"🔧 Cleaning up temporary file: {config_file_path}")
                os.unlink(config_file_path)
                print(f"✅ Cleaned up temporary file: {config_file_path}")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean up temporary file: {e}")
            
            # Success summary
            print("\n" + "=" * 70)
            print("🎉 NGINX CONFIGURATION REPLACEMENT COMPLETE!")
            print("=" * 70)
            print(f"📋 Instance Name: {instance_name}")
            print(f"🖥️  Instance ID: {instance_info['id']}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
            print(f"📄 Config File: {config_filename}")
            print(f"🔗 SSH Command: ssh -i {key_path} ec2-user@{ip_address}")
            
            print("\n✅ Nginx configuration has been updated and deployed!")
            print("💡 The new configuration is now active and serving requests")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error replacing nginx configuration: {e}")
            return False

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
    """Main function to replace nginx configuration."""
    
    parser = argparse.ArgumentParser(description='Replace Nginx Configuration on EC2 Instance')
    parser.add_argument('--instance_name', '-i', type=str, help='Instance name (e.g., jalusi-dev-1)')
    parser.add_argument('--config_file', '-c', type=str, default='nginx_http.conf',
                       help='Nginx config file name from nginx.conf directory (default: nginx_http.conf)')
    parser.add_argument('--action', '-a', type=str, choices=['replace', 'restart'], default='replace',
                       help='Action to perform: replace (replace config and restart) or restart (restart only, default: replace)')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    
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
    
    print("🔧 Nginx Configuration Replacer for EC2 Instances")
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
    
    # Validate instance_name is provided
    if not args.instance_name:
        print("❌ --instance_name is required")
        print("\nUsage:")
        print("  python replace_nginx_conf_file.py --instance_name jalusi-dev-1")
        print("  python replace_nginx_conf_file.py -i jalusi-dev-1 --config_file nginx_https.conf")
        print("  python replace_nginx_conf_file.py -i jalusi-dev-1 --action restart")
        print("\nAvailable config files:")
        nginx_conf_dir = os.path.join(os.path.dirname(__file__), "nginx.conf")
        if os.path.exists(nginx_conf_dir):
            for f in os.listdir(nginx_conf_dir):
                if f.endswith('.conf'):
                    print(f"   - {f}")
        return
    
    try:
        # Initialize nginx config replacer
        replacer = NginxConfigReplacer(
            region_name=args.region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN
        )
        
        # Execute the requested action
        if args.action == 'restart':
            # Restart nginx only
            print(f"🔄 Restarting nginx service for instance: {args.instance_name}")
            success = replacer.restart_nginx(args.instance_name)
            if success:
                print(f"\n✅ Nginx service restarted successfully for instance {args.instance_name}!")
            else:
                print(f"\n❌ Failed to restart nginx service for instance {args.instance_name}")
        else:
            # Replace nginx configuration (default action)
            print(f"🔧 Replacing nginx configuration for instance: {args.instance_name}")
            success = replacer.replace_nginx_config(args.instance_name, args.config_file)
            if success:
                print(f"\n✅ Nginx configuration replaced successfully for instance {args.instance_name}!")
            else:
                print(f"\n❌ Failed to replace nginx configuration for instance {args.instance_name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()



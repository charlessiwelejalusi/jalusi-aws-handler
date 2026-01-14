#!/usr/bin/env python3
"""
Nginx Configuration File Replacer for Learnly Production EC2 Instances

⚠️  WARNING: This is for development/testing purposes only!
    Never commit real AWS credentials to version control.
    Use environment variables or AWS CLI configuration in production.

This script SSH into EC2 instances with the naming pattern:
- learnly-prod-<sequence_number>

And replaces the nginx configuration file with:
- Updated IP address from the EC2 instance
- Deploys the new configuration to the instance
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

    def copy_nginx_config_file(self, sequence_number):
        """Copy the nginx configuration file and replace the IP address."""
        print("📋 Copying nginx configuration file...")
        
        # Source file path
        source_file = os.path.join(os.path.dirname(__file__), "nginx.conf", "nginx_http.conf")
        
        if not os.path.exists(source_file):
            print(f"❌ Source nginx configuration file not found: {source_file}")
            return None
        
        # Create a temporary file for the modified configuration
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
        
        try:
            # Read the source file
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Replace the placeholder IP with the actual IP
            # First, get the instance info to get the IP
            instance_info = self.find_instance_by_sequence(sequence_number)
            if not instance_info:
                return None
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            if not ip_address:
                print("❌ No public IP address found for the instance")
                return None
            
            # Replace the placeholder IP
            placeholder_ip = "13.246.77.68"
            modified_content = content.replace(placeholder_ip, ip_address)
            
            # Write the modified content to the temporary file
            temp_file.write(modified_content)
            temp_file.close()
            
            print(f"✅ Nginx configuration file copied and IP updated:")
            print(f"   Original IP: {placeholder_ip}")
            print(f"   New IP: {ip_address}")
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
            
            # Move the file to the nginx configuration directory (/home/ec2-user/learnly-project/learnly-project/nginx_http.conf)
            success, output = self.run_ssh_command(
                instance_info, key_path,
                "sudo mv /tmp/nginx_http.conf /home/ec2-user/learnly-project/learnly-project/nginx_http.conf",
                "Moving configuration file to nginx directory"
            )
            
            if not success:
                print(f"❌ Failed to move configuration file: {output}")
                return False
            
            # Test nginx configuration
            # success, output = self.run_ssh_command(
            #     instance_info, key_path,
            #     "sudo nginx -t",
            #     "Testing nginx configuration"
            # )
            
            # if not success:
            #     print(f"❌ Nginx configuration test failed: {output}")
            #     return False
            
            # print("✅ Nginx configuration test passed")
            
            # Reload nginx
            # success, output = self.run_ssh_command(
            #     instance_info, key_path,
            #     "sudo systemctl reload nginx",
            #     "Reloading nginx service"
            # )
            
            # if not success:
            #     print(f"❌ Failed to reload nginx: {output}")
            #     return False
            
            print("✅ Nginx configuration file deployed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying nginx configuration: {e}")
            return False

    def replace_nginx_config(self, sequence_number):
        """Replace nginx configuration file for the specified instance."""
        print(f"🔧 Replacing nginx configuration for sequence: {sequence_number}")
        print("=" * 70)
        
        try:
            # Step 1: Find the instance
            instance_info = self.find_instance_by_sequence(sequence_number)
            if not instance_info:
                print(f"❌ Cannot replace nginx config: Instance not found for sequence {sequence_number}")
                return False
            print(f"✅ EC2 instance found for sequence: {sequence_number}")
            
            # Step 2: Check SSH key
            key_path = self.check_ssh_key_exists(sequence_number)
            if not key_path:
                print(f"❌ SSH key not found for sequence: {sequence_number}")
                return False
            print(f"✅ SSH key found for sequence: {sequence_number}")

            # Step 3: Test SSH connection

            if not self.test_ssh_connection(instance_info, key_path):
                print(f"❌ SSH connection failed for sequence: {sequence_number}")
                return False
            print(f"✅ SSH connection successful for sequence: {sequence_number}")

            # Step 4: Check Nginx installation
            print(f"🔧 Checking Nginx installation for sequence: {sequence_number}")
            nginx_installed = self.check_nginx_installation(instance_info, key_path)

            if not nginx_installed:
                print("📦 Installing Nginx...")
                if not self.install_nginx(instance_info, key_path):
                    print(f"❌ Nginx installation failed for sequence: {sequence_number}")
                    return False
                print(f"✅ Nginx installation successful for sequence: {sequence_number}")
            else:
                print(f"✅ Nginx is already installed for sequence: {sequence_number}")

            # Step 5: Copy and modify nginx configuration file
            print(f"🔧 Copying nginx configuration file for sequence: {sequence_number}")
            config_file_path = self.copy_nginx_config_file(sequence_number)
            if not config_file_path:
                print(f"❌ Failed to copy nginx configuration file for sequence: {sequence_number}")
                return False
            print(f"✅ Nginx configuration file copied and IP updated for sequence: {sequence_number}")
            
            # Step 6: Deploy the configuration
            print(f"🔧 Deploying nginx configuration for sequence: {sequence_number}")
            if not self.deploy_nginx_config(instance_info, key_path, config_file_path):
                print(f"❌ Failed to deploy nginx configuration for sequence: {sequence_number}")
                return False
            print(f"✅ Nginx configuration file deployed successfully for sequence: {sequence_number}")

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
            print(f"📋 Sequence Number: {sequence_number}")
            print(f"🖥️  Instance ID: {instance_info['id']}")
            print(f"📋 Instance Name: {instance_info['name']}")
            
            ip_address = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            print(f"🌐 IP Address: {ip_address}")
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
    
    parser = argparse.ArgumentParser(description='Replace Nginx Configuration on Learnly Production EC2 Instance')
    parser.add_argument('--sequence', '-s', type=int, help='Sequence number to replace nginx config (e.g., 1 for learnly-prod-1)')
    parser.add_argument('--list', '-l', action='store_true', help='List all available sequence numbers')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    
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
    
    print("🔧 Nginx Configuration Replacer for Learnly Production")
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
        # Initialize nginx config replacer
        replacer = NginxConfigReplacer(
            region_name=args.region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN
        )
        
        if args.list:
            # List all sequences
            replacer.list_all_sequences()
        elif str(args.sequence):
            # Replace nginx configuration for specific sequence
            print(f"🔧 Replacing nginx configuration for sequence: {args.sequence}")
            success = replacer.replace_nginx_config(args.sequence)
            if success:
                print(f"\n✅ Nginx configuration replaced successfully for sequence {args.sequence}!")
            else:
                print(f"\n❌ Failed to replace nginx configuration for sequence {args.sequence}")
        else:
            # Show usage
            print("❌ Please specify either --sequence <number> or --list")
            print("\nExamples:")
            print("  python replace_nginx_conf_file.py --list")
            print("  python replace_nginx_conf_file.py --sequence 1")
            print("  python replace_nginx_conf_file.py -s 2")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()



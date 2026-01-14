#!/usr/bin/env python3
"""
Deploy Project Environment File (.env.prod.<sequence_number>) to EC2 Instance

This script:
1. Finds EC2 instance by sequence number
2. SSH into the instance
3. Securely copies .env.prod.<sequence_number> file to remote directory
4. Places it in /home/ec2-user/learnly-project/learnly-project

Usage:
    python deploy_project_env.py --sequence 1
    python deploy_project_env.py --sequence 2 --region us-east-1
"""

import os
import sys
import subprocess
import argparse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class ProjectEnvDeployer:
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

    def check_env_file_exists(self, sequence_number):
        """Check if .env.prod.<sequence_number> file exists."""
        env_file = f".env.prod.{sequence_number}"
        env_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'envs')
        env_path = os.path.join(env_dir, env_file)
        
        if os.path.exists(env_path):
            print(f"✅ Found environment file: {env_path}")
            return env_path
        else:
            print(f"❌ Environment file not found: {env_path}")
            print("💡 Make sure to generate the environment file first using:")
            print(f"   python generate_project_env.py --sequence {sequence_number}")
            return None

    def create_remote_directory(self, ssh_key_path, target_ip, remote_dir):
        """Create remote directory if it doesn't exist."""
        print(f"📁 Creating remote directory: {remote_dir}")
        
        ssh_command = [
            "ssh",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-t",
            f"ec2-user@{target_ip}",
            f"mkdir -p {remote_dir}"
        ]
        
        try:
            result = subprocess.run(ssh_command, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                print(f"✅ Remote directory created/verified: {remote_dir}")
                return True
            else:
                print(f"❌ Failed to create remote directory: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating remote directory: {e}")
            return False

    def copy_env_file(self, sequence_number, ssh_key_path=None, remote_dir="/home/ec2-user/learnly-project/learnly-project"):
        """Copy .env.prod.<sequence_number> file to EC2 instance."""

        # Find the instance
        instance_info = self.find_instance_by_sequence(sequence_number)
        if not instance_info:
            return False
        
        # Determine the IP address to use (Elastic IP preferred, then public IP)
        target_ip = instance_info.get('elastic_ip') or instance_info.get('public_ip')
        if not target_ip:
            print("❌ No public IP address found for the instance!")
            return False
        
        print(f"🌐 Target IP: {target_ip}")
        
        # Find SSH key if not provided
        if not ssh_key_path:
            ssh_key_path = self.check_ssh_key_exists(sequence_number)
            if not ssh_key_path:
                print("❌ Please provide the SSH key path using --ssh-key option")
                return False
        
        # Check if environment file exists
        env_file_path = self.check_env_file_exists(sequence_number)
        if not env_file_path:
            return False
        
        # Create remote directory
        if not self.create_remote_directory(ssh_key_path, target_ip, remote_dir):
            return False
        
        # Copy the environment file using scp
        remote_env_path = os.path.join(remote_dir, f".env")
        
        scp_command = [
            "scp",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            env_file_path,
            f"ec2-user@{target_ip}:{remote_env_path}"
        ]
        
        print(f"🔗 Connecting to EC2 instance: {target_ip}")
        print(f"👤 SSH User: ec2-user")
        print(f"📁 Local file: {env_file_path}")
        print(f"📁 Remote file: {remote_env_path}")
        print(f"🔑 SSH Key: {ssh_key_path}")
        print("🚀 Copying environment file...")
        print("-" * 80)
        
        try:
            result = subprocess.run(scp_command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            print("✅ Environment file copied successfully!")
            print("📤 Output:")
            print(result.stdout)
            if result.stderr:
                print("⚠️  Warnings:")
                print(result.stderr)
            
            # Verify the file was copied successfully
            verify_command = [
                "ssh",
                "-i", ssh_key_path,
                "-o", "StrictHostKeyChecking=no",
                "-t",
                f"ec2-user@{target_ip}",
                f"ls -la {remote_env_path}"
            ]
            
            verify_result = subprocess.run(verify_command, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if verify_result.returncode == 0:
                print("✅ File verification successful!")
                print("📋 Remote file details:")
                print(verify_result.stdout)
            else:
                print("⚠️  Could not verify file on remote server")
            
            return True
                
        except subprocess.CalledProcessError as e:
            print("❌ SCP command failed!")
            print("📤 STDOUT:")
            print(e.stdout)
            print("❌ STDERR:")
            print(e.stderr)
            return False
        except FileNotFoundError:
            print(f"❌ SCP command not found. Make sure SSH/SCP is installed and available in PATH.")
            return False

    def deploy_env(self, sequence_number, ssh_key_path=None, remote_dir="/home/ec2-user/learnly-project/learnly-project"):
        """Deploy the environment file to EC2 instance."""
        print(f"🚀 Deploying environment file for sequence: {sequence_number}")
        print("=" * 60)
        
        try:
            # Copy the environment file
            success = self.copy_env_file(sequence_number, ssh_key_path, remote_dir)
            
            if success:
                print("=" * 60)
                print("🎉 Environment file deployment completed successfully!")
                print(f"📁 Remote location: {remote_dir}/.env")
            else:
                print("=" * 60)
                print("❌ Environment file deployment failed!")
            
            return success
            
        except Exception as e:
            print(f"❌ Error deploying environment file: {e}")
            return False


def main():
    """Main function to execute the script."""
    parser = argparse.ArgumentParser(description='Deploy .env file to EC2 instance')
    parser.add_argument('--sequence', '-s', type=int, required=True, help='EC2 instance sequence number')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    parser.add_argument('--ssh-key', '-k', help='Path to SSH private key file')
    parser.add_argument('--remote-dir', '-d', default='/home/ec2-user/learnly-project/learnly-project', help='Remote directory to copy .env file to')
    parser.add_argument('--aws-access-key-id', help='AWS Access Key ID')
    parser.add_argument('--aws-secret-access-key', help='AWS Secret Access Key')
    parser.add_argument('--aws-session-token', help='AWS Session Token')
    
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
    
    print("🚀 Learnly Production Environment Deployer")
    print("=" * 60)
    print("⚠️  WARNING: This is for development/testing only!")
    print("   Never commit real AWS credentials to version control.")
    print("=" * 60)
    print(f"🎯 Target Sequence: {args.sequence}")
    print(f"🌍 AWS Region: {args.region}")
    print(f"📁 Remote Directory: {args.remote_dir}")
    
    # Check if credentials are set
    if AWS_ACCESS_KEY_ID == "YOUR_ACCESS_KEY_ID_HERE":
        print("❌ Please update the credentials in this file before running.")
        print("   Replace 'YOUR_ACCESS_KEY_ID_HERE' with your actual AWS Access Key ID")
        print("   Replace 'YOUR_SECRET_ACCESS_KEY_HERE' with your actual AWS Secret Access Key")
        return
    
    try:
        # Initialize the deployer
        deployer = ProjectEnvDeployer(
            region_name=args.region,
            aws_access_key_id=args.aws_access_key_id or AWS_ACCESS_KEY_ID,
            aws_secret_access_key=args.aws_secret_access_key or AWS_SECRET_ACCESS_KEY,
            aws_session_token=args.aws_session_token or AWS_SESSION_TOKEN
        )
        
        # Check if SSH key file exists
        if args.ssh_key and not os.path.isfile(args.ssh_key):
            print(f"❌ SSH key file not found: {args.ssh_key}")
            sys.exit(1)
        
        # Deploy the environment file
        success = deployer.deploy_env(
            sequence_number=args.sequence,
            ssh_key_path=args.ssh_key,
            remote_dir=args.remote_dir
        )
        
        if success:
            print("\n✅ Environment file deployment completed successfully!")
        else:
            print("\n❌ Environment file deployment failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

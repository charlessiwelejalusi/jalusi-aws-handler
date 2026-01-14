#!/usr/bin/env python3
"""
Generate Project Environment File (.env) for Learnly Production

This script:
1. Copies .env.example to .env
2. Generates database credentials with sequence number
3. Generates secure secret keys
4. Reads AWS credentials from infrastructure directories
5. Gets EC2 instance public IP
6. Updates all required environment variables

Usage:
    python generate_project_env.py --sequence 1
    python generate_project_env.py --sequence 2 --region us-east-1
"""

import os
import sys
import shutil
import argparse
import random
import string
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add the parent directory to the path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class ProjectEnvGenerator:
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

    def read_aws_credentials(self, sequence_number):
        """Read AWS credentials from the infrastructure directories."""
        print(f"🔐 Reading AWS credentials for sequence: {sequence_number}")
        
        # Define credential file paths
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        aws_access_key_dir = os.path.join(base_dir, "aws_access_key_id")
        aws_secret_key_dir = os.path.join(base_dir, "aws_secret_access_key")
        
        access_key_file = os.path.join(aws_access_key_dir, f"learnly-prod-{sequence_number}.txt")
        secret_key_file = os.path.join(aws_secret_key_dir, f"learnly-prod-{sequence_number}.txt")
        
        try:
            # Read AWS Access Key ID
            if os.path.exists(access_key_file):
                with open(access_key_file, 'r') as f:
                    aws_access_key_id = f.read().strip()
                print(f"✅ Read Access Key ID from: {access_key_file}")
            else:
                print(f"❌ Access Key file not found: {access_key_file}")
                return None, None
            
            # Read AWS Secret Access Key
            if os.path.exists(secret_key_file):
                with open(secret_key_file, 'r') as f:
                    aws_secret_access_key = f.read().strip()
                print(f"✅ Read Secret Access Key from: {secret_key_file}")
            else:
                print(f"❌ Secret Key file not found: {secret_key_file}")
                return None, None
            
            return aws_access_key_id, aws_secret_access_key
            
        except Exception as e:
            print(f"❌ Error reading AWS credentials: {e}")
            return None, None

    def generate_random_password(self, length=9):
        """Generate a random alphanumeric password."""
        characters = string.ascii_letters + string.digits
        chars = [c for c in characters if c not in "`'\""]
        return ''.join(random.choice(chars) for _ in range(length))

    def generate_secret_key(self, length=50):
        """Generate a secure secret key."""
        characters = string.ascii_letters + string.digits + string.punctuation
        chars = [c for c in characters if c not in "`'\"=#$%()_+-=[]{}|\\.?"]
        return ''.join(random.choice(chars) for _ in range(length))

    def copy_env_example(self, sequence_number, target_env_path):
        """Copy .env.example to .env.prod.<sequence_number>."""
        env_example_path = os.path.join(os.path.dirname(__file__), '..', '..', 'envs', '.env.example')
        
        if not os.path.exists(env_example_path):
            print(f"❌ .env.example not found at: {env_example_path}")
            return False
        
        try:
            shutil.copy2(env_example_path, target_env_path)
            print(f"✅ Copied .env.example to: {target_env_path}")
            return True
        except Exception as e:
            print(f"❌ Error copying .env.example: {e}")
            return False

    def update_env_file(self, env_path, sequence_number, aws_access_key_id, aws_secret_access_key, public_ip):
        """Update the .env file with generated values."""
        print(f"🔧 Updating .env file: {env_path}")
        
        try:
            # Read the current .env file
            with open(env_path, 'r') as f:
                content = f.read()
            
            # Generate values
            db_user = f"learnly_user"
            db_password = f"learnly_password"
            db_name = "learnly_db"
            database_url = f"postgresql://{db_user}:{db_password}@db:5432/{db_name}"
            
            django_secret_key = self.generate_secret_key(50)
            flask_secret_key = self.generate_secret_key(50)
            jwt_secret_key = self.generate_secret_key(50)
            
            aws_bucket_name = f"learnly-prod-{sequence_number}"
            
            # Update content with new values
            updates = {
                'DATABASE_URL': database_url,
                'POSTGRES_DB': db_name,
                'POSTGRES_USER': db_user,
                'POSTGRES_PASSWORD': db_password,
                'SECRET_KEY': django_secret_key,
                'WEB_SECRET_KEY': flask_secret_key,
                'JWT_SECRET_KEY': jwt_secret_key,
                'AWS_ACCESS_KEY_ID': aws_access_key_id,
                'AWS_SECRET_ACCESS_KEY': aws_secret_access_key,
                'AWS_STORAGE_BUCKET_NAME': aws_bucket_name,
                'PUBLIC_STATIC_IP': public_ip
            }
            
            # Apply updates
            for key, value in updates.items():
                # Handle different patterns in .env file
                patterns = [
                    f"{key}=",
                    f"{key} =",
                    f"export {key}=",
                    f"export {key} ="
                ]
                
                updated = False
                for pattern in patterns:
                    if pattern in content:
                        # Find the line and replace the value
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip().startswith(pattern.strip()):
                                if '=' in line:
                                    # Keep the original format (with or without spaces around =)
                                    if ' = ' in line:
                                        lines[i] = f"{key} = {value}"
                                    else:
                                        lines[i] = f"{key}={value}"
                                    updated = True
                                    break
                        if updated:
                            content = '\n'.join(lines)
                            break
                
                if not updated:
                    # Add the variable if it doesn't exist
                    content += f"\n{key}={value}\n"
            
            # Write the updated content back
            with open(env_path, 'w') as f:
                f.write(content)
            
            print("✅ .env file updated successfully!")
            print(f"📋 Generated values:")
            print(f"   Database Name: {db_name}")
            print(f"   Database User: {db_user}")
            print(f"   Database Password: {db_password}")
            print(f"   Database URL: {database_url}")
            print(f"   AWS Bucket: {aws_bucket_name}")
            print(f"   Public IP: {public_ip}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating .env file: {e}")
            return False

    def generate_env(self, sequence_number, output_path=None):
        """Generate the complete .env file."""
        print(f"🚀 Generating .env file for sequence: {sequence_number}")
        print("=" * 60)
        
        try:
            # Step 1: Get EC2 instance info
            instance_info = self.find_instance_by_sequence(sequence_number)
            if not instance_info:
                return False
            
            public_ip = instance_info.get('elastic_ip') or instance_info.get('public_ip')
            if not public_ip:
                print("❌ No public IP address found for the instance!")
                return False
            
            # Step 2: Read AWS credentials
            aws_access_key_id, aws_secret_access_key = self.read_aws_credentials(sequence_number)
            if not aws_access_key_id or not aws_secret_access_key:
                print("❌ Could not read AWS credentials!")
                return False
            
            # Step 3: Determine output path
            if not output_path:
                output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'envs', f'.env.prod.{sequence_number}')
            
            # Step 4: Copy .env.example
            if not self.copy_env_example(sequence_number, output_path):
                return False
            
            # Step 5: Update .env file
            if not self.update_env_file(output_path, sequence_number, aws_access_key_id, aws_secret_access_key, public_ip):
                return False
            
            print("=" * 60)
            print("🎉 .env file generation completed successfully!")
            print(f"📁 Output file: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating .env file: {e}")
            return False


def main():
    """Main function to execute the script."""
    parser = argparse.ArgumentParser(description='Generate .env file for Learnly Production')
    parser.add_argument('--sequence', '-s', type=int, required=True, help='EC2 instance sequence number')
    parser.add_argument('--region', '-r', default='af-south-1', help='AWS region (default: af-south-1)')
    parser.add_argument('--output', '-o', help='Output path for .env file')
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
    
    print("🔧 Learnly Production Environment Generator")
    print("=" * 60)
    print("⚠️  WARNING: This is for development/testing only!")
    print("   Never commit real AWS credentials to version control.")
    print("=" * 60)
    print(f"🎯 Target Sequence: {args.sequence}")
    print(f"🌍 AWS Region: {args.region}")
    
    # Check if credentials are set
    if AWS_ACCESS_KEY_ID == "YOUR_ACCESS_KEY_ID_HERE":
        print("❌ Please update the credentials in this file before running.")
        print("   Replace 'YOUR_ACCESS_KEY_ID_HERE' with your actual AWS Access Key ID")
        print("   Replace 'YOUR_SECRET_ACCESS_KEY_HERE' with your actual AWS Secret Access Key")
        return
    
    try:
        # Initialize the generator
        generator = ProjectEnvGenerator(
            region_name=args.region,
            aws_access_key_id=args.aws_access_key_id or AWS_ACCESS_KEY_ID,
            aws_secret_access_key=args.aws_secret_access_key or AWS_SECRET_ACCESS_KEY,
            aws_session_token=args.aws_session_token or AWS_SESSION_TOKEN
        )
        
        # Generate the .env file
        success = generator.generate_env(
            sequence_number=args.sequence,
            output_path=args.output
        )
        
        if success:
            print("\n✅ .env file generation completed successfully!")
        else:
            print("\n❌ .env file generation failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")
        sys.exit(1)


if __name__ == "__main__":
    main()

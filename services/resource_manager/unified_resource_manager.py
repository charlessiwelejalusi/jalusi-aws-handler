#!/usr/bin/env python3
"""
Unified AWS Resource Manager with Generic Naming Pattern
AWS Credentials are passed in by ENV variables
This script provides comprehensive AWS resource management functionality:

1. EC2 Instance Management:
   - List all EC2 instances and their statuses
   - Start EC2 instances by instance name filter pattern
   - Stop EC2 instances by instance name filter pattern

2. EBS Volume Management:
   - List EBS volumes
   - Create EBS volumes
   - Attach/Detach EBS volumes
   - Destroy EBS volumes

3. Complete Infrastructure Management:
   - Create complete infrastructure (EC2, EBS, S3, Security Groups, IAM, Key Pairs)
   - Destroy complete infrastructure
   - List all resources for a instance name
   - Auto-find next available instance name suffix sequence number (if no suffix sequence number then start at 1)

4. Resource Discovery:
   - Find all across instance names
   - List resources by type and status

Usage Examples:
    python unified_resource_manager.py --action list-instances
    python unified_resource_manager.py --action start-instance --instance_name jalusi-db-1
    python unified_resource_manager.py --action stop-instance --instance_name jalusi-db-1
    python unified_resource_manager.py --action create-infrastructure --instance_name jalusi-db-1
    python unified_resource_manager.py --action destroy-infrastructure --instance_name jalusi-db-1
    python unified_resource_manager.py --action list-resources --instance_name jalusi-db-1
    python unified_resource_manager.py --action list-volumes
    python unified_resource_manager.py --action destroy-volume-by-name --instance_name jalusi-db-1
    python unified_resource_manager.py --action destroy-volume-by-id --volume-id vol-1234567890abcdef0
"""

import boto3
import re
import json
import argparse
import time
import sys
import os
from botocore.exceptions import ClientError, NoCredentialsError, WaiterError
from datetime import datetime


class AWSResourceManager:
    """Base class for AWS resource management with credential handling."""
    
    def __init__(self, region_name='af-south-1', aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        """Initialize AWS clients with credentials."""
        try:
            # Store credentials for later use
            self.aws_access_key_id = aws_access_key_id
            self.aws_secret_access_key = aws_secret_access_key
            self.aws_session_token = aws_session_token
            self.region = region_name
            
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
            self.ec2_resource = session.resource('ec2')
            self.s3_client = session.client('s3')
            self.iam_client = session.client('iam')
            
            print(f"✅ Connected to AWS in region: {region_name}")
            
        except NoCredentialsError:
            print("❌ AWS credentials not found. Please configure your AWS credentials.")
            raise
        except Exception as e:
            print(f"❌ Error connecting to AWS: {e}")
            raise


class EC2InstanceManager(AWSResourceManager):
    """Manages EC2 instances with generic naming pattern."""
    
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
            print(f"{'Instance Name':<25} {'Instance ID':<20} {'State':<12} {'Type':<12} {'Public IP':<15} {'Private IP':<15} {'Launch Time':<20}")
            print("-" * 130)
            
            # Print each instance
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
                instance_type = instance['InstanceType']
                public_ip = instance.get('PublicIpAddress', 'N/A')
                private_ip = instance.get('PrivateIpAddress', 'N/A')
                launch_time = instance['LaunchTime'].strftime('%Y-%m-%d %H:%M:%S')
                
                # Color code the state
                state_color = {
                    'running': '🟢',
                    'stopped': '🔴',
                    'pending': '🟡',
                    'stopping': '🟠',
                    'terminated': '⚫',
                    'shutting-down': '🟠'
                }.get(state, '⚪')
                
                print(f"{instance_name:<25} {instance_id:<20} {state_color} {state:<10} {instance_type:<12} {public_ip:<15} {private_ip:<15} {launch_time:<20}")
            
            print("-" * 130)
            print(f"📊 Total instances found: {len(all_instances)}")
            
            # Summary by state
            state_counts = {}
            for instance in all_instances:
                state = instance['State']['Name']
                state_counts[state] = state_counts.get(state, 0) + 1
            
            if state_counts:
                print("\n📈 Instance Status Summary:")
                for state, count in sorted(state_counts.items()):
                    state_color = {
                        'running': '🟢',
                        'stopped': '🔴',
                        'pending': '🟡',
                        'stopping': '🟠',
                        'terminated': '⚫',
                        'shutting-down': '🟠'
                    }.get(state, '⚪')
                    print(f"  {state_color} {state.capitalize()}: {count}")
            
            return all_instances
            
        except Exception as e:
            print(f"❌ Error listing EC2 instances: {e}")
            raise


    def find_instances_by_filter(self, filter_pattern):
        """Find EC2 instances by filter pattern (matches instance name)."""
        print(f"🔍 Looking for instances matching pattern: {filter_pattern}")
        
        try:
            # Get all instances
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                ]
            )
            
            all_instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    all_instances.append(instance)
            
            if not all_instances:
                print(f"ℹ️  No EC2 instances found in this region.")
                return []
            
            # Filter instances by pattern
            filtered_instances = []
            for instance in all_instances:
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name' and filter_pattern.lower() in tag['Value'].lower():
                            filtered_instances.append(instance)
                            break
            
            if not filtered_instances:
                print(f"❌ No instances found matching pattern: {filter_pattern}")
                return []
            
            print(f"✅ Found {len(filtered_instances)} instance(s) matching pattern")
            for instance in filtered_instances:
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"   - {instance_name} ({instance['InstanceId']}) - State: {instance['State']['Name']}")
            
            return filtered_instances
                
        except Exception as e:
            print(f"❌ Error finding instances: {e}")
            raise

    def stop_instance(self, filter_pattern):
        """Stop EC2 instance(s) by filter pattern."""
        instances = self.find_instances_by_filter(filter_pattern)
        if not instances:
            return False
        
        # Filter out instances that can't be stopped
        stoppable_instances = []
        for instance in instances:
            instance_id = instance['InstanceId']
            current_state = instance['State']['Name']
            
            if current_state == 'stopped':
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"ℹ️  Instance {instance_name} ({instance_id}) is already stopped")
            elif current_state == 'terminated':
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"❌ Cannot stop terminated instance {instance_name} ({instance_id})")
            else:
                stoppable_instances.append(instance)
        
        if not stoppable_instances:
            print("ℹ️  No instances to stop (all are already stopped or terminated)")
            return True
        
        # Stop all stoppable instances
        instance_ids = [inst['InstanceId'] for inst in stoppable_instances]
        
        try:
            print(f"🛑 Stopping {len(stoppable_instances)} instance(s)...")
            for instance in stoppable_instances:
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"   - {instance_name} ({instance['InstanceId']})")
            
            self.ec2_client.stop_instances(InstanceIds=instance_ids)
            
            # Wait for all instances to be stopped
            print("⏳ Waiting for instances to be stopped...")
            waiter = self.ec2_client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=instance_ids)
            
            print(f"✅ Successfully stopped {len(stoppable_instances)} instance(s)!")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping instances: {e}")
            raise

    def start_instance(self, filter_pattern):
        """Start EC2 instance(s) by filter pattern."""
        instances = self.find_instances_by_filter(filter_pattern)
        if not instances:
            return False
        
        # Filter out instances that can't be started
        startable_instances = []
        for instance in instances:
            instance_id = instance['InstanceId']
            current_state = instance['State']['Name']
            
            if current_state == 'running':
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"ℹ️  Instance {instance_name} ({instance_id}) is already running")
            elif current_state == 'terminated':
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"❌ Cannot start terminated instance {instance_name} ({instance_id})")
            else:
                startable_instances.append(instance)
        
        if not startable_instances:
            print("ℹ️  No instances to start (all are already running or terminated)")
            return True
        
        # Start all startable instances
        instance_ids = [inst['InstanceId'] for inst in startable_instances]
        
        try:
            print(f"🚀 Starting {len(startable_instances)} instance(s)...")
            for instance in startable_instances:
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                print(f"   - {instance_name} ({instance['InstanceId']})")
            
            self.ec2_client.start_instances(InstanceIds=instance_ids)
            
            # Wait for all instances to be running
            print("⏳ Waiting for instances to be running...")
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=instance_ids)
            
            # Get updated instance info
            response = self.ec2_client.describe_instances(InstanceIds=instance_ids)
            print(f"✅ Successfully started {len(startable_instances)} instance(s)!")
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_name = 'Unnamed'
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                instance_name = tag['Value']
                                break
                    public_ip = instance.get('PublicIpAddress')
                    print(f"   - {instance_name} ({instance['InstanceId']})")
                    if public_ip:
                        print(f"     🌐 Public IP: {public_ip}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting instances: {e}")
            raise


class EBSVolumeManager(AWSResourceManager):
    """Manages EBS volumes with generic naming pattern."""
    
    def list_all_volumes(self, filter_pattern=None):
        """List all EBS volumes."""
        print("🔍 Listing EBS volumes...")
        print("=" * 80)
        
        try:
            response = self.ec2_client.describe_volumes()
            
            all_volumes = response['Volumes']
            
            if not all_volumes:
                print("ℹ️  No EBS volumes found in this region.")
                return []
            
            # Filter volumes if pattern is provided
            if filter_pattern:
                filtered_volumes = []
                for volume in all_volumes:
                    if 'Tags' in volume:
                        for tag in volume['Tags']:
                            if tag['Key'] == 'Name' and filter_pattern.lower() in tag['Value'].lower():
                                filtered_volumes.append(volume)
                                break
                all_volumes = filtered_volumes
                if not all_volumes:
                    print(f"ℹ️  No EBS volumes found matching pattern: {filter_pattern}")
                    return []
            
            # Sort volumes by name
            def get_volume_name(volume):
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            return tag['Value']
                return 'Unnamed'
            
            all_volumes.sort(key=get_volume_name)
            
            # Print header
            print(f"{'Volume Name':<25} {'Volume ID':<20} {'State':<12} {'Size':<8} {'Type':<8} {'Attached To':<20} {'Availability Zone':<20}")
            print("-" * 120)
            
            # Print each volume
            for volume in all_volumes:
                # Get volume name
                volume_name = 'Unnamed'
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            volume_name = tag['Value']
                            break
                
                # Get volume details
                volume_id = volume['VolumeId']
                state = volume['State']
                size = f"{volume['Size']} GiB"
                volume_type = volume['VolumeType']
                availability_zone = volume['AvailabilityZone']
                
                # Check if attached
                attached_to = 'N/A'
                if volume['Attachments']:
                    attached_to = volume['Attachments'][0]['InstanceId']
                
                # Color code the state
                state_color = {
                    'available': '🟢',
                    'in-use': '🔗',
                    'creating': '🟡',
                    'deleting': '🔴',
                    'deleted': '⚫',
                    'error': '❌'
                }.get(state, '⚪')
                
                print(f"{volume_name:<25} {volume_id:<20} {state_color} {state:<10} {size:<8} {volume_type:<8} {attached_to:<20} {availability_zone:<20}")
            
            print("-" * 120)
            print(f"📊 Total volumes found: {len(all_volumes)}")
            
            return all_volumes
            
        except Exception as e:
            print(f"❌ Error listing EBS volumes: {e}")
            raise


    def find_volume_by_sequence(self, sequence_number):
        """Find EBS volume by sequence number."""
        volume_name = f"learnly-prod-{sequence_number}"
        print(f"🔍 Looking for EBS volume: {volume_name}")
        
        try:
            response = self.ec2_client.describe_volumes(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [volume_name]}
                ]
            )
            
            if response['Volumes']:
                volume = response['Volumes'][0]
                print(f"✅ Found volume: {volume['VolumeId']} (State: {volume['State']})")
                return volume
            else:
                print(f"❌ Volume {volume_name} not found")
                return None
                
        except Exception as e:
            print(f"❌ Error finding volume: {e}")
            raise

    def find_volumes_by_name(self, instance_name):
        """Find EBS volumes by instance name pattern."""
        print(f"🔍 Looking for EBS volumes matching pattern: {instance_name}")
        
        try:
            response = self.ec2_client.describe_volumes()
            
            all_volumes = response['Volumes']
            
            if not all_volumes:
                print(f"ℹ️  No EBS volumes found in this region.")
                return []
            
            # Filter volumes by pattern
            filtered_volumes = []
            for volume in all_volumes:
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name' and instance_name.lower() in tag['Value'].lower():
                            filtered_volumes.append(volume)
                            break
            
            if not filtered_volumes:
                print(f"❌ No volumes found matching pattern: {instance_name}")
                return []
            
            print(f"✅ Found {len(filtered_volumes)} volume(s) matching pattern")
            for volume in filtered_volumes:
                volume_name = 'Unnamed'
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            volume_name = tag['Value']
                            break
                print(f"   - {volume_name} ({volume['VolumeId']}) - State: {volume['State']}")
            
            return filtered_volumes
                
        except Exception as e:
            print(f"❌ Error finding volumes: {e}")
            raise

    def destroy_volume_by_name(self, instance_name):
        """Destroy EBS volume(s) by instance name pattern."""
        volumes = self.find_volumes_by_name(instance_name)
        if not volumes:
            return False
        
        # Filter out volumes that can't be destroyed
        destroyable_volumes = []
        for volume in volumes:
            volume_id = volume['VolumeId']
            volume_state = volume['State']
            
            if volume_state == 'in-use':
                volume_name = 'Unnamed'
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            volume_name = tag['Value']
                            break
                print(f"❌ Cannot destroy volume {volume_name} ({volume_id}) - it is currently attached to an instance")
            elif volume_state == 'deleted':
                volume_name = 'Unnamed'
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            volume_name = tag['Value']
                            break
                print(f"ℹ️  Volume {volume_name} ({volume_id}) is already deleted")
            else:
                destroyable_volumes.append(volume)
        
        if not destroyable_volumes:
            print("ℹ️  No volumes to destroy (all are attached or already deleted)")
            return True
        
        # Destroy all destroyable volumes
        success_count = 0
        failed_count = 0
        
        for volume in destroyable_volumes:
            volume_id = volume['VolumeId']
            volume_name = 'Unnamed'
            if 'Tags' in volume:
                for tag in volume['Tags']:
                    if tag['Key'] == 'Name':
                        volume_name = tag['Value']
                        break
            
            try:
                print(f"🗑️  Destroying volume {volume_name} ({volume_id})...")
                self.ec2_client.delete_volume(VolumeId=volume_id)
                
                # Wait for volume to be deleted
                print("⏳ Waiting for volume to be deleted...")
                waiter = self.ec2_client.get_waiter('volume_deleted')
                waiter.wait(VolumeIds=[volume_id])
                
                print(f"✅ Volume {volume_name} ({volume_id}) destroyed successfully!")
                success_count += 1
            except Exception as e:
                print(f"❌ Error destroying volume {volume_id}: {e}")
                failed_count += 1
        
        print(f"\n📊 Summary: {success_count} destroyed, {failed_count} failed")
        return success_count > 0

    def destroy_volume_by_sequence(self, sequence_number):
        """Destroy EBS volume by sequence number."""
        volume = self.find_volume_by_sequence(sequence_number)
        if not volume:
            return False
        
        volume_id = volume['VolumeId']
        return self.destroy_volume_by_volume_id(volume_id)

    def destroy_volume_by_volume_id(self, volume_id):
        """Destroy EBS volume by volume ID."""
        print(f"🔍 Looking for volume: {volume_id}")
        
        try:
            # Get volume details
            response = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
            
            if not response['Volumes']:
                print(f"❌ Volume {volume_id} not found")
                return False
            
            volume = response['Volumes'][0]
            volume_state = volume['State']
            
            # Get volume name for display
            volume_name = 'Unnamed'
            if 'Tags' in volume:
                for tag in volume['Tags']:
                    if tag['Key'] == 'Name':
                        volume_name = tag['Value']
                        break
            
            print(f"📋 Volume Details:")
            print(f"   Name: {volume_name}")
            print(f"   ID: {volume_id}")
            print(f"   State: {volume_state}")
            print(f"   Size: {volume['Size']} GiB")
            print(f"   Type: {volume['VolumeType']}")
            
            if volume_state == 'in-use':
                print(f"❌ Cannot destroy volume {volume_id} - it is currently attached to an instance")
                if volume['Attachments']:
                    attached_to = volume['Attachments'][0]['InstanceId']
                    print(f"   Attached to instance: {attached_to}")
                return False
            elif volume_state == 'deleted':
                print(f"ℹ️  Volume {volume_id} is already deleted")
                return True
            
            try:
                print(f"🗑️  Destroying volume {volume_id}...")
                self.ec2_client.delete_volume(VolumeId=volume_id)
                
                # Wait for volume to be deleted
                print("⏳ Waiting for volume to be deleted...")
                waiter = self.ec2_client.get_waiter('volume_deleted')
                waiter.wait(VolumeIds=[volume_id])
                
                print(f"✅ Volume {volume_id} ({volume_name}) destroyed successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Error destroying volume: {e}")
                raise
                
        except Exception as e:
            print(f"❌ Error finding volume: {e}")
            raise

    def destroy_volume_by_volume_id_list(self, volume_id_list: str):
        """Destroy multiple EBS volumes by comma-separated volume ID list."""
        print(f"🔍 Processing volume list: {volume_id_list}")
        
        # Parse comma-separated volume IDs
        volume_ids = [vid.strip() for vid in volume_id_list.split(',') if vid.strip()]
        
        if not volume_ids:
            print("❌ No valid volume IDs found in the list")
            return False
        
        print(f"📋 Found {len(volume_ids)} volume(s) to process:")
        for i, vid in enumerate(volume_ids, 1):
            print(f"   {i}. {vid}")
        
        print("\n" + "="*60)
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, volume_id in enumerate(volume_ids, 1):
            print(f"\n🔄 Processing volume {i}/{len(volume_ids)}: {volume_id}")
            print("-" * 40)
            
            try:
                # Get volume details
                response = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
                
                if not response['Volumes']:
                    print(f"❌ Volume {volume_id} not found")
                    failed_count += 1
                    continue
                
                volume = response['Volumes'][0]
                volume_state = volume['State']
                
                # Get volume name for display
                volume_name = 'Unnamed'
                if 'Tags' in volume:
                    for tag in volume['Tags']:
                        if tag['Key'] == 'Name':
                            volume_name = tag['Value']
                            break
                
                print(f"📋 Volume Details:")
                print(f"   Name: {volume_name}")
                print(f"   ID: {volume_id}")
                print(f"   State: {volume_state}")
                print(f"   Size: {volume['Size']} GiB")
                print(f"   Type: {volume['VolumeType']}")
                
                if volume_state == 'in-use':
                    print(f"❌ Cannot destroy volume {volume_id} - it is currently attached to an instance")
                    if volume['Attachments']:
                        attached_to = volume['Attachments'][0]['InstanceId']
                        print(f"   Attached to instance: {attached_to}")
                    failed_count += 1
                    continue
                elif volume_state == 'deleted':
                    print(f"ℹ️  Volume {volume_id} is already deleted")
                    skipped_count += 1
                    continue
                
                # Confirm destruction (optional - you can remove this for automation)
                print(f"🗑️  Destroying volume {volume_id}...")
                self.ec2_client.delete_volume(VolumeId=volume_id)
                
                # Wait for volume to be deleted
                print("⏳ Waiting for volume to be deleted...")
                waiter = self.ec2_client.get_waiter('volume_deleted')
                waiter.wait(VolumeIds=[volume_id])
                
                print(f"✅ Volume {volume_id} ({volume_name}) destroyed successfully!")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error processing volume {volume_id}: {e}")
                failed_count += 1
                continue
        
        # Summary
        print("\n" + "="*60)
        print("📊 BATCH DESTRUCTION SUMMARY")
        print("="*60)
        print(f"✅ Successfully destroyed: {success_count}")
        print(f"❌ Failed to destroy: {failed_count}")
        print(f"ℹ️  Skipped (already deleted): {skipped_count}")
        print(f"📋 Total processed: {len(volume_ids)}")
        
        if success_count > 0:
            print(f"\n🎉 Successfully destroyed {success_count} volume(s)!")
        
        if failed_count > 0:
            print(f"⚠️  {failed_count} volume(s) could not be destroyed. Check the logs above for details.")
        
        return success_count > 0


class InfrastructureManager(AWSResourceManager):
    """Manages complete infrastructure creation and destruction with generic naming pattern."""
    
    def find_next_instance_name(self, base_instance_name):
        """Find the next available instance name with suffix sequence number.
        
        If base_instance_name already has a suffix (e.g., 'jalusi-db-1'), extracts the base
        and finds the next available suffix. If no suffix exists, starts at 1.
        """
        print(f"🔍 Finding next available instance name for pattern: {base_instance_name}")
        
        try:
            # Extract base name and check if it already has a suffix
            # Pattern: name-{number} or just name
            match = re.search(r'^(.+)-(\d+)$', base_instance_name)
            if match:
                base_name = match.group(1)
                existing_suffix = int(match.group(2))
            else:
                base_name = base_instance_name
                existing_suffix = None
            
            # Get all instances
            response = self.ec2_client.describe_instances()
            
            existing_sequences = []
            pattern = re.compile(rf'^{re.escape(base_name)}-(\d+)$')
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                match = pattern.search(tag['Value'])
                                if match:
                                    existing_sequences.append(int(match.group(1)))
            
            if existing_sequences:
                print(f"📊 Found existing sequence numbers: {sorted(existing_sequences)}")
                next_sequence = max(existing_sequences) + 1
            else:
                print("📊 No existing instances found with this pattern")
                next_sequence = 1
            
            next_instance_name = f"{base_name}-{next_sequence}"
            print(f"🎯 Next instance name: {next_instance_name}")
            return next_instance_name
            
        except Exception as e:
            print(f"❌ Error finding next instance name: {e}")
            raise

    def create_key_pair(self, instance_name):
        """Create EC2 key pair for the instance name."""
        key_name = instance_name
        
        # Create pems directory path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up to aws-handler directory
        pems_dir = os.path.join(project_dir, 'pems')
        
        # Create pems directory if it doesn't exist
        if not os.path.exists(pems_dir):
            os.makedirs(pems_dir)
            print(f"📁 Created pems directory: {pems_dir}")
        
        key_file = os.path.join(pems_dir, f"{key_name}.pem")
        
        print(f"🔑 Creating key pair: {key_name}")
        
        try:
            # Check if key pair already exists
            try:
                response = self.ec2_client.describe_key_pairs(KeyNames=[key_name])
                if response['KeyPairs']:
                    print(f"ℹ️  Key pair {key_name} already exists, using existing one")
                    return key_name, key_file
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
                    pass  # Key doesn't exist, create it
                else:
                    raise
            
            # Create new key pair
            response = self.ec2_client.create_key_pair(KeyName=key_name)
            
            # Save private key to file in pems directory
            with open(key_file, 'w') as f:
                f.write(response['KeyMaterial'])
            
            # Set proper permissions on key file (Unix-like systems)
            try:
                os.chmod(key_file, 0o400)
            except:
                # On Windows, chmod might not work, but that's okay
                pass
            
            print(f"✅ Key pair created successfully!")
            print(f"📁 Private key saved to: {key_file}")
            
            return key_name, key_file
            
        except Exception as e:
            print(f"❌ Error creating key pair: {e}")
            raise

    def create_s3_bucket(self, instance_name):
        """Create S3 bucket for the instance name."""
        bucket_name = instance_name
        
        print(f"🪣 Creating S3 bucket: {bucket_name}")
        
        try:
            # Check if bucket already exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"ℹ️  S3 bucket {bucket_name} already exists, using existing one")
                return bucket_name
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    pass  # Bucket doesn't exist, create it
                else:
                    raise
            
            # Create bucket
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.region}
            )
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            print(f"✅ S3 bucket created successfully!")
            return bucket_name
            
        except Exception as e:
            print(f"❌ Error creating S3 bucket: {e}")
            raise

    def create_security_group(self, instance_name):
        """Create security group for the instance name."""
        sg_name = instance_name
        sg_description = f"Security group for {instance_name}"
        
        print(f"🛡️ Creating security group: {sg_name}")
        
        try:
            # Get default VPC
            response = self.ec2_client.describe_vpcs(
                Filters=[{'Name': 'is-default', 'Values': ['true']}]
            )
            
            if not response['Vpcs']:
                raise Exception("No default VPC found")
            
            vpc_id = response['Vpcs'][0]['VpcId']
            
            # Check if security group already exists
            try:
                response = self.ec2_client.describe_security_groups(
                    Filters=[
                        {'Name': 'group-name', 'Values': [sg_name]},
                        {'Name': 'vpc-id', 'Values': [vpc_id]}
                    ]
                )
                if response['SecurityGroups']:
                    sg_id = response['SecurityGroups'][0]['GroupId']
                    print(f"ℹ️  Security group {sg_name} already exists, using existing one: {sg_id}")
                    return sg_id
            except Exception:
                pass
            
            # Create security group
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description=sg_description,
                VpcId=vpc_id
            )
            
            sg_id = response['GroupId']
            
            # Add inbound rules
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            
            print(f"✅ Security group created successfully!")
            return sg_id
            
        except Exception as e:
            print(f"❌ Error creating security group: {e}")
            raise

    def create_iam_role_and_policy(self, instance_name):
        """Create IAM role, policy, and instance profile for the instance name."""
        role_name = instance_name
        policy_name = instance_name
        instance_profile_name = instance_name
        
        print(f"👤 Creating IAM role: {role_name}")
        
        try:
            # Create IAM policy
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{instance_name}",
                            f"arn:aws:s3:::{instance_name}/*"
                        ]
                    }
                ]
            }
            
            # Check if policy already exists
            try:
                self.iam_client.get_policy(PolicyArn=f"arn:aws:iam::{self.get_account_id()}:policy/{policy_name}")
                print(f"ℹ️  IAM policy {policy_name} already exists, using existing one")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # Create policy
                    response = self.iam_client.create_policy(
                        PolicyName=policy_name,
                        PolicyDocument=json.dumps(policy_document)
                    )
                    print(f"✅ IAM policy created: {response['Policy']['Arn']}")
                else:
                    raise
            
            # Check if role already exists
            try:
                self.iam_client.get_role(RoleName=role_name)
                print(f"ℹ️  IAM role {role_name} already exists, using existing one")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # Create role
                    trust_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "ec2.amazonaws.com"},
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    }
                    
                    response = self.iam_client.create_role(
                        RoleName=role_name,
                        AssumeRolePolicyDocument=json.dumps(trust_policy)
                    )
                    print(f"✅ IAM role created: {response['Role']['Arn']}")
                else:
                    raise
            
            # Attach policy to role
            try:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=f"arn:aws:iam::{self.get_account_id()}:policy/{policy_name}"
                )
                print(f"✅ Policy attached to role")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    print(f"ℹ️  Policy already attached to role")
                else:
                    raise
            
            # Check if instance profile already exists
            try:
                self.iam_client.get_instance_profile(InstanceProfileName=instance_profile_name)
                print(f"ℹ️  IAM instance profile {instance_profile_name} already exists, using existing one")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    # Create instance profile
                    response = self.iam_client.create_instance_profile(
                        InstanceProfileName=instance_profile_name
                    )
                    print(f"✅ IAM instance profile created: {response['InstanceProfile']['Arn']}")
                else:
                    raise
            
            # Check if role is already attached to instance profile
            try:
                response = self.iam_client.get_instance_profile(InstanceProfileName=instance_profile_name)
                attached_roles = response['InstanceProfile']['Roles']
                role_already_attached = any(role['RoleName'] == role_name for role in attached_roles)
                
                if role_already_attached:
                    print(f"ℹ️  Role already attached to instance profile")
                else:
                    # Add role to instance profile
                    self.iam_client.add_role_to_instance_profile(
                        InstanceProfileName=instance_profile_name,
                        RoleName=role_name
                    )
                    print(f"✅ Role added to instance profile")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    print(f"ℹ️  Role already added to instance profile")
                else:
                    raise
            
            # Wait a moment for the instance profile to be fully propagated
            print("⏳ Waiting for IAM instance profile to be fully propagated...")
            time.sleep(10)
            
            print(f"✅ IAM role, policy, and instance profile created successfully!")
            return instance_profile_name
            
        except Exception as e:
            print(f"❌ Error creating IAM resources: {e}")
            raise

    def get_account_id(self):
        """Get AWS account ID."""
        try:
            # Create STS client with the stored credentials
            sts_client = boto3.client('sts', 
                                    aws_access_key_id=self.aws_access_key_id,
                                    aws_secret_access_key=self.aws_secret_access_key,
                                    aws_session_token=self.aws_session_token,
                                    region_name=self.region)
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            print(f"❌ Error getting account ID: {e}")
            raise

    def create_ec2_instance(self, instance_name, key_name, security_group_id, instance_profile_name, instance_type='t3.micro'):
        """Create EC2 instance for the instance name.
        
        Note: This method creates paid EC2 instances. Free Tier restrictions do not apply.
        If you encounter Free Tier errors, ensure your AWS account allows paid resources.
        """
        
        print(f"🖥️ Creating EC2 instance: {instance_name}")
        print(f"💳 Instance Type: {instance_type} (Paid resource - not Free Tier)")
        
        try:
            # Get latest Amazon Linux 2023 AMI
            response = self.ec2_client.describe_images(
                Owners=['amazon'],
                Filters=[
                    {'Name': 'name', 'Values': ['al2023-ami-*-x86_64']},
                    {'Name': 'state', 'Values': ['available']}
                ]
            )
            
            if not response['Images']:
                raise Exception("No Amazon Linux 2023 AMI found")
            
            # Sort by creation date and get the latest
            latest_ami = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]
            ami_id = latest_ami['ImageId']
            
            print(f"📦 Using AMI: {ami_id}")
            
            # Create instance (paid resource - not subject to Free Tier restrictions)
            # Note: If you get Free Tier errors, check your AWS account settings
            # Free Tier restrictions are account-level and may need to be disabled
            try:
                response = self.ec2_client.run_instances(
                    ImageId=ami_id,
                    MinCount=1,
                    MaxCount=1,
                    InstanceType=instance_type,
                    KeyName=key_name,
                    SecurityGroupIds=[security_group_id],
                    IamInstanceProfile={'Name': instance_profile_name},
                    TagSpecifications=[
                        {
                            'ResourceType': 'instance',
                            'Tags': [
                                {'Key': 'Name', 'Value': instance_name}
                            ]
                        }
                    ],
                    BlockDeviceMappings=[
                        {
                            'DeviceName': '/dev/xvda',
                            'Ebs': {
                                'VolumeSize': 30,
                                'VolumeType': 'gp3',
                                'DeleteOnTermination': False,
                                'Encrypted': True
                            }
                        }
                    ]
                )
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                # Handle Free Tier restriction errors with helpful message
                # Check for Free Tier in error message or InvalidParameterCombination with Free Tier context
                is_free_tier_error = (
                    'Free Tier' in error_message or 
                    'free-tier' in error_message.lower() or
                    (error_code == 'InvalidParameterCombination' and 'free-tier' in error_message.lower())
                )
                
                if is_free_tier_error:
                    print(f"\n❌ Free Tier Restriction Error:")
                    print(f"   Your AWS account appears to have Free Tier restrictions enabled.")
                    print(f"   Instance type '{instance_type}' is not Free Tier eligible.")
                    print(f"\n💡 Solutions:")
                    print(f"   1. Disable Free Tier restrictions in your AWS account settings")
                    print(f"   2. Use a Free Tier eligible instance type: t2.micro or t3.micro")
                    print(f"   3. Contact AWS Support to enable paid resources for your account")
                    print(f"   4. Check if your account has Service Control Policies (SCPs) enforcing Free Tier")
                    print(f"   5. Verify your account billing/payment method is set up correctly")
                    print(f"\n📋 Free Tier Eligible Instance Types:")
                    print(f"   - t2.micro (1 vCPU, 1 GiB RAM)")
                    print(f"   - t3.micro (2 vCPU, 1 GiB RAM)")
                    print(f"\n💳 Paid Instance Types (require account configuration):")
                    print(f"   - t3.small, t3.medium, t3.large, t3.xlarge, etc.")
                    print(f"   - m5.large, m5.xlarge, m5.2xlarge, etc.")
                    print(f"   - Any instance type beyond Free Tier limits")
                    raise Exception(f"Free Tier restriction: {error_message}. See solutions above.")
                else:
                    # Re-raise other errors as-is
                    raise
            
            instance_id = response['Instances'][0]['InstanceId']
            
            print(f"✅ EC2 instance created successfully!")
            print(f"🆔 Instance ID: {instance_id}")
            
            # Wait for instance to be running
            print("⏳ Waiting for instance to be running...")
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            
            # Get instance details
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            public_ip = instance.get('PublicIpAddress')
            availability_zone = instance['Placement']['AvailabilityZone']
            
            print(f"🌐 Public IP: {public_ip}")
            print(f"📍 Availability Zone: {availability_zone}")
            
            return instance_id, public_ip, availability_zone
            
        except Exception as e:
            print(f"❌ Error creating EC2 instance: {e}")
            raise

    def create_or_reuse_ebs_volume(self, instance_name, availability_zone):
        """Create or reuse EBS volume for the instance name."""
        volume_name = instance_name
        
        print(f"🔍 Looking for existing EBS volume: {volume_name}")
        
        try:
            # Check if volume already exists
            response = self.ec2_client.describe_volumes(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [volume_name]},
                    {'Name': 'status', 'Values': ['available', 'in-use']}
                ]
            )
            
            if response['Volumes']:
                volume = response['Volumes'][0]
                volume_id = volume['VolumeId']
                print(f"✅ Found existing EBS volume: {volume_id} (State: {volume['State']})")
                print(f"✅ Using existing EBS volume: {volume_id}")
                return volume_id
            
            # Create new volume
            print(f"💾 Creating new EBS volume: {volume_name}")
            
            response = self.ec2_client.create_volume(
                AvailabilityZone=availability_zone,
                Size=30,
                VolumeType='gp3',
                TagSpecifications=[
                    {
                        'ResourceType': 'volume',
                        'Tags': [
                            {'Key': 'Name', 'Value': volume_name}
                        ]
                    }
                ]
            )
            
            volume_id = response['VolumeId']
            
            # Wait for volume to be available
            print("⏳ Waiting for EBS volume to be available...")
            waiter = self.ec2_client.get_waiter('volume_available')
            waiter.wait(VolumeIds=[volume_id])
            
            print(f"✅ EBS volume created successfully: {volume_id}")
            return volume_id
            
        except Exception as e:
            print(f"❌ Error creating/reusing EBS volume: {e}")
            raise

    def attach_ebs_volume(self, volume_id, instance_id):
        """Attach EBS volume to EC2 instance."""
        print(f"🔗 Attaching EBS volume {volume_id} to instance {instance_id}")
        
        try:
            # Check current volume state and attachments
            response = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
            if not response['Volumes']:
                raise Exception(f"Volume {volume_id} not found")
            
            volume = response['Volumes'][0]
            attachments = volume.get('Attachments', [])
            
            # Check if volume is already attached
            if attachments:
                current_attachment = attachments[0]
                current_instance_id = current_attachment['InstanceId']
                current_state = current_attachment['State']
                
                # If already attached to the target instance, skip
                if current_instance_id == instance_id:
                    if current_state == 'attached':
                        print(f"✅ Volume {volume_id} is already attached to instance {instance_id}")
                        return
                    elif current_state in ['attaching', 'detaching']:
                        print(f"⏳ Volume {volume_id} is currently {current_state}, waiting...")
                        waiter = self.ec2_client.get_waiter('volume_in_use')
                        waiter.wait(VolumeIds=[volume_id])
                        print(f"✅ Volume {volume_id} attachment completed")
                        return
                
                # If attached to a different instance, detach it first
                if current_instance_id != instance_id:
                    print(f"⚠️  Volume {volume_id} is attached to different instance: {current_instance_id}")
                    print(f"🔄 Detaching from instance {current_instance_id}...")
                    
                    self.ec2_client.detach_volume(VolumeId=volume_id)
                    
                    # Wait for detachment to complete
                    print("⏳ Waiting for volume to detach...")
                    waiter = self.ec2_client.get_waiter('volume_available')
                    waiter.wait(VolumeIds=[volume_id])
                    print(f"✅ Volume {volume_id} detached successfully")
            
            # Attach volume to target instance
            print(f"🔗 Attaching volume {volume_id} to instance {instance_id}...")
            response = self.ec2_client.attach_volume(
                VolumeId=volume_id,
                InstanceId=instance_id,
                Device='/dev/sdf'
            )
            
            print(f"✅ EBS volume attachment initiated!")
            print(f"🔗 Device: /dev/sdf")
            print(f"📊 State: {response['State']}")
            
            # Wait for attachment to complete
            print("⏳ Waiting for EBS volume attachment to complete...")
            waiter = self.ec2_client.get_waiter('volume_in_use')
            waiter.wait(VolumeIds=[volume_id])
            
            print(f"✅ EBS volume attached successfully!")
            
        except Exception as e:
            error_msg = str(e)
            # Handle the specific VolumeInUse error more gracefully
            if 'VolumeInUse' in error_msg:
                print(f"⚠️  Volume {volume_id} is already in use")
                # Try to get current attachment info
                try:
                    response = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
                    if response['Volumes']:
                        volume = response['Volumes'][0]
                        attachments = volume.get('Attachments', [])
                        if attachments:
                            attached_to = attachments[0]['InstanceId']
                            if attached_to == instance_id:
                                print(f"✅ Volume is already attached to the target instance")
                                return
                            else:
                                print(f"💡 Volume is attached to instance: {attached_to}")
                                print(f"💡 You may need to detach it first or use a different volume")
                except:
                    pass
            print(f"❌ Error attaching EBS volume: {e}")
            raise

    def allocate_elastic_ip(self, instance_name):
        """Allocate an Elastic IP address and tag it with instance name."""
        print(f"🌐 Allocating Elastic IP for instance: {instance_name}")
        
        try:
            # Allocate Elastic IP
            response = self.ec2_client.allocate_address(
                Domain='vpc'  # Use VPC domain for EC2-VPC instances
            )
            
            allocation_id = response['AllocationId']
            public_ip = response['PublicIp']
            
            # Tag the Elastic IP with instance name
            self.ec2_client.create_tags(
                Resources=[allocation_id],
                Tags=[
                    {'Key': 'Name', 'Value': instance_name}
                ]
            )
            
            print(f"✅ Elastic IP allocated successfully!")
            print(f"🆔 Allocation ID: {allocation_id}")
            print(f"🌐 Public IP: {public_ip}")
            
            return allocation_id, public_ip
            
        except Exception as e:
            print(f"❌ Error allocating Elastic IP: {e}")
            raise

    def associate_elastic_ip(self, allocation_id, instance_id):
        """Associate an Elastic IP with an EC2 instance."""
        print(f"🔗 Associating Elastic IP {allocation_id} with instance {instance_id}")
        
        try:
            # Associate Elastic IP with instance
            response = self.ec2_client.associate_address(
                AllocationId=allocation_id,
                InstanceId=instance_id
            )
            
            association_id = response['AssociationId']
            print(f"✅ Elastic IP associated successfully!")
            print(f"🔗 Association ID: {association_id}")
            
            # Get the public IP address
            response = self.ec2_client.describe_addresses(AllocationIds=[allocation_id])
            if response['Addresses']:
                public_ip = response['Addresses'][0]['PublicIp']
                print(f"🌐 Static Public IP: {public_ip}")
                return public_ip
            
            return None
            
        except Exception as e:
            print(f"❌ Error associating Elastic IP: {e}")
            raise

    def find_elastic_ip_by_instance_name(self, instance_name):
        """Find Elastic IP allocation by instance name tag."""
        print(f"🔍 Looking for Elastic IP with tag Name={instance_name}")
        
        try:
            # Get all Elastic IPs
            response = self.ec2_client.describe_addresses()
            
            # Filter by tag
            for address in response['Addresses']:
                if 'Tags' in address:
                    for tag in address['Tags']:
                        if tag['Key'] == 'Name' and tag['Value'] == instance_name:
                            allocation_id = address['AllocationId']
                            public_ip = address['PublicIp']
                            instance_id = address.get('InstanceId')
                            association_id = address.get('AssociationId')
                            
                            print(f"✅ Found Elastic IP: {allocation_id} ({public_ip})")
                            if instance_id:
                                print(f"   Associated with instance: {instance_id}")
                            
                            return {
                                'allocation_id': allocation_id,
                                'public_ip': public_ip,
                                'instance_id': instance_id,
                                'association_id': association_id
                            }
            
            print(f"ℹ️  No Elastic IP found with tag Name={instance_name}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding Elastic IP: {e}")
            return None

    def release_elastic_ip(self, allocation_id):
        """Release an Elastic IP address."""
        print(f"🗑️  Releasing Elastic IP: {allocation_id}")
        
        try:
            # First, disassociate if it's associated
            response = self.ec2_client.describe_addresses(AllocationIds=[allocation_id])
            if response['Addresses']:
                address = response['Addresses'][0]
                if address.get('AssociationId'):
                    print(f"🔗 Disassociating Elastic IP from instance...")
                    self.ec2_client.disassociate_address(AssociationId=address['AssociationId'])
                    print(f"✅ Elastic IP disassociated")
            
            # Release the Elastic IP
            self.ec2_client.release_address(AllocationId=allocation_id)
            print(f"✅ Elastic IP {allocation_id} released successfully!")
            
        except Exception as e:
            print(f"❌ Error releasing Elastic IP: {e}")
            raise

    def destroy_infrastructure(self, instance_name):
        """Destroy complete infrastructure for the instance name."""
        print(f"💥 Starting Infrastructure Destruction for: {instance_name}")
        print("=" * 70)
        
        try:
            # First, list all resources to see what exists
            resources = self.list_resources_by_instance_name(instance_name)
            
            # Destroy resources in reverse order of dependencies
            
            # 1. Terminate EC2 instances (this will detach EBS volumes)
            if resources['instance']:
                instance_id = resources['instance']['id']
                print(f"\n🖥️  Terminating EC2 instance: {instance_id}")
                try:
                    self.ec2_client.terminate_instances(InstanceIds=[instance_id])
                    print("⏳ Waiting for instance to terminate...")
                    waiter = self.ec2_client.get_waiter('instance_terminated')
                    waiter.wait(InstanceIds=[instance_id])
                    print(f"✅ Instance {instance_id} terminated successfully!")
                except Exception as e:
                    print(f"❌ Error terminating instance: {e}")
            
            # Also check for any other instances with the same name
            try:
                response = self.ec2_client.describe_instances(
                    Filters=[
                        {'Name': 'tag:Name', 'Values': [instance_name]},
                        {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                    ]
                )
                
                additional_instances = []
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        if instance['InstanceId'] != resources['instance']['id'] if resources['instance'] else None:
                            additional_instances.append(instance['InstanceId'])
                
                if additional_instances:
                    print(f"\n🖥️  Found additional instances with same sequence number: {additional_instances}")
                    for instance_id in additional_instances:
                        print(f"🖥️  Terminating additional instance: {instance_id}")
                        try:
                            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
                            waiter = self.ec2_client.get_waiter('instance_terminated')
                            waiter.wait(InstanceIds=[instance_id])
                            print(f"✅ Additional instance {instance_id} terminated successfully!")
                        except Exception as e:
                            print(f"❌ Error terminating additional instance {instance_id}: {e}")
            except Exception as e:
                print(f"⚠️  Error checking for additional instances: {e}")
            
            # 2. Release Elastic IP if it exists
            elastic_ip_info = self.find_elastic_ip_by_instance_name(instance_name)
            if elastic_ip_info:
                allocation_id = elastic_ip_info['allocation_id']
                print(f"\n🌐 Releasing Elastic IP: {allocation_id}")
                try:
                    self.release_elastic_ip(allocation_id)
                    print(f"✅ Elastic IP {allocation_id} released successfully!")
                except Exception as e:
                    print(f"❌ Error releasing Elastic IP: {e}")
            
            # 3. Delete EBS volume
            if resources['volume']:
                volume_id = resources['volume']['id']
                print(f"\n💾 Deleting EBS volume: {volume_id}")
                try:
                    self.ec2_client.delete_volume(VolumeId=volume_id)
                    print("⏳ Waiting for volume to be deleted...")
                    waiter = self.ec2_client.get_waiter('volume_deleted')
                    waiter.wait(VolumeIds=[volume_id])
                    print(f"✅ EBS volume {volume_id} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting EBS volume: {e}")
            
            # 4. Delete S3 bucket
            if resources['s3_bucket']:
                bucket_name = resources['s3_bucket']['name']
                print(f"\n🪣 Deleting S3 bucket: {bucket_name}")
                try:
                    # Delete all objects in bucket
                    response = self.s3_client.list_objects_v2(Bucket=bucket_name)
                    if 'Contents' in response:
                        objects = [{'Key': obj['Key']} for obj in response['Contents']]
                        if objects:
                            self.s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
                            print(f"🗑️  Deleted {len(objects)} objects from bucket")
                    
                    # Delete bucket
                    self.s3_client.delete_bucket(Bucket=bucket_name)
                    print(f"✅ S3 bucket {bucket_name} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting S3 bucket: {e}")
            
            # 5. Delete key pair
            if resources['key_pair']:
                key_name = resources['key_pair']['name']
                
                # Look for key file in pems directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up to aws-handler directory
                pems_dir = os.path.join(project_dir, 'pems')
                key_file = os.path.join(pems_dir, f"{key_name}.pem")
                
                print(f"\n🔑 Deleting key pair: {key_name}")
                try:
                    self.ec2_client.delete_key_pair(KeyName=key_name)
                    print(f"✅ Key pair {key_name} deleted successfully!")
                    
                    # Delete local key file
                    if os.path.exists(key_file):
                        try:
                            os.remove(key_file)
                            print(f"🗑️  Deleted local key file: {key_file}")
                        except PermissionError:
                            print(f"⚠️  Could not delete key file (access denied): {key_file}")
                        except Exception as e:
                            print(f"⚠️  Error deleting key file: {e}")
                    else:
                        print(f"ℹ️  Key file not found: {key_file}")
                except Exception as e:
                    print(f"❌ Error deleting key pair: {e}")
            
            # 6. Delete security group
            if resources['security_group']:
                sg_id = resources['security_group']['id']
                sg_name = resources['security_group']['name']
                print(f"\n🛡️  Deleting security group: {sg_name} ({sg_id})")
                try:
                    self.ec2_client.delete_security_group(GroupId=sg_id)
                    print(f"✅ Security group {sg_name} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting security group: {e}")
            
            # 7. Delete IAM resources (in proper order)
            if resources['iam_instance_profile']:
                instance_profile_name = resources['iam_instance_profile']['name']
                print(f"\n👤 Deleting IAM instance profile: {instance_profile_name}")
                try:
                    # Remove role from instance profile first
                    role_name = instance_name
                    self.iam_client.remove_role_from_instance_profile(
                        InstanceProfileName=instance_profile_name,
                        RoleName=role_name
                    )
                    print(f"🔗 Removed role from instance profile")
                    
                    # Delete instance profile
                    self.iam_client.delete_instance_profile(InstanceProfileName=instance_profile_name)
                    print(f"✅ IAM instance profile {instance_profile_name} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting IAM instance profile: {e}")
            
            if resources['iam_role']:
                role_name = resources['iam_role']['name']
                print(f"\n👤 Deleting IAM role: {role_name}")
                try:
                    # Detach policy from role
                    policy_name = instance_name
                    self.iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=f"arn:aws:iam::{self.get_account_id()}:policy/{policy_name}"
                    )
                    print(f"🔗 Detached policy from role")
                    
                    # Delete role
                    self.iam_client.delete_role(RoleName=role_name)
                    print(f"✅ IAM role {role_name} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting IAM role: {e}")
            
            if resources['iam_policy']:
                policy_name = resources['iam_policy']['name']
                print(f"\n👤 Deleting IAM policy: {policy_name}")
                try:
                    self.iam_client.delete_policy(PolicyArn=f"arn:aws:iam::{self.get_account_id()}:policy/{policy_name}")
                    print(f"✅ IAM policy {policy_name} deleted successfully!")
                except Exception as e:
                    print(f"❌ Error deleting IAM policy: {e}")
            
            # Summary
            print("\n" + "=" * 70)
            print("🎉 INFRASTRUCTURE DESTRUCTION COMPLETE!")
            print("=" * 70)
            print(f"📋 Instance Name: {instance_name}")
            print("✅ All resources have been cleaned up")
            print("=" * 70)
            
        except Exception as e:
            print(f"❌ Error destroying infrastructure: {e}")
            raise

    def list_resources_by_instance_name(self, instance_name):
        """List all resources for a given instance name."""
        print(f"🔍 Listing all resources for instance: {instance_name}")
        print("=" * 60)
        
        resources = {
            'instance': None,
            'volume': None,
            'security_group': None,
            'key_pair': None,
            's3_bucket': None,
            'iam_role': None,
            'iam_policy': None,
            'iam_instance_profile': None,
            'elastic_ip': None
        }
        
        try:
            # Find EC2 instance
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [instance_name]},
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                ]
            )
            
            if response['Reservations']:
                instance = response['Reservations'][0]['Instances'][0]
                resources['instance'] = {
                    'id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'public_ip': instance.get('PublicIpAddress'),
                    'private_ip': instance.get('PrivateIpAddress')
                }
                print(f"🖥️  EC2 Instance: {instance['InstanceId']} ({instance['State']['Name']})")
            else:
                print(f"🖥️  EC2 Instance: Not found")
            
            # Find EBS volume
            volume_name = instance_name
            response = self.ec2_client.describe_volumes(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [volume_name]},
                    {'Name': 'status', 'Values': ['available', 'in-use']}
                ]
            )
            
            if response['Volumes']:
                volume = response['Volumes'][0]
                resources['volume'] = {
                    'id': volume['VolumeId'],
                    'state': volume['State'],
                    'size': volume['Size'],
                    'attached_to': volume.get('Attachments', [])
                }
                print(f"💾 EBS Volume: {volume['VolumeId']} ({volume['State']}, {volume['Size']} GiB)")
            else:
                print(f"💾 EBS Volume: Not found")
            
            # Find security group
            sg_name = instance_name
            response = self.ec2_client.describe_security_groups(
                Filters=[{'Name': 'group-name', 'Values': [sg_name]}]
            )
            
            if response['SecurityGroups']:
                sg = response['SecurityGroups'][0]
                resources['security_group'] = {
                    'id': sg['GroupId'],
                    'name': sg['GroupName']
                }
                print(f"🛡️  Security Group: {sg['GroupId']} ({sg['GroupName']})")
            else:
                print(f"🛡️  Security Group: Not found")
            
            # Find key pair
            key_name = instance_name
            try:
                response = self.ec2_client.describe_key_pairs(KeyNames=[key_name])
                if response['KeyPairs']:
                    resources['key_pair'] = {'name': key_name}
                    print(f"🔑 Key Pair: {key_name}")
                else:
                    print(f"🔑 Key Pair: Not found")
            except ClientError:
                print(f"🔑 Key Pair: Not found")
            
            # Check S3 bucket
            bucket_name = instance_name
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                resources['s3_bucket'] = {'name': bucket_name}
                print(f"🪣 S3 Bucket: {bucket_name}")
            except ClientError:
                print(f"🪣 S3 Bucket: Not found")
            
            # Check IAM role
            role_name = instance_name
            try:
                self.iam_client.get_role(RoleName=role_name)
                resources['iam_role'] = {'name': role_name}
                print(f"👤 IAM Role: {role_name}")
            except ClientError:
                print(f"👤 IAM Role: Not found")
            
            # Check IAM policy
            policy_name = instance_name
            try:
                self.iam_client.get_policy(PolicyArn=f"arn:aws:iam::{self.get_account_id()}:policy/{policy_name}")
                resources['iam_policy'] = {'name': policy_name}
                print(f"👤 IAM Policy: {policy_name}")
            except ClientError:
                print(f"👤 IAM Policy: Not found")
            
            # Check IAM instance profile
            instance_profile_name = instance_name
            try:
                self.iam_client.get_instance_profile(InstanceProfileName=instance_profile_name)
                resources['iam_instance_profile'] = {'name': instance_profile_name}
                print(f"👤 IAM Instance Profile: {instance_profile_name}")
            except ClientError:
                print(f"👤 IAM Instance Profile: Not found")
            
            # Check Elastic IP
            elastic_ip_info = self.find_elastic_ip_by_instance_name(instance_name)
            if elastic_ip_info:
                resources['elastic_ip'] = {
                    'allocation_id': elastic_ip_info['allocation_id'],
                    'public_ip': elastic_ip_info['public_ip'],
                    'instance_id': elastic_ip_info.get('instance_id')
                }
                print(f"🌐 Elastic IP: {elastic_ip_info['allocation_id']} ({elastic_ip_info['public_ip']})")
            else:
                print(f"🌐 Elastic IP: Not found")
            
            print("=" * 60)
            return resources
            
        except Exception as e:
            print(f"❌ Error listing resources: {e}")
            raise

    def create_infrastructure(self, instance_name=None, instance_type='t3.micro', attach_static_ip=False):
        """Create complete infrastructure for the instance name.
        
        Note: This method creates paid AWS resources. Free Tier restrictions do not apply.
        Supports any instance type including paid resources (t3.medium, t3.large, m5.large, etc.).
        If you encounter Free Tier errors, ensure your AWS account allows paid resources.
        
        Args:
            instance_name: Name for the instance
            instance_type: EC2 instance type (default: t3.micro)
                          Supports any instance type including paid resources
            attach_static_ip: Whether to allocate and attach an Elastic IP (default: False)
        """
        if instance_name is None:
            # If no instance name provided, we need a base name to find next available
            # For now, we'll require instance_name to be provided
            print("❌ Instance name is required for create-infrastructure action")
            raise ValueError("Instance name is required")
        
        # Check if instance_name has a suffix, if not, find next available
        match = re.search(r'^(.+)-(\d+)$', instance_name)
        if not match:
            # No suffix found, find next available
            instance_name = self.find_next_instance_name(instance_name)
        
        print(f"🚀 Starting Infrastructure Creation")
        print("=" * 70)
        
        try:
            # Create key pair
            key_name, key_file = self.create_key_pair(instance_name)
            
            # Create S3 bucket
            bucket_name = self.create_s3_bucket(instance_name)
            
            # Create security group
            security_group_id = self.create_security_group(instance_name)
            
            # Create IAM role and policy
            instance_profile_name = self.create_iam_role_and_policy(instance_name)
            
            # Create EC2 instance
            instance_id, public_ip, availability_zone = self.create_ec2_instance(
                instance_name, key_name, security_group_id, instance_profile_name, instance_type
            )
            
            # Create or reuse EBS volume
            volume_id = self.create_or_reuse_ebs_volume(instance_name, availability_zone)
            
            # Attach EBS volume
            self.attach_ebs_volume(volume_id, instance_id)
            
            # Allocate and associate Elastic IP if requested
            elastic_ip_allocation_id = None
            elastic_ip = None
            if attach_static_ip:
                elastic_ip_allocation_id, elastic_ip = self.allocate_elastic_ip(instance_name)
                # Wait a moment for instance to be fully ready
                time.sleep(2)
                static_public_ip = self.associate_elastic_ip(elastic_ip_allocation_id, instance_id)
                if static_public_ip:
                    elastic_ip = static_public_ip
                    public_ip = static_public_ip  # Update public_ip for summary
            
            # Summary
            print("\n" + "=" * 70)
            print("🎉 INFRASTRUCTURE CREATION COMPLETE!")
            print("=" * 70)
            print(f"📋 Instance Name: {instance_name}")
            print(f"🔑 Key Pair: {key_name}")
            print(f"📁 Key File: {key_file}")
            print(f"🪣 S3 Bucket: {bucket_name}")
            print(f"🛡️ Security Group: {security_group_id}")
            print(f"👤 IAM Role: {instance_name}")
            print(f"👤 IAM Instance Profile: {instance_profile_name}")
            print(f"🖥️ EC2 Instance: {instance_id}")
            print(f"💾 EBS Volume: {volume_id} (30 GiB gp3)")
            if attach_static_ip and elastic_ip:
                print(f"🌐 Static Public IP (Elastic IP): {elastic_ip}")
                print(f"🆔 Elastic IP Allocation ID: {elastic_ip_allocation_id}")
            else:
                print(f"🌐 Public IP: {public_ip}")
            if public_ip:
                # Use just the filename for SSH command (not full path)
                key_filename = os.path.basename(key_file)
                print(f"🔗 SSH Command: ssh -i {key_file} ec2-user@{public_ip}")
                print(f"   Or from pems directory: ssh -i {key_filename} ec2-user@{public_ip}")
            print("=" * 70)
            
            return {
                'instance_name': instance_name,
                'key_name': key_name,
                'key_file': key_file,
                'bucket_name': bucket_name,
                'security_group_id': security_group_id,
                'instance_profile_name': instance_profile_name,
                'instance_id': instance_id,
                'volume_id': volume_id,
                'public_ip': public_ip,
                'elastic_ip_allocation_id': elastic_ip_allocation_id,
                'elastic_ip': elastic_ip
            }
            
        except Exception as e:
            print(f"❌ Error creating infrastructure: {e}")
            raise


def main():
    """Main function to manage AWS resources."""
    
    parser = argparse.ArgumentParser(description='Unified AWS Resource Manager')
    parser.add_argument('--action', '-a', required=True, 
                       choices=['list-instances', 'start-instance', 'stop-instance', 
                               'list-volumes', 'destroy-volume-by-name', 'destroy-volume-by-id',
                               'create-infrastructure', 'destroy-infrastructure', 'list-resources'],
                       help='Action to perform')
    parser.add_argument('--instance_name', '-i', type=str,
                       help='Instance name (e.g., jalusi-db-1)')
    parser.add_argument('--volume-id', '-v', type=str,
                       help='Volume ID for direct volume operations')
    parser.add_argument('--region', '-r', default='af-south-1', 
                       help='AWS region (default: af-south-1)')
    parser.add_argument('--filter', '-f', 
                       help='Filter resources by name pattern')
    parser.add_argument('--instance-type', '-t', type=str, default='t3.micro',
                       help='EC2 instance type (default: t3.micro)')
    parser.add_argument('--attach_static_ip', action='store_true',
                       help='Allocate and attach an Elastic IP address to the instance (for create-infrastructure action)')
    
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
            # Get project root directory (go up from services/resource_manager/)
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
    
    print("🔧 Unified AWS Resource Manager")
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
    
    # Test credentials by trying to get account ID
    print("🔍 Testing AWS credentials...")
    try:
        print(f"🔍 Testing AWS credentials: {AWS_ACCESS_KEY_ID} and {AWS_SECRET_ACCESS_KEY}")
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
            region_name=args.region
        )
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        account_id = response['Account']
        user_arn = response['Arn']
        print(f"✅ Credentials validated successfully!")
        print(f"   Account ID: {account_id}")
        print(f"   User ARN: {user_arn}")
    except Exception as e:
        print(f"❌ Credential validation failed: {e}")
        print("   Please check your AWS credentials and permissions.")
        print("   Required permissions: ec2:*, s3:*, iam:*, sts:GetCallerIdentity")
        return
    
    try:
        if args.action in ['list-instances', 'start-instance', 'stop-instance']:
            # EC2 Instance Management
            manager = EC2InstanceManager(
                region_name=args.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            
            if args.action == 'list-instances':
                manager.list_all_instances(filter_pattern=args.filter)
            elif args.action == 'start-instance':
                if not args.instance_name:
                    print("❌ Instance name is required for start-instance action")
                    print("   Example: --instance_name jalusi-db-1")
                    return
                manager.start_instance(args.instance_name)
            elif args.action == 'stop-instance':
                if not args.instance_name:
                    print("❌ Instance name is required for stop-instance action")
                    print("   Example: --instance_name jalusi-db-1")
                    return
                manager.stop_instance(args.instance_name)
        
        elif args.action in ['list-volumes', 'destroy-volume-by-name', 'destroy-volume-by-id']:
            # EBS Volume Management
            manager = EBSVolumeManager(
                region_name=args.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            
            if args.action == 'list-volumes':
                manager.list_all_volumes(filter_pattern=args.filter)
            elif args.action == 'destroy-volume-by-name':
                if not args.instance_name:
                    print("❌ Instance name is required for destroy-volume-by-name action")
                    print("   Example: --instance_name jalusi-db-1")
                    return
                manager.destroy_volume_by_name(args.instance_name)
            elif args.action == 'destroy-volume-by-id':
                if not args.volume_id:
                    print("❌ Volume ID is required for destroy-volume-by-id action")
                    return
                manager.destroy_volume_by_volume_id(args.volume_id)
        
        elif args.action == 'create-infrastructure':
            # Infrastructure Management
            manager = InfrastructureManager(
                region_name=args.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            
            # If no instance name provided, auto-find the next available one
            instance_name = args.instance_name
            manager.create_infrastructure(instance_name, args.instance_type, attach_static_ip=args.attach_static_ip)
        
        elif args.action == 'destroy-infrastructure':
            # Infrastructure Management
            manager = InfrastructureManager(
                region_name=args.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            
            if not args.instance_name:
                print("❌ Instance name is required for destroy-infrastructure action")
                print("   Example: --instance_name jalusi-db-1")
                return
            
            manager.destroy_infrastructure(args.instance_name)
        
        elif args.action == 'list-resources':
            # Infrastructure Management
            manager = InfrastructureManager(
                region_name=args.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            
            if not args.instance_name:
                print("❌ Instance name is required for list-resources action")
                print("   Example: --instance_name jalusi-db-1")
                return
            
            manager.list_resources_by_instance_name(args.instance_name)

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your AWS credentials are correct and have the required permissions.")


if __name__ == "__main__":
    main()

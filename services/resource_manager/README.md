# Learnly Production Infrastructure Manager

A comprehensive AWS infrastructure automation toolkit that creates and destroys complete EC2 environments with the `learnly-prod-<sequence_number>` naming pattern.

## 📦 Included Scripts

- **`unified_resource_manager.py`** - Unified AWS resource management for EC2 instances, EBS volumes, and infrastructure with enhanced volume destruction capabilities

## 🎯 Overview

This unified script provides comprehensive AWS resource management for Learnly production environments, including:

- **EC2 Instance** with Amazon Linux 2023 (8GiB gp3 root volume)
- **EBS Volume** (gp3, 8GiB) - reuses existing volumes if found
- **S3 Bucket** for data storage
- **EC2 Key Pair** for SSH access
- **Security Group** with proper network rules
- **IAM Role, Policy, and Instance Profile** for S3 access
- **Automatic sequence numbering** to avoid naming conflicts

## 🚀 Features

### ✅ **EC2 Instance Management**
- **List Instances**: List all EC2 instances with their statuses and details
- **Start Instances**: Start stopped EC2 instances by sequence number
- **Stop Instances**: Stop running EC2 instances by sequence number
- **Elastic IP Detection**: Automatically detects and displays associated Elastic IPs
- **SSH Command Generation**: Provides ready-to-use SSH commands with correct IP addresses
- **Status Monitoring**: Real-time instance state tracking with visual indicators

### ✅ **EBS Volume Management**
- **List Volumes**: List all EBS volumes with their statuses and details
- **Destroy Volumes by Sequence**: Destroy EBS volumes by sequence number
- **Destroy Volumes by ID**: Destroy EBS volumes by direct volume ID
- **Volume Discovery**: Find volumes by sequence number and naming pattern
- **Status Monitoring**: Track volume states and attachment information
- **Enhanced Volume Information**: Show detailed volume information (name, size, type, attachment status) before destruction
- **Safety Checks**: Verify volume state and attachment status before deletion
- **Flexible Destruction**: Choose between sequence-based or direct volume ID destruction

### ✅ **Infrastructure Operations**
- **Resource Discovery**: Find all learnly-prod resources across sequence numbers
- **Complete Infrastructure Management**: Create and destroy complete infrastructure stacks
- **Smart Resource Management**: Checks for existing resources, handles duplicates gracefully
- **Security Best Practices**: Least privilege IAM policies, secure configurations

### ✅ **Resource Types Managed**
- **EC2 Instance**: t3.medium with Amazon Linux 2023 (kernel-6.1)
- **Root Volume**: gp3, 8GiB, mounted as /dev/xvda (DeleteOnTermination: False)
- **EBS Volume**: gp3, 8GiB, mounted as /dev/sdf (reused if exists)
- **S3 Bucket**: With versioning enabled and all objects
- **Security Group**: Opens ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **IAM Resources**: Role, Policy, and Instance Profile for S3 access
- **Key Pair**: Private key saved locally for SSH access

## 📋 Prerequisites

### **AWS Credentials**
You need valid AWS credentials with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "s3:*",
                "iam:*",
                "vpc:*"
            ],
            "Resource": "*"
        }
    ]
}
```

### **Required Permissions**
- **EC2**: Create instances, key pairs, security groups
- **S3**: Create buckets, manage versioning
- **IAM**: Create roles, policies, instance profiles
- **VPC**: Access default VPC for security groups

### **Python Dependencies**
```bash
pip install boto3
```

## 🛠️ Installation

1. **Clone or download the script**
2. **Install dependencies**:
   ```bash
   pip install boto3
   ```
3. **Configure AWS credentials** (see Configuration section)
4. **Run the script**:
   ```bash
   python create_ec2_with_credentials.py
   ```

## ⚙️ Configuration

### **AWS Credentials Setup**

⚠️ **WARNING**: Never commit real AWS credentials to version control!

#### **Option 1: Hardcoded Credentials (Development Only)**
Update the credentials in the script:

```python
AWS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_SECRET_ACCESS_KEY"
AWS_SESSION_TOKEN = None  # Optional, for temporary credentials
AWS_REGION = "eu-west-1"  # Change to your preferred region
```

#### **Option 2: Environment Variables (Recommended)**
Set environment variables:

```bash
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_DEFAULT_REGION="eu-west-1"
```

#### **Option 3: AWS CLI Configuration**
```bash
aws configure
```

### **Region Configuration**
The script defaults to `eu-west-1`. To change the region:

1. Update `AWS_REGION` in the script, or
2. Set `AWS_DEFAULT_REGION` environment variable, or
3. Configure via AWS CLI

## 📖 Usage

### **EC2 Instance Management**

#### **List All Instances**
```bash
python unified_resource_manager.py --action list-instances
# or with filter
python unified_resource_manager.py --action list-instances --filter learnly-prod
```

#### **Start Instance**
```bash
python unified_resource_manager.py --action start-instance --sequence 1
# or
python unified_resource_manager.py --action start-instance --sequence 2
```

#### **Stop Instance**
```bash
python unified_resource_manager.py --action stop-instance --sequence 1
# or
python unified_resource_manager.py --action stop-instance --sequence 2
```

#### **Different Region**
```bash
python unified_resource_manager.py --action start-instance --sequence 1 --region us-east-1
python unified_resource_manager.py --action stop-instance --sequence 1 --region us-east-1
```

### **EBS Volume Management**

#### **List All Volumes**
```bash
python unified_resource_manager.py --action list-volumes
# or with filter
python unified_resource_manager.py --action list-volumes --filter learnly-prod
```

#### **Destroy Volume by Sequence Number**
```bash
python unified_resource_manager.py --action destroy-volume-by-sequence --sequence 1
# or
python unified_resource_manager.py --action destroy-volume-by-sequence --sequence 2
```

#### **Destroy Volume by Volume ID**
```bash
python unified_resource_manager.py --action destroy-volume-by-id --volume-id vol-1234567890abcdef0
# or
python unified_resource_manager.py --action destroy-volume-by-id --volume-id vol-0987654321fedcba0
```

### **Enhanced Volume Destruction Features**

The volume destruction methods now provide enhanced functionality:

#### **Detailed Volume Information Display**
Before destroying a volume, the script shows comprehensive information:
- **Volume Name**: Human-readable name from tags
- **Volume ID**: AWS volume identifier
- **State**: Current volume state (available, in-use, deleted, etc.)
- **Size**: Volume size in GiB
- **Type**: Volume type (gp3, io2, etc.)
- **Attachment Status**: Which instance the volume is attached to (if any)

#### **Safety Checks**
- **Attachment Detection**: Prevents destruction of attached volumes
- **State Validation**: Checks if volume is already deleted
- **Error Handling**: Graceful handling of missing or invalid volumes

#### **Example Output**
```
🔍 Looking for volume: vol-1234567890abcdef0
📋 Volume Details:
   Name: learnly-prod-1
   ID: vol-1234567890abcdef0
   State: available
   Size: 8 GiB
   Type: gp3
🗑️  Destroying volume vol-1234567890abcdef0...
⏳ Waiting for volume to be deleted...
✅ Volume vol-1234567890abcdef0 (learnly-prod-1) destroyed successfully!
```

### **Infrastructure Operations**

#### **Create Infrastructure**
```bash
python unified_resource_manager.py --action create-infrastructure --sequence 1
```

#### **Destroy Infrastructure**
```bash
python unified_resource_manager.py --action destroy-infrastructure --sequence 1
```

#### **List All Resources**
```bash
python unified_resource_manager.py --action list-resources
```

#### **What Happens When You Destroy**

1. **🌐 Elastic IP Release**: Disassociates and releases the Elastic IP
2. **🖥️ EC2 Instance Termination**: Terminates and waits for completion (root volume preserved)
3. **🪣 S3 Bucket Deletion**: Removes all objects and the bucket
4. **🔑 Key Pair Deletion**: Removes AWS key pair and local `.pem` file
5. **🛡️ Security Group Deletion**: Removes the security group
6. **👤 IAM Resources Deletion**: Removes role, policy, and instance profile (in proper order)

#### **EBS Volume Management**

**Important**: EBS volumes are **preserved** when destroying EC2 instances. This allows you to:
- Reuse data across instance recreations
- Prevent accidental data loss
- Maintain persistent storage

**To destroy EBS volumes separately**:
```bash
# List all EBS volumes
python unified_resource_manager.py --action list-volumes

# Destroy specific EBS volume by sequence number
python unified_resource_manager.py --action destroy-volume-by-sequence --sequence 1

# Destroy specific EBS volume by volume ID
python unified_resource_manager.py --action destroy-volume-by-id --volume-id vol-1234567890abcdef0

# Note: EBS volumes must be detached before destruction
```

### **Example Creation Output**
```
🔧 Learnly Production Infrastructure Creator
============================================================
⚠️  WARNING: This is for development/testing only!
   Never commit real AWS credentials to version control.
============================================================

✅ Connected to AWS in region: eu-west-1

🚀 Starting Learnly Production Infrastructure Creation
======================================================================

🔍 Finding next sequence number for learnly-prod instances...
📊 Found existing sequence numbers: [1, 2, 3]
🎯 Next sequence number: 4

🔑 Creating key pair: learnly-prod-4
✅ Key pair created successfully!
📁 Private key saved to: learnly-prod-4.pem

🪣 Creating S3 bucket: learnly-prod-4
✅ S3 bucket created successfully!

🛡️ Creating security group: learnly-prod-4
✅ Security group created successfully!

👤 Creating IAM role: learnly-prod-4
✅ IAM role, policy, and instance profile created successfully!

🖥️ Creating EC2 instance: learnly-prod-4
📦 Using AMI: ami-0c55b3c78fc1b9e0a
✅ EC2 instance created successfully!
🆔 Instance ID: i-1234567890abcdef0
⏳ Waiting for instance to be running...
🌐 Public IP: 34.252.123.188
📍 Availability Zone: eu-west-1a

🔍 Looking for existing EBS volume: learnly-prod-4
✅ Found existing EBS volume: vol-1234567890abcdef0 (State: available)
✅ Using existing EBS volume: vol-1234567890abcdef0

🔗 Attaching EBS volume vol-1234567890abcdef0 to instance i-1234567890abcdef0
✅ EBS volume attachment initiated!
🔗 Device: /dev/sdf
📊 State: attaching
⏳ Waiting for EBS volume attachment to complete...
✅ EBS volume attached successfully!

======================================================================
🎉 INFRASTRUCTURE CREATION COMPLETE!
======================================================================
📋 Sequence Number: 4
🔑 Key Pair: learnly-prod-4
📁 Key File: learnly-prod-4.pem
🪣 S3 Bucket: learnly-prod-4
🛡️ Security Group: sg-1234567890abcdef0
👤 IAM Role: learnly-prod-4
👤 IAM Instance Profile: learnly-prod-4
🖥️ EC2 Instance: i-1234567890abcdef0
💾 EBS Volume: vol-1234567890abcdef0 (8 GiB gp3)
🌐 Public IP: 34.252.123.188
🔗 SSH Command: ssh -i learnly-prod-4.pem ec2-user@34.252.123.188
======================================================================
```

### **Example Destruction Output**
```
💥 Learnly Production Infrastructure Destroyer
============================================================
⚠️  WARNING: This is for development/testing only!
   Never commit real AWS credentials to version control.
============================================================

✅ Connected to AWS in region: af-south-1
🗑️  Destroying infrastructure for sequence: 1

💥 Starting Learnly Production Infrastructure Destruction for sequence: 1
======================================================================

🖥️  Looking for EC2 instance: learnly-prod-1
🖥️  Found instance: i-1234567890abcdef0 (State: running)
🗑️  Terminating instance: i-1234567890abcdef0
⏳ Waiting for instance to terminate...
✅ Instance i-1234567890abcdef0 terminated successfully!

💾 Looking for EBS volume: learnly-prod-1
💾 Found EBS volume: vol-1234567890abcdef0 (State: available)
🗑️  Deleting EBS volume: vol-1234567890abcdef0
⏳ Waiting for EBS volume deletion to complete...
✅ EBS volume vol-1234567890abcdef0 deleted successfully!

🪣 Looking for S3 bucket: learnly-prod-1
🗑️  Deleting all objects in bucket: learnly-prod-1
🗑️  Deleting bucket: learnly-prod-1
✅ S3 bucket learnly-prod-1 deleted successfully!

🔑 Looking for key pair: learnly-prod-1
🗑️  Deleting key pair: learnly-prod-1
✅ Key pair learnly-prod-1 deleted successfully!
🗑️  Deleted local key file: learnly-prod-1.pem

🛡️  Looking for security group: learnly-prod-1
🗑️  Deleting security group: learnly-prod-1 (sg-1234567890abcdef0)
✅ Security group learnly-prod-1 deleted successfully!

👤 Looking for IAM resources for sequence: 1
🗑️  Deleting IAM instance profile: learnly-prod-1
✅ IAM instance profile learnly-prod-1 deleted successfully!
🔗 Detaching policy from role: learnly-prod-1 -> learnly-prod-1
✅ Policy learnly-prod-1 detached from role learnly-prod-1
🗑️  Deleting IAM role: learnly-prod-1
✅ IAM role learnly-prod-1 deleted successfully!
🗑️  Deleting IAM policy: learnly-prod-1
✅ IAM policy learnly-prod-1 deleted successfully!

======================================================================
🎉 INFRASTRUCTURE DESTRUCTION COMPLETE!
======================================================================
📋 Sequence Number: 1
🖥️  EC2 Instance: i-1234567890abcdef0 (terminated)
🪣 S3 Bucket: learnly-prod-1 (deleted)
🔑 Key Pair: learnly-prod-1 (deleted)
🛡️  Security Group: sg-1234567890abcdef0 (deleted)
👤 IAM Resources: instance_profile:learnly-prod-1, role:learnly-prod-1, policy:learnly-prod-1 (deleted)
======================================================================

✅ Infrastructure destruction completed successfully!
```

### **Example Start/Stop Output**

#### **List Instances**
```
🚀 Learnly Production EC2 Instance Starter
============================================================
⚠️  WARNING: This is for development/testing only!
   Never commit real AWS credentials to version control.
============================================================

✅ Connected to AWS in region: af-south-1

🔍 Scanning for all learnly-prod instances...
📊 Found learnly-prod instances:
  🟢 learnly-prod-1 (ID: i-1234567890abcdef0, State: running)
  🔴 learnly-prod-2 (ID: i-0987654321fedcba0, State: stopped)
  🟡 learnly-prod-3 (ID: i-abcdef1234567890, State: pending)

📊 Available sequence numbers:
  - learnly-prod-1
  - learnly-prod-2
  - learnly-prod-3
```

#### **Start Instance**
```
🚀 Starting instance for sequence: 2
🔍 Looking for instance: learnly-prod-2
✅ Found instance: i-0987654321fedcba0 (State: stopped)
🚀 Starting instance: i-0987654321fedcba0
⏳ Waiting for instance to start...
✅ Instance i-0987654321fedcba0 started successfully!
🌐 Elastic IP: 34.252.123.189
🔗 SSH Command: ssh -i learnly-prod-2.pem ec2-user@34.252.123.189

✅ Instance started successfully!
🆔 Instance ID: i-0987654321fedcba0
📋 Name: learnly-prod-2
🔄 State: running
🌐 Elastic IP: 34.252.123.189
```

#### **Stop Instance**
```
🛑 Stopping instance for sequence: 1
🔍 Looking for instance: learnly-prod-1
✅ Found instance: i-1234567890abcdef0 (State: running)
🛑 Stopping instance: i-1234567890abcdef0
⏳ Waiting for instance to stop...
✅ Instance i-1234567890abcdef0 stopped successfully!

✅ Instance stopped successfully!
🆔 Instance ID: i-1234567890abcdef0
📋 Name: learnly-prod-1
🔄 State: stopped
```

## 🏗️ Infrastructure Details

### **EC2 Instance Specifications**
- **Instance Type**: t3.medium (2 vCPU, 4 GB RAM)
- **AMI**: Latest Amazon Linux 2023 (kernel-6.1)
- **Storage**: 8 GiB gp3 root volume
- **Network**: Default VPC with public IP

### **Root Volume Specifications**
- **Volume Type**: gp3 (General Purpose SSD)
- **Size**: 8 GiB
- **Device Name**: /dev/xvda
- **Availability Zone**: Same as EC2 instance
- **Performance**: 3,000 IOPS baseline, 125 MiB/s baseline throughput
- **Encryption**: Uses default AWS managed encryption
- **Delete on Termination**: No (preserved when instance is terminated)

### **EBS Volume Specifications**
- **Volume Type**: gp3 (General Purpose SSD)
- **Size**: 8 GiB
- **Device Name**: /dev/sdf
- **Availability Zone**: Same as EC2 instance
- **Performance**: 3,000 IOPS baseline, 125 MiB/s baseline throughput
- **Encryption**: Uses default AWS managed encryption
- **Reuse Logic**: Checks for existing volume with same name, reuses if found

### **Security Group Rules**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | 0.0.0.0/0 | SSH Access |
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |

### **S3 Bucket Configuration**
- **Versioning**: Enabled
- **Region**: Same as EC2 instance
- **Access**: EC2 instance has full access via IAM role

### **IAM Role Permissions**
The EC2 instance gets the following S3 permissions:
- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`
- `s3:ListBucket`

## 🔧 Customization

### **Modifying Instance Type**
Edit the `create_ec2_instance` method:

```python
InstanceType='t3.large'  # Change from t3.medium
```

### **Adding Additional Security Group Rules**
Edit the `create_security_group` method:

```python
{
    'IpProtocol': 'tcp',
    'FromPort': 8080,
    'ToPort': 8080,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
}
```

### **Changing AMI**
Edit the AMI filter in `create_ec2_instance`:

```python
{'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-22.04-*']}
```

### **Modifying EBS Volume Configuration**
Edit the `create_ebs_volume` method:

```python
# Change volume size (in GiB)
Size=16,  # Change from 8 to 16 GiB

# Change volume type
VolumeType='io2',  # Change from gp3 to io2 for higher performance

# Change device name
Device='/dev/sdg'  # Change from /dev/sdf to /dev/sdg
```

### **EBS Volume Management**
After creation, you can manage the EBS volume:

```bash
# SSH into the instance
ssh -i learnly-prod-1.pem ec2-user@<elastic-ip>

# Check if volume is attached
lsblk

# Format the volume (if needed)
sudo mkfs -t xfs /dev/xvdf

# Mount the volume
sudo mkdir /mnt/data
sudo mount /dev/xvdf /mnt/data

# Make mount permanent (add to /etc/fstab)
echo "/dev/xvdf /mnt/data xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab
```

## 🚨 Troubleshooting

### **Common Issues**

#### **1. Credentials Error**
```
❌ AWS credentials not found. Please configure your AWS credentials.
```
**Solution**: Set up AWS credentials using one of the methods in the Configuration section.

#### **2. Permission Denied**
```
❌ Error creating EC2 instance: An error occurred (UnauthorizedOperation)
```
**Solution**: Ensure your AWS user has the required permissions listed in Prerequisites.

#### **3. Duplicate Resource Names**
```
⚠️ Key pair learnly-prod-4 already exists
```
**Solution**: The script handles this automatically by using existing resources.

#### **4. VPC Not Found**
```
❌ Error creating security group: An error occurred (VPCIdNotSpecified)
```
**Solution**: Ensure you have a default VPC in your AWS region.

#### **5. IAM Instance Profile Not Available**
```
❌ Error creating EC2 instance: Invalid IAM Instance Profile name
```
**Solution**: The script includes automatic retry logic and fallback mechanisms.

#### **6. Destruction Order Issues**
```
❌ Error destroying IAM role: Cannot delete entity, must detach all policies first
```
**Solution**: The destroy script handles dependencies automatically in the correct order.

### **Debug Mode**
Both scripts include comprehensive logging. Check the output for specific error messages and progress indicators.

## 🧹 Cleanup

### **Automated Cleanup (Recommended)**
Use the included destroy script for complete and safe cleanup:

```bash
# List all available sequences
python destroy_ec2_with_credentials.py --list

# Destroy specific sequence
python destroy_ec2_with_credentials.py --sequence 1
```

### **Manual Cleanup (Alternative)**
If you prefer manual cleanup, follow this order:

1. **Terminate EC2 Instance**:
   ```bash
   aws ec2 terminate-instances --instance-ids i-1234567890abcdef0
   ```

2. **Delete S3 Bucket**:
   ```bash
   aws s3 rb s3://learnly-prod-4 --force
   ```

3. **Delete Key Pair**:
   ```bash
   aws ec2 delete-key-pair --key-name learnly-prod-4
   ```

4. **Delete Security Group**:
   ```bash
   aws ec2 delete-security-group --group-id sg-1234567890abcdef0
   ```

5. **Delete IAM Resources** (in order):
   ```bash
   aws iam delete-instance-profile --instance-profile-name learnly-prod-4
   aws iam delete-role --role-name learnly-prod-4
   aws iam delete-policy --policy-arn arn:aws:iam::ACCOUNT:policy/learnly-prod-4
   ```

### **Why Use the Automated Script?**
- ✅ **Safe deletion order**: Handles dependencies automatically
- ✅ **Complete cleanup**: Removes all associated resources
- ✅ **Local file cleanup**: Removes `.pem` files automatically
- ✅ **Error handling**: Graceful handling of missing resources
- ✅ **Progress tracking**: Real-time feedback on cleanup progress

## 🔒 Security Considerations

### **Best Practices**
- ✅ Use environment variables for credentials in production
- ✅ Regularly rotate AWS access keys
- ✅ Use IAM roles with least privilege
- ✅ Monitor and audit resource usage
- ✅ Enable CloudTrail for API logging

### **Network Security**
- 🔒 Security groups restrict access to necessary ports only
- 🔒 Consider using private subnets for production workloads
- 🔒 Implement proper firewall rules
- 🔒 Use VPN or bastion hosts for secure access

## 📝 File Structure

```
resource_manager/
├── README.md                           # This documentation
├── unified_resource_manager.py         # Unified AWS resource management script
└── learnly-prod-*.pem                  # Generated key files (auto-created)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is for internal use. Please ensure compliance with your organization's policies.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section
2. Review AWS documentation
3. Contact your AWS administrator
4. Check CloudTrail logs for detailed error information

---

**⚠️ Important**: These scripts are designed for development and testing environments. For production use, consider using Infrastructure as Code tools like AWS CloudFormation, Terraform, or AWS CDK for better resource management and version control.

## 🎯 Quick Start Guide

### **List and Manage Instances**
```bash
# 1. Configure AWS credentials
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"

# 2. List all instances
python unified_resource_manager.py --action list-instances

# 3. Start specific instance
python unified_resource_manager.py --action start-instance --sequence 1

# 4. Stop specific instance
python unified_resource_manager.py --action stop-instance --sequence 1
```

### **Manage EBS Volumes**
```bash
# 1. List all volumes
python unified_resource_manager.py --action list-volumes

# 2. Destroy specific volume by sequence number
python unified_resource_manager.py --action destroy-volume-by-sequence --sequence 1

# 3. Destroy specific volume by volume ID
python unified_resource_manager.py --action destroy-volume-by-id --volume-id vol-1234567890abcdef0
```

### **Infrastructure Operations**
```bash
# 1. Create infrastructure
python unified_resource_manager.py --action create-infrastructure --sequence 1

# 2. List all resources
python unified_resource_manager.py --action list-resources

# 3. Destroy infrastructure
python unified_resource_manager.py --action destroy-infrastructure --sequence 1
```

### **Complete Workflow Example**
```bash
# List all instances
python unified_resource_manager.py --action list-instances
# Output: Shows all learnly-prod instances with their statuses

# Start specific instance
python unified_resource_manager.py --action start-instance --sequence 1
# Output: Instance learnly-prod-1 started with SSH: ssh -i learnly-prod-1.pem ec2-user@34.252.123.188

# Use the infrastructure...
ssh -i learnly-prod-1.pem ec2-user@34.252.123.188

# Stop instance when not in use (save costs)
python unified_resource_manager.py --action stop-instance --sequence 1
# Output: Instance learnly-prod-1 stopped

# Start instance when needed again
python unified_resource_manager.py --action start-instance --sequence 1
# Output: Instance learnly-prod-1 started with SSH: ssh -i learnly-prod-1.pem ec2-user@34.252.123.188

# Destroy when completely done
python unified_resource_manager.py --action destroy-infrastructure --sequence 1
# Output: All resources for learnly-prod-1 destroyed
```

### **Cost Optimization Workflow**
```bash
# List all instances to see what's running
python unified_resource_manager.py --action list-instances

# Stop instances you're not using
python unified_resource_manager.py --action stop-instance --sequence 2
python unified_resource_manager.py --action stop-instance --sequence 3

# Start only the instance you need
python unified_resource_manager.py --action start-instance --sequence 1
```

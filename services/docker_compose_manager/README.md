# 🐳 Unified Docker and Docker Compose Manager

A comprehensive Docker and Docker Compose management toolkit for Learnly Production EC2 instances with the `learnly-prod-<sequence_number>` naming pattern.

## 📦 Included Scripts

- **`unified_docker_manager.py`** - Unified Docker and Docker Compose management for EC2 instances

## 🎯 Overview

This script provides comprehensive Docker and Docker Compose management functionality for EC2 instances:

- **Docker Environment Management**: Build and setup Docker environment on EC2 instances
- **Docker Compose Operations**: Start/Stop/Restart services, build and deploy
- **Docker Cleanup and Maintenance**: Clean up unused resources, monitor disk usage
- **Service Management**: Manage individual services, view status and logs
- **System Information**: Docker system info, disk usage monitoring

## 🚀 Features

### ✅ **Docker Environment Management**
- **Automatic Installation**: Install Docker and Docker Compose on EC2 instances
- **Buildx Support**: Install/upgrade Docker Buildx (required for compose build)
- **Docker Restart**: Restart Docker daemon remotely
- **Configuration**: Configure Docker daemon for optimal performance
- **Verification**: Verify installations and system compatibility
- **SSH Integration**: Secure SSH connections to EC2 instances

### ✅ **Docker Compose Operations**
- **Service Lifecycle**: Start, stop, restart all or specific services
- **Build Management**: Build images when starting services
- **Log Management**: View logs with tail and follow options
- **Status Monitoring**: Real-time service status and system information

### ✅ **Docker Cleanup and Maintenance**
- **Resource Cleanup**: Remove unused containers, images, volumes, networks
- **Aggressive Cleanup**: Complete system cleanup (use with caution)
- **Disk Monitoring**: Monitor disk usage before and after cleanup
- **System Pruning**: Automated Docker system pruning

### ✅ **Service Management**
- **Individual Services**: Target specific services for operations
- **Service Status**: View detailed service status and resource usage
- **Log Access**: Access service logs with filtering options
- **Command Execution**: Execute commands in containers

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
                "ec2:DescribeInstances",
                "ec2:DescribeAddresses"
            ],
            "Resource": "*"
        }
    ]
}
```

### **Required Permissions**
- **EC2**: Describe instances and addresses
- **SSH Access**: SSH access to EC2 instances
- **Docker**: Docker and Docker Compose installation capabilities

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
   python unified_docker_manager.py --action build-env --sequence 1
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
AWS_REGION = "af-south-1"  # Change to your preferred region
```

#### **Option 2: Environment Variables (Recommended)**
Set environment variables:

```bash
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_DEFAULT_REGION="af-south-1"
```

#### **Option 3: AWS CLI Configuration**
```bash
aws configure
```

### **SSH Key Management**

SSH keys are automatically detected from:
1. **Primary Location**: `aws-handler/pems/learnly-prod-{sequence_number}.pem`
2. **Fallback Location**: `./learnly-prod-{sequence_number}.pem`
3. **Parent Directories**: Any parent directory's `pems/` folder

## 📖 Usage

### **Docker Environment Setup**

#### **Build Docker Environment**
```bash
# Install Docker and Docker Compose on EC2 instance
python unified_docker_manager.py --action build-env --instance_name jalusi-db-1

# Different region
python unified_docker_manager.py --action build-env --instance_name jalusi-db-1 --region us-east-1
```

#### **Install/Upgrade Docker Buildx**
```bash
# Install or upgrade Docker Buildx (fixes "compose build requires buildx 0.17 or later" error)
python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1

# Different region
python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1 --region us-east-1
```

#### **Restart Docker Daemon**
```bash
# Restart Docker daemon on EC2 instance
python unified_docker_manager.py --action restart-docker --instance_name jalusi-db-1

# Different region
python unified_docker_manager.py --action restart-docker --instance_name jalusi-db-1 --region us-east-1
```

#### **What Happens During Environment Setup**

1. **🔍 Instance Discovery**: Finds running EC2 instance by name
2. **🔑 SSH Connection**: Establishes secure SSH connection
3. **📦 System Update**: Updates system packages
4. **🐳 Docker Installation**: Installs Docker and Docker Compose
5. **🔧 Buildx Installation**: Installs Docker Buildx (required for compose build)
6. **⚙️ Configuration**: Configures Docker daemon for performance
7. **✅ Verification**: Verifies installations and system compatibility

### **Docker Compose Operations**

#### **Start Services**
```bash
# Start all services
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project

# Start with build
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --build

# Start specific service
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --service api

# Start with custom docker-compose path
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

#### **Stop Services**
```bash
# Stop all services
python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project

# Stop specific service
python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project --service db

# Stop with custom docker-compose path
python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

#### **Restart Services**
```bash
# Restart all services
python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project

# Restart specific service
python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project --service api

# Restart with custom docker-compose path
python unified_docker_manager.py --action restart --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

#### **View Logs**
```bash
# View all service logs
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project

# View specific service logs
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --service api

# View logs with custom tail
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --tail 50

# View logs with follow flag
python unified_docker_manager.py --action logs --follow --instance_name jalusi-db-1 --project_name learnly-project --service api --tail 50

# View logs with custom docker-compose path
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

#### **Check Status**
```bash
# Check service status
python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project

# Check status with custom docker-compose path
python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

### **Docker Cleanup and Maintenance**

#### **Standard Cleanup**
```bash
# Clean up unused Docker resources
python unified_docker_manager.py --action cleanup --sequence 1
```

#### **Aggressive Cleanup**
```bash
# Remove all Docker resources (use with caution)
python unified_docker_manager.py --action cleanup --sequence 1 --aggressive
```

#### **System Information**
```bash
# Get Docker system information
python unified_docker_manager.py --action info --sequence 1

# Check disk usage
python unified_docker_manager.py --action disk-usage --sequence 1
```

### **Example Output**

#### **Environment Setup**
```
🐳 Unified Docker and Docker Compose Manager
============================================================
⚠️  WARNING: This is for development/testing only!
   Never commit real AWS credentials to version control.
============================================================

✅ Connected to AWS in region: af-south-1

🔧 Building Docker environment for sequence 1
🔍 Looking for instance: learnly-prod-1
✅ Found instance: i-1234567890abcdef0 (State: running)
✅ Found SSH key: aws-handler/pems/learnly-prod-1.pem
🚀 Installing Docker and Docker Compose...
📋 Step 1/15: sudo yum update -y
✅ SSH command executed successfully
📋 Step 2/15: sudo yum install -y docker
✅ SSH command executed successfully
...
✅ Docker environment setup completed successfully!
```

#### **Service Management**
```
🚀 Starting Docker Compose services for sequence 1
🔍 Looking for instance: learnly-prod-1
✅ Found instance: i-1234567890abcdef0 (State: running)
✅ Found SSH key: aws-handler/pems/learnly-prod-1.pem
🔗 Executing SSH command on 34.252.123.188: cd ~/projects && docker-compose up -d
✅ SSH command executed successfully
📤 Output:
Creating network "projects_default" ... done
Creating projects_api_1 ... done
Creating projects_db_1 ... done
✅ Docker Compose services started successfully!
```

#### **Cleanup Operations**
```
🧹 Cleaning up Docker resources for sequence 1
🔍 Looking for instance: learnly-prod-1
✅ Found instance: i-1234567890abcdef0 (State: running)
✅ Found SSH key: aws-handler/pems/learnly-prod-1.pem
📊 Disk usage before cleanup:
Filesystem      Size  Used Avail Use% Mounted on
/dev/xvda1       20G   15G  4.5G  77% /
🐳 Docker system info:
Images Space Usage:
REPOSITORY          TAG                 SIZE                SHARED SIZE         UNIQUE SIZE         CONTAINERS
projects_api        latest              1.2GB               0B                  1.2GB               1
projects_db         latest              2.1GB               0B                  2.1GB               1
🧹 Executing cleanup commands...
🔧 Executing: docker container prune -f
✅ Cleanup command executed successfully
🔧 Executing: docker image prune -f
✅ Cleanup command executed successfully
📊 Disk usage after cleanup:
Filesystem      Size  Used Avail Use% Mounted on
/dev/xvda1       20G   12G  7.5G  62% /
✅ Docker cleanup completed!
```

## 🏗️ Infrastructure Details

### **Docker Installation**
- **Docker Version**: Latest stable version
- **Docker Compose**: Latest release from GitHub
- **Docker Buildx**: Latest version (0.17+) for compose build support
- **Configuration**: Optimized for performance and logging
- **User Permissions**: ec2-user added to docker group

### **Docker Compose Configuration**
- **Working Directory**: `~/projects/{project_name}/` (default) or custom path via `--docker_compose_file_path`
- **Compose File**: `docker-compose.yml`
- **Service Management**: Individual or all services
- **Log Management**: Configurable tail and follow options
- **Custom Path Support**: Use `--docker_compose_file_path` to specify a custom directory for docker-compose operations

### **Cleanup Operations**
- **Standard Cleanup**: Removes unused containers, images, volumes, networks
- **Aggressive Cleanup**: Removes all Docker resources (use with caution)
- **Disk Monitoring**: Before and after cleanup reporting
- **System Pruning**: Automated Docker system maintenance

## 🔧 Customization

### **Modifying Docker Installation**
Edit the `build_docker_environment` method:

```python
# Add custom Docker installation steps
docker_install_commands.extend([
    "sudo yum install -y docker-compose-plugin",
    "sudo systemctl enable docker-compose"
])
```

### **Adding Custom Docker Compose Commands**
Edit the Docker Compose methods:

```python
# Add custom compose commands
command = "cd ~/projects && docker-compose up -d --scale api=3"
```

### **Custom Cleanup Commands**
Edit the `docker_cleanup` method:

```python
# Add custom cleanup commands
cleanup_commands.extend([
    "docker builder prune -f",
    "docker system prune -a -f --volumes"
])
```

## 🚨 Troubleshooting

### **Common Issues**

#### **1. SSH Connection Failed**
```
❌ SSH connection failed: Connection refused
```
**Solutions:**
- Verify EC2 instance is running
- Check security group allows SSH (port 22)
- Ensure SSH key file exists and has correct permissions
- Verify IP address hasn't changed (use Elastic IP)

#### **2. Docker Installation Failed**
```
❌ Failed at step 5: sudo yum install -y docker
```
**Solutions:**
- Check instance has internet connectivity
- Verify yum repositories are accessible
- Ensure sufficient disk space
- Check instance permissions

#### **3. Docker Compose Command Failed**
```
❌ Failed to start Docker Compose services
```
**Solutions:**
- Verify Docker Compose is installed
- Check docker-compose.yml file exists in the project directory
- Ensure Docker daemon is running
- Check service configuration

#### **3a. Buildx Version Error**
```
compose build requires buildx 0.17 or later
```
**Solutions:**
- Install or upgrade Docker Buildx:
  ```bash
  python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1
  ```
- Or rebuild the entire Docker environment:
  ```bash
  python unified_docker_manager.py --action build-env --instance_name jalusi-db-1
  ```

#### **4. Cleanup Permission Issues**
```
⚠️ Cleanup command had issues: Permission denied
```
**Solutions:**
- Ensure user has Docker permissions
- Check Docker daemon is running
- Verify sudo access on the instance

### **Debug Mode**
The script includes comprehensive logging. Check the output for specific error messages and progress indicators.

## 🧹 Cleanup

### **Automated Cleanup (Recommended)**
Use the included cleanup functionality:

```bash
# Standard cleanup
python unified_docker_manager.py --action cleanup --sequence 1

# Aggressive cleanup (use with caution)
python unified_docker_manager.py --action cleanup --sequence 1 --aggressive
```

### **Manual Cleanup (Alternative)**
If you prefer manual cleanup on the EC2 instance:

```bash
# SSH into the instance
ssh -i learnly-prod-1.pem ec2-user@<elastic-ip>

# Standard cleanup
docker system prune -f

# Aggressive cleanup
docker system prune -a -f --volumes
```

## 🔒 Security Considerations

### **Best Practices**
- ✅ Use environment variables for credentials in production
- ✅ Regularly rotate AWS access keys
- ✅ Use IAM roles with least privilege
- ✅ Monitor and audit resource usage
- ✅ Enable CloudTrail for API logging

### **Docker Security**
- 🔒 Run containers as non-root users
- 🔒 Use specific image tags instead of latest
- 🔒 Regularly update Docker and images
- 🔒 Scan images for vulnerabilities
- 🔒 Use Docker secrets for sensitive data

## 📝 File Structure

```
manage_docker_compose/
├── README.md                           # This documentation
├── unified_docker_manager.py           # Unified Docker management script
└── learnly-prod-*.pem                  # SSH key files (auto-detected)
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
2. Review Docker documentation
3. Contact your system administrator
4. Check Docker logs for detailed error information

---

**⚠️ Important**: These scripts are designed for development and testing environments. For production use, consider using Infrastructure as Code tools like Docker Swarm, Kubernetes, or AWS ECS for better container orchestration and management.

## 🎯 Quick Start Guide

### **Setup Docker Environment**
```bash
# 1. Configure AWS credentials
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"

# 2. Build Docker environment
python unified_docker_manager.py --action build-env --instance_name jalusi-db-1

# 3. Verify installation
python unified_docker_manager.py --action info --instance_name jalusi-db-1

# 4. If you get "compose build requires buildx 0.17 or later" error, install Buildx:
python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1
```

### **Manage Docker Compose Services**
```bash
# 1. Start services
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project

# 2. Check status
python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project

# 3. View logs
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project

# 4. Stop services
python unified_docker_manager.py --action down --instance_name jalusi-db-1 --project_name learnly-project

# 5. Use custom docker-compose path
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --docker_compose_file_path /home/ec2-user/custom/path
```

### **Maintenance Operations**
```bash
# 1. Clean up resources
python unified_docker_manager.py --action cleanup --sequence 1

# 2. Check disk usage
python unified_docker_manager.py --action disk-usage --sequence 1

# 3. Restart services
python unified_docker_manager.py --action restart --sequence 1
```

### **Complete Workflow Example**
```bash
# Setup environment
python unified_docker_manager.py --action build-env --instance_name jalusi-db-1
# Output: Docker environment setup completed successfully!

# If Buildx is missing or outdated, install/upgrade it
python unified_docker_manager.py --action install-buildx --instance_name jalusi-db-1
# Output: Docker Buildx installation completed!

# Start services
python unified_docker_manager.py --action up --instance_name jalusi-db-1 --project_name learnly-project --build
# Output: Docker Compose services started successfully!

# Monitor services
python unified_docker_manager.py --action status --instance_name jalusi-db-1 --project_name learnly-project
# Output: Service status and resource usage

# View logs
python unified_docker_manager.py --action logs --instance_name jalusi-db-1 --project_name learnly-project --service api
# Output: Service logs

# Cleanup when done
python unified_docker_manager.py --action cleanup --instance_name jalusi-db-1
# Output: Docker cleanup completed!
```

---

**Last Updated**: December 2024  
**Version**: 1.0.0  
**Compatibility**: Python 3.7+, Docker 20.10+, Docker Compose 2.0+

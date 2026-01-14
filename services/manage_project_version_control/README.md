# 📁 Project Version Control Management

This directory contains scripts for managing project directory structures and version control on Learnly Production EC2 instances.

## 🎯 Overview

The Project Directory Creator automates the setup of development environments on EC2 instances by:
- SSH into EC2 instances with the naming pattern `learnly-prod-<sequence_number>`
- Installing and configuring Git
- Cloning GitHub repositories with proper authentication
- Setting up the complete project directory structure

## 📋 Included Scripts

### `create_project_repository.py`
**Main script for creating project directory structures on EC2 instances**

**Features:**
- 🔍 **Instance Discovery**: Finds EC2 instances by sequence number
- 🔑 **SSH Management**: Automatic SSH key detection and connection testing
- 📦 **Git Installation**: Checks and installs Git if needed
- 🔧 **Git Configuration**: Sets up Git for HTTPS access with GitHub
- 📥 **Repository Cloning**: Clones multiple repositories with authentication
- 🏗️ **Directory Structure**: Creates organized project layout
- 🔍 **Verification**: Validates the complete setup

### `update_project_directory.py`
**Script for updating existing project directories on EC2 instances**

**Features:**
- 🔄 **Repository Updates**: Pull latest changes from all repositories
- 🔧 **Git Maintenance**: Clean and optimize Git repositories
- 📦 **Dependency Updates**: Update project dependencies if needed
- 🔍 **Status Reporting**: Report on update status and changes

### `collect_static_files.py`
**Script for collecting and managing static files on EC2 instances**

**Features:**
- 📁 **Static File Collection**: Collect static files from project directories
- 🗂️ **File Organization**: Organize static files in proper directory structure
- 🔧 **File Processing**: Process and optimize static files
- 📊 **Collection Reporting**: Report on collected files and sizes

### `replace_nginx_conf_file.py`
**Script for managing Nginx configuration files on EC2 instances**

**Features:**
- ⚙️ **Configuration Management**: Replace Nginx configuration files
- 🔧 **Template Processing**: Process configuration templates with variables
- 🔄 **Service Reload**: Reload Nginx service after configuration changes
- ✅ **Validation**: Validate Nginx configuration before applying

### `generate_project_env.py`
**Script for generating environment files for projects**

**Features:**
- 🔧 **Environment Generation**: Generate .env files from templates
- 🔐 **Secret Management**: Handle sensitive configuration data
- 📝 **Template Processing**: Process environment templates with variables
- ✅ **Validation**: Validate generated environment configurations

### `deploy_project_env.py`
**Script for deploying project environments on EC2 instances**

**Features:**
- 🚀 **Environment Deployment**: Deploy complete project environments
- 🔧 **Configuration Management**: Manage all project configurations
- 📦 **Dependency Installation**: Install project dependencies
- 🔄 **Service Management**: Start and manage project services

## 🚀 Quick Start

### Prerequisites

1. **AWS Credentials**: Configured AWS credentials with EC2 access
2. **SSH Keys**: PEM files in `aws-handler/pems/` directory
3. **GitHub Token**: Personal Access Token in `aws-handler/pacs/learnly-pac.txt`

### Basic Usage

```bash
# List all available EC2 instances
python create_project_repository.py --list

# Create project directory structure for sequence 1
python create_project_repository.py --sequence 1

# Create project directory structure for sequence 2
python create_project_repository.py -s 2

# Use custom GitHub token
python create_project_repository.py -s 1 --github-token YOUR_TOKEN_HERE

# Update existing project directories
python update_project_directory.py --sequence 1

# Collect static files
python collect_static_files.py --sequence 1

# Replace Nginx configuration
python replace_nginx_conf_file.py --sequence 1 --config-type https

# Generate project environment
python generate_project_env.py --sequence 1 --environment production

# Deploy project environment
python deploy_project_env.py --sequence 1
```

## 📁 Directory Structure

### Expected File Layout
```
aws-handler/
├── pacs/
│   └── learnly-pac.txt          # GitHub Personal Access Token
├── pems/
│   ├── learnly-prod-1.pem       # SSH key for instance 1
│   ├── learnly-prod-2.pem       # SSH key for instance 2
│   └── ...                      # Additional SSH keys
└── services/
    └── manage_project_version_control/
        ├── README.md                    # This file
        ├── create_project_repository.py  # Create project directories
        ├── update_project_directory.py  # Update existing directories
        ├── collect_static_files.py      # Collect static files
        ├── replace_nginx_conf_file.py   # Manage Nginx configs
        ├── generate_project_env.py      # Generate environment files
        ├── deploy_project_env.py        # Deploy project environments
        └── nginx.conf/                  # Nginx configuration templates
            ├── nginx_http.conf
            └── nginx_https.conf
```

### Created Project Structure
```
~/learnly-project/ (on EC2 instance)
├── learnly-project/             # Main project files
├── learnly-api/                 # API submodule
└── learnly-web/                 # Web submodule
```

## 🔧 Configuration

### GitHub Token Setup

1. **Create Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token with `repo` permissions
   - Copy the token

2. **Save Token**:
   ```bash
   # Create the pacs directory
   mkdir -p aws-handler/pacs
   
   # Save the token to file
   echo "ghp_your_actual_token_here" > aws-handler/pacs/learnly-pac.txt
   ```

### SSH Key Management

SSH keys are automatically detected from:
1. **Primary Location**: `aws-handler/pems/learnly-prod-{sequence_number}.pem`
2. **Fallback Location**: `./learnly-prod-{sequence_number}.pem`

### AWS Credentials

The script reads AWS credentials from files (for development only):
```python
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
```

⚠️ **Security Note**: Replace with environment variables in production!

## 📚 Detailed Usage

### Command Line Arguments

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--sequence` | `-s` | Sequence number for EC2 instance | `--sequence 1` |
| `--list` | `-l` | List all available instances | `--list` |
| `--region` | `-r` | AWS region (default: af-south-1) | `--region us-east-1` |
| `--github-token` | `-t` | GitHub Personal Access Token | `--github-token ghp_xxx` |

### Workflow Steps

1. **Instance Discovery**: Finds running EC2 instance by sequence number
2. **SSH Key Check**: Locates and validates SSH key file
3. **Connection Test**: Tests SSH connectivity to the instance
4. **Git Installation**: Checks and installs Git if needed
5. **Git Configuration**: Sets up Git for HTTPS access
6. **Directory Cleanup**: Removes existing project directories
7. **Repository Cloning**: Clones all repositories with authentication
8. **Structure Verification**: Validates the complete setup

### Example Output

```
📁 Creating project directory structure for sequence: 1
======================================================================
🔍 Looking for instance: learnly-prod-1
✅ Found instance: i-1234567890abcdef0 (State: running)
✅ Found SSH key: aws-handler/pems/learnly-prod-1.pem
🔗 Testing SSH connection to 13.244.48.182...
✅ SSH connection successful!
📦 Checking Git installation...
✅ Git is installed: git version 2.37.1
🔧 Configuring Git for HTTPS access...
✅ Git HTTPS configuration completed
📁 Creating project directory structure...
✅ Base directory created: /home/ec2-user/learnly-project
🏗️  Setting up project structure...
📥 Cloning learnly-project...
✅ learnly-project cloned successfully
📥 Cloning learnly-api...
✅ learnly-api cloned successfully
📥 Cloning learnly-web...
✅ learnly-web cloned successfully
📋 Directory structure:
total 12
drwxr-xr-x 5 ec2-user ec2-user 4096 Dec 15 10:30 .
drwxr-xr-x 3 ec2-user ec2-user 4096 Dec 15 10:30 ..
drwxr-xr-x 8 ec2-user ec2-user 4096 Dec 15 10:30 learnly-api
drwxr-xr-x 8 ec2-user ec2-user 4096 Dec 15 10:30 learnly-project
drwxr-xr-x 8 ec2-user ec2-user 4096 Dec 15 10:30 learnly-web

======================================================================
🎉 PROJECT DIRECTORY CREATION COMPLETE!
======================================================================
📋 Sequence Number: 1
🖥️  Instance ID: i-1234567890abcdef0
📋 Instance Name: learnly-prod-1
🌐 IP Address: 13.244.48.182
🔗 SSH Command: ssh -i aws-handler/pems/learnly-prod-1.pem ec2-user@13.244.48.182

📁 Project Structure Created:
~/learnly-project/
├── learnly-project/ (main project files)
├── learnly-api/ (API submodule)
└── learnly-web/ (Web submodule)

✅ Project directories are ready for development!
💡 You can now SSH into the instance and start working on the projects
======================================================================
```

## 🔍 Troubleshooting

### Common Issues

#### SSH Connection Failed
```
❌ SSH connection failed: Connection refused
```
**Solutions:**
- Verify EC2 instance is running
- Check security group allows SSH (port 22)
- Ensure SSH key file exists and has correct permissions
- Verify IP address hasn't changed (use Elastic IP)

#### SSH Host Key Verification Failed
```
The authenticity of host '13.244.48.182' can't be established.
Host key verification failed.
```
**Solutions:**
- **Option 1**: Accept the host key manually first:
  ```bash
  ssh -i aws-handler/pems/learnly-prod-1.pem -o StrictHostKeyChecking=accept-new ec2-user@13.244.48.182
  ```
- **Option 2**: Add the host key to known_hosts:
  ```bash
  ssh-keyscan -H 13.244.48.182 >> ~/.ssh/known_hosts
  ```
- **Option 3**: Use the script's built-in host key bypass (already configured)

#### Git Clone Authentication Failed
```
❌ Failed to clone learnly-project: Authentication failed
```
**Solutions:**
- Check GitHub token is valid and has `repo` permissions
- Verify token file exists: `aws-handler/pacs/learnly-pac.txt`
- Ensure repositories are accessible with the provided token

#### Directory Already Exists
```
❌ Failed to clone learnly-project: destination path already exists
```
**Solutions:**
- The script automatically cleans up existing directories
- If issues persist, manually remove directories on the EC2 instance

#### AWS Credentials Error
```
❌ AWS credentials not found
```
**Solutions:**
- Update credentials in the script
- Use AWS CLI configuration: `aws configure`
- Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

#### Docker "No Space Left on Device" Error
```
open /var/lib/docker/tmp/GetImageBlob1378721133: no space left on device
```
**Solutions:**
- **Option 1**: Use the Docker cleanup script:
  ```bash
  python aws-handler/services/manage_docker_compose/docker_cleanup.py --sequence 1
  ```
- **Option 2**: Manual cleanup on the EC2 instance:
  ```bash
  docker system prune -a -f --volumes
  ```
- **Option 3**: Check disk space and clean up:
  ```bash
  df -h
  docker system df
  ```

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `No running EC2 instance found` | Instance not running or doesn't exist | Start instance or check sequence number |
| `SSH key not found` | Missing PEM file | Place key in `aws-handler/pems/` |
| `GitHub token file not found` | Missing token file | Create `aws-handler/pacs/learnly-pac.txt` |
| `Permission denied` | SSH key permissions | Run `chmod 400 key.pem` |
| `Authentication failed` | Invalid GitHub token | Generate new token with correct permissions |
| `Host key verification failed` | SSH host key not trusted | Accept host key or add to known_hosts |
| `no space left on device` | Docker disk space full | Use Docker cleanup script or manual cleanup |

## 🔒 Security Considerations

### Development vs Production

**Current Setup (Development):**
- Hardcoded AWS credentials in script
- Local token file storage
- Direct SSH key access

**Production Recommendations:**
- Use AWS IAM roles and environment variables
- Store tokens in AWS Secrets Manager
- Use SSH key management services
- Implement proper logging and monitoring

### Token Security

- Store GitHub tokens securely
- Use minimal required permissions
- Rotate tokens regularly
- Never commit tokens to version control

## 📝 Development Notes

### Script Architecture

The script follows a modular design:
- **Instance Management**: AWS EC2 discovery and connection
- **SSH Operations**: Secure command execution
- **Git Management**: Installation and configuration
- **Repository Operations**: Cloning with authentication
- **Verification**: Structure validation and reporting

### Extensibility

The script can be easily extended for:
- Additional repository types (GitLab, Bitbucket)
- Different directory structures
- Custom post-clone operations
- Integration with CI/CD pipelines

### Future Enhancements

- Support for Git submodules
- Branch selection for cloning
- Custom repository configurations
- Backup and restore functionality
- Multi-instance deployment

## 🤝 Contributing

When modifying the script:
1. Maintain backward compatibility
2. Add proper error handling
3. Update documentation
4. Test with different scenarios
5. Follow the existing code style

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error messages carefully
3. Verify all prerequisites are met
4. Test with a simple sequence first

---

**Last Updated**: December 2024  
**Version**: 1.0.0  
**Compatibility**: Python 3.7+, AWS CLI, Git 2.0+

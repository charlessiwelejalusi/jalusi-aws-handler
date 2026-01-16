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
- 🔍 **Instance Discovery**: Finds EC2 instances by instance name (not sequence number)
- 🌿 **Branch Management**: Checks out provided branch, or falls back to master branch
- 🔄 **Repository Updates**: Pulls latest changes from the deployed branch
- 📦 **Multi-Project Support**: Updates all projects if project name not provided
- 🐳 **Docker Compose Restart**: Automatically restarts services for projects with updates
- 🔍 **Update Detection**: Only restarts Docker Compose when updates are detected
- 🔑 **Credential Handling**: Supports environment variables and credential files (aligned with unified managers)

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
- 🔍 **Instance Discovery**: Finds EC2 instances by instance name
- ⚙️ **Configuration Management**: Replace Nginx configuration files
- 🔧 **Template Processing**: Process configuration templates with variables
- 🔄 **Service Reload**: Reload Nginx service after configuration changes
- ✅ **Validation**: Validate Nginx configuration before applying
- 📝 **IP Address Replacement**: Automatically updates IP addresses in configuration files
- 🐳 **Docker Service Replacement**: Automatically replaces Docker service names (e.g., web-service) with localhost
- 📦 **Auto-Installation**: Automatically installs Nginx if not present
- 🔒 **Configuration Wrapping**: Automatically wraps server blocks in proper nginx.conf structure
- 🐳 **Docker Service Replacement**: Automatically replaces Docker service names (e.g., web-service) with localhost
- 📦 **Auto-Installation**: Automatically installs Nginx if not present
- 🔒 **Configuration Wrapping**: Automatically wraps server blocks in proper nginx.conf structure

### `generate_project_env.py`
**Script for generating environment files for projects**

**Features:**
- 🔧 **Environment Generation**: Generate .env files from templates
- 🔐 **Secret Management**: Handle sensitive configuration data
- 📝 **Template Processing**: Process environment templates with variables
- ✅ **Validation**: Validate generated environment configurations

### `deploy_project_env.py`
**Script for deploying project environment files (.env) to EC2 instances**

**Features:**
- 🔍 **Instance Discovery**: Finds EC2 instances by instance name (not sequence number)
- 📁 **Environment File Management**: Deploys `.env.<project_name>` files from local `envs/` directory
- 🚀 **Secure Deployment**: Uses SCP to securely copy environment files to EC2 instances
- 📂 **Flexible Directory**: Deploys to `/home/ec2-user/projects/<project_name>` by default, or custom directory
- ✅ **Verification**: Verifies file deployment and shows remote file details
- 🔑 **Credential Handling**: Supports environment variables and credential files (aligned with unified managers)

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

# Update specific project on instance
python update_project_directory.py --instance-name jalusi-db-1 --project jalusicorp

# Update specific project with branch
python update_project_directory.py --instance-name jalusi-db-1 --project jalusicorp --branch develop

# Update all projects on instance
python update_project_directory.py --instance-name jalusi-db-1

# List all instances
python update_project_directory.py --list

# Replace Nginx configuration (default: nginx_http.conf)
python replace_nginx_conf_file.py --instance_name jalusi-dev-1

# Replace Nginx configuration with specific config file
python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_https.conf

# Replace Nginx configuration with Let's Encrypt config
python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_http.lets_encrypt.conf

# Generate project environment
python generate_project_env.py --sequence 1 --environment production

# Deploy project environment file (default location)
python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp

# Deploy project environment file to custom directory
python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp --remote-dir /home/ec2-user/projects/envs

# Deploy with custom SSH key
python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp --ssh-key /path/to/key.pem

# Deploy to different AWS region
python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp --region us-east-1
```

## 📁 Directory Structure

### Expected File Layout
```
aws-handler-master/
├── aws_access_key_id/
│   └── aws-handler.txt          # AWS Access Key ID
├── aws_secret_access_key/
│   └── aws-handler.txt          # AWS Secret Access Key
├── pacs/
│   ├── jalusi-pac.txt           # GitHub Personal Access Token (example)
│   └── ...                      # Additional PAC files
├── pems/
│   ├── jalusi-db-1.pem          # SSH key for jalusi-db-1 instance
│   └── ...                      # Additional SSH keys
├── envs/
│   ├── .env.jalusicorp          # Environment file for jalusicorp project
│   └── ...                      # Additional environment files
└── services/
    └── manage_project_version_control/
        ├── README.md                    # This file
        ├── create_project_repository.py  # Create project directories
        ├── update_project_directory.py  # Update existing directories
        ├── replace_nginx_conf_file.py   # Manage Nginx configs
        ├── generate_project_env.py      # Generate environment files
        ├── deploy_project_env.py        # Deploy project environments
        └── nginx.conf/                  # Nginx configuration templates
            ├── nginx_http.conf          # Multi-domain HTTP configuration
            ├── nginx_http.lets_encrypt.conf  # HTTP config for Let's Encrypt setup
            └── nginx_https.conf         # Multi-domain HTTPS configuration with SSL
```

### Created Project Structure
```
/home/ec2-user/projects/ (on EC2 instance)
├── project1/                    # Project 1 directory
│   ├── .env                     # Environment file
│   └── ...                      # Project files
├── project2/                    # Project 2 directory
│   ├── .env                     # Environment file
│   └── ...                      # Project files
└── ...
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
1. **Primary Location**: `pems/<instance_name>.pem` (e.g., `pems/jalusi-db-1.pem`)
2. **Fallback Location**: `./<instance_name>.pem` (current directory)

### AWS Credentials

The scripts support multiple methods for AWS credentials (in order of priority):

1. **Environment Variables** (Recommended for production):
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_SESSION_TOKEN=your_session_token  # Optional
   ```

2. **Credential Files** (Development only):
   - `aws_access_key_id/aws-handler.txt` - Contains AWS Access Key ID
   - `aws_secret_access_key/aws-handler.txt` - Contains AWS Secret Access Key

3. **Command-Line Arguments**:
   ```bash
   --aws-access-key-id AKIA...
   --aws-secret-access-key ...
   --aws-session-token ...  # Optional
   ```

⚠️ **Security Note**: 
- Use environment variables or AWS IAM roles in production
- Never commit credential files to version control
- Rotate credentials regularly

## 📚 Detailed Usage

### Command Line Arguments

#### `create_project_repository.py`

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--instance-name` | `-i` | EC2 instance name | `--instance-name jalusi-db-1` |
| `--project` | `-p` | Project name | `--project jalusicorp` |
| `--github-username` | `-u` | GitHub username | `--github-username Jalusi-Tech` |
| `--region` | `-r` | AWS region (default: af-south-1) | `--region us-east-1` |
| `--pac-name` | | PAC name for token file | `--pac-name jalusi-pac` |
| `--pac-filename` | | Specific PAC filename | `--pac-filename jalusi-pac.txt` |

#### `update_project_directory.py`

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--instance-name` | `-i` | EC2 instance name (required) | `--instance-name jalusi-db-1` |
| `--project` | `-p` | Project name (optional, updates all if not provided) | `--project jalusicorp` |
| `--branch` | `-b` | Branch name to checkout (optional, tries master if not provided) | `--branch develop` |
| `--list` | `-l` | List all available instances | `--list` |
| `--filter` | `-f` | Filter instances by name pattern | `--filter jalusi` |
| `--region` | `-r` | AWS region (default: af-south-1) | `--region us-east-1` |
| `--github-token` | `-t` | GitHub Personal Access Token | `--github-token ghp_xxx` |
| `--pac-name` | | PAC name for token file | `--pac-name jalusi-pac` |
| `--pac-filename` | | Specific PAC filename | `--pac-filename jalusi-pac.txt` |

#### `deploy_project_env.py`

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--instance-name` | `-i` | EC2 instance name (required) | `--instance-name jalusi-db-1` |
| `--project` | `-p` | Project name (required) | `--project jalusicorp` |
| `--remote-dir` | `-d` | Remote directory (default: `/home/ec2-user/projects/<project_name>`) | `--remote-dir /home/ec2-user/projects/envs` |
| `--ssh-key` | `-k` | Path to SSH private key file | `--ssh-key /path/to/key.pem` |
| `--region` | `-r` | AWS region (default: af-south-1) | `--region us-east-1` |
| `--aws-access-key-id` | | AWS Access Key ID (optional) | `--aws-access-key-id AKIA...` |
| `--aws-secret-access-key` | | AWS Secret Access Key (optional) | `--aws-secret-access-key ...` |
| `--aws-session-token` | | AWS Session Token (optional) | `--aws-session-token ...` |

### Workflow Steps

#### `create_project_repository.py` Workflow:
1. **Instance Discovery**: Finds running EC2 instance by instance name
2. **SSH Key Check**: Locates and validates SSH key file
3. **Connection Test**: Tests SSH connectivity to the instance
4. **Git Installation**: Checks and installs Git if needed
5. **Git Configuration**: Sets up Git for HTTPS access
6. **Directory Creation**: Creates project directory structure
7. **Repository Cloning**: Clones repository with authentication
8. **Structure Verification**: Validates the complete setup

#### `update_project_directory.py` Workflow:
1. **Instance Discovery**: Finds running EC2 instance by instance name
2. **SSH Key Check**: Locates and validates SSH key file
3. **Connection Test**: Tests SSH connectivity to the instance
4. **Project Discovery**: Lists all projects or uses specified project
5. **Branch Checkout**: Checks out provided branch or master
6. **Update Detection**: Fetches and checks for new commits
7. **Pull Changes**: Pulls latest changes from remote branch
8. **Service Restart**: Restarts Docker Compose if updates detected

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

### `deploy_project_env.py` Example Output

```
🚀 Project Environment Deployer
============================================================
⚠️  WARNING: This is for development/testing only!
   Never commit real AWS credentials to version control.
============================================================
🔑 Using AWS credentials from credential directories
🎯 Target Instance: jalusi-db-1
📦 Project Name: jalusicorp
🌍 AWS Region: af-south-1
📁 Remote Directory: /home/ec2-user/projects/jalusicorp (default)
✅ Connected to AWS in region: af-south-1
🔍 Looking for instance: jalusi-db-1
✅ Found instance: i-1234567890abcdef0 (State: running)
✅ Found SSH key: /home/charles/Documents/projects/aws-handler-master/pems/jalusi-db-1.pem
✅ Found environment file: /home/charles/Documents/projects/aws-handler-master/envs/.env.jalusicorp
🌐 Target IP: 16.28.64.151
📁 Creating remote directory: /home/ec2-user/projects/jalusicorp
✅ Remote directory created/verified: /home/ec2-user/projects/jalusicorp
🔗 Connecting to EC2 instance: 16.28.64.151
👤 SSH User: ec2-user
📁 Local file: /home/charles/Documents/projects/aws-handler-master/envs/.env.jalusicorp
📁 Remote file: /home/ec2-user/projects/jalusicorp/.env
🔑 SSH Key: /home/charles/Documents/projects/aws-handler-master/pems/jalusi-db-1.pem
🚀 Copying environment file...
--------------------------------------------------------------------------------
✅ Environment file copied successfully!
📤 Output:

✅ File verification successful!
📋 Remote file details:
-rw-r--r-- 1 ec2-user ec2-user 1234 Dec 15 10:30 /home/ec2-user/projects/jalusicorp/.env

============================================================
🎉 Environment file deployment completed successfully!
📁 Remote location: /home/ec2-user/projects/jalusicorp/.env
============================================================
```

## 📚 Detailed Usage Examples

### `deploy_project_env.py` Usage

#### Basic Deployment

Deploy environment file to default location (`/home/ec2-user/projects/<project_name>`):

```bash
python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp
```

#### Custom Remote Directory

Deploy environment file to a custom directory:

```bash
python deploy_project_env.py \
  --instance-name jalusi-db-1 \
  --project jalusicorp \
  --remote-dir /home/ec2-user/projects/envs
```

#### With Custom SSH Key

Specify a custom SSH key path:

```bash
python deploy_project_env.py \
  --instance-name jalusi-db-1 \
  --project jalusicorp \
  --ssh-key /path/to/custom-key.pem
```

#### Different AWS Region

Deploy to an instance in a different AWS region:

```bash
python deploy_project_env.py \
  --instance-name jalusi-db-1 \
  --project jalusicorp \
  --region us-east-1
```

#### Using Environment Variables for AWS Credentials

The script automatically uses environment variables if available:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_SESSION_TOKEN=your_session_token  # Optional

python deploy_project_env.py --instance-name jalusi-db-1 --project jalusicorp
```

#### Using Command-Line Credentials

Override credentials via command-line arguments:

```bash
python deploy_project_env.py \
  --instance-name jalusi-db-1 \
  --project jalusicorp \
  --aws-access-key-id AKIA... \
  --aws-secret-access-key ... \
  --aws-session-token ...  # Optional
```

### Environment File Requirements

1. **File Location**: Environment files must be in the `envs/` directory at the project root
2. **File Naming**: Files must be named `.env.<project_name>`
3. **Example**: For project `jalusicorp`, the file should be `envs/.env.jalusicorp`

```
aws-handler-master/
├── envs/
│   ├── .env.jalusicorp      # Environment file for jalusicorp project
│   ├── .env.test-project    # Environment file for test-project
│   └── ...
└── services/
    └── manage_project_version_control/
        └── deploy_project_env.py
```

### How It Works

#### `deploy_project_env.py`:
1. **Instance Discovery**: Finds the EC2 instance by instance name (e.g., `jalusi-db-1`)
2. **SSH Key Detection**: Automatically locates SSH key from `pems/<instance_name>.pem`
3. **Environment File Check**: Verifies `.env.<project_name>` exists in `envs/` directory
4. **Remote Directory Setup**: Creates remote directory if it doesn't exist
5. **File Deployment**: Uses SCP to securely copy the environment file
6. **Verification**: Verifies the file was copied successfully and shows details

#### `update_project_directory.py`:
1. **Instance Discovery**: Finds the EC2 instance by instance name
2. **Project Selection**: Uses specified project or lists all projects
3. **Branch Management**: Checks out provided branch, or master if not provided
4. **Update Detection**: Fetches remote changes and detects if updates are available
5. **Pull Changes**: Pulls latest changes from the remote branch
6. **Service Restart**: Automatically restarts Docker Compose services if updates were pulled

## 🔧 Nginx Configuration

### Nginx Configuration Files

The `nginx.conf/` directory contains three configuration templates:

#### `nginx_http.conf`
**Multi-domain HTTP configuration for production use**

- Supports multiple domains routing to different services
- Includes IP address access block
- Default catch-all server block
- Use this for HTTP-only setups

#### `nginx_http.lets_encrypt.conf`
**HTTP configuration for Let's Encrypt SSL setup**

- Includes ACME challenge locations (`/.well-known/acme-challenge/`)
- Allows Let's Encrypt to verify domain ownership
- Use this BEFORE obtaining SSL certificates
- Each domain has its own server block with ACME support

#### `nginx_https.conf`
**Multi-domain HTTPS configuration with SSL**

- HTTP to HTTPS redirects for all domains
- SSL/TLS configuration with modern protocols
- Security headers (HSTS, X-Frame-Options, etc.)
- ACME challenge locations preserved for certificate renewal
- Use this AFTER SSL certificates are obtained

### Let's Encrypt SSL Setup Workflow

1. **Initial Setup**: Deploy `nginx_http.lets_encrypt.conf`
   ```bash
   python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_http.lets_encrypt.conf
   ```

2. **Create Certbot Directory**:
   ```bash
   ssh -i pems/jalusi-db-1.pem ec2-user@<IP> "sudo mkdir -p /var/www/certbot"
   ```

3. **Obtain Certificates**:
   ```bash
   certbot certonly --webroot -w /var/www/certbot -d example1.com -d www.example1.com
   certbot certonly --webroot -w /var/www/certbot -d example2.com -d www.example2.com
   ```

4. **Update Certificate Paths**: Edit `nginx_https.conf` and replace:
   - `DOMAIN1_CERT_PATH` with your domain (e.g., `example1.com`)
   - `DOMAIN2_CERT_PATH` with your domain (e.g., `example2.com`)
   - `DOMAIN3_CERT_PATH` with your domain (e.g., `example3.com`)

5. **Deploy HTTPS Configuration**:
   ```bash
   python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_https.conf
   ```

6. **Certificate Renewal**: Certificates auto-renew, but you can manually renew:
   ```bash
   certbot renew --webroot -w /var/www/certbot
   nginx -s reload
   ```

### Nginx Configuration Features

- **Multi-Domain Support**: Each domain routes to different Docker services
- **IP Address Access**: Dedicated block for direct IP access (HTTP only)
- **SSL/TLS Security**: Modern protocols and strong cipher suites
- **Security Headers**: HSTS, X-Frame-Options, CSP, and more
- **Certificate Renewal**: ACME challenge locations preserved for auto-renewal
- **Service Routing**: Flexible routing based on domain names

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
- Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Use AWS CLI configuration: `aws configure`
- Ensure credential files exist: `aws_access_key_id/aws-handler.txt` and `aws_secret_access_key/aws-handler.txt`
- Pass credentials via command-line arguments: `--aws-access-key-id` and `--aws-secret-access-key`

#### Environment File Not Found
```
❌ Environment file not found: /path/to/envs/.env.<project_name>
```
**Solutions:**
- Ensure the environment file exists in the `envs/` directory
- Verify the file is named correctly: `.env.<project_name>`
- Check that the project name matches the filename
- Generate the environment file first using `generate_project_env.py`

#### Instance Not Found
```
❌ No running EC2 instance found with name: <instance_name>
```
**Solutions:**
- Verify the instance name is correct (use `--instance-name` not `--sequence`)
- Ensure the instance is running (not stopped or terminated)
- Check the AWS region matches where the instance exists
- List instances to verify the name: `python unified_resource_manager.py --action list-instances`

#### Branch Checkout Failed
```
❌ Failed to checkout branch '<branch_name>': Branch not found
```
**Solutions:**
- Verify the branch name is correct
- Check if the branch exists on the remote repository
- The script will try master branch if provided branch doesn't exist
- Ensure you have proper Git permissions

#### Docker Compose Restart Failed
```
❌ Failed to restart Docker Compose services
```
**Solutions:**
- Verify Docker Compose is installed on the instance
- Check if docker-compose.yml exists in the project directory
- Ensure Docker services are running
- Check Docker logs for errors: `docker-compose logs`

#### Nginx Configuration Error
```
❌ nginx: configuration file test failed
```
**Solutions:**
- Validate nginx configuration: `nginx -t`
- Check for syntax errors in the configuration file
- Verify certificate paths are correct (for HTTPS config)
- Ensure all required directories exist

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
| `No running EC2 instance found` | Instance not running or doesn't exist | Start instance or check instance name |
| `SSH key not found` | Missing PEM file | Place key in `pems/<instance_name>.pem` |
| `GitHub token file not found` | Missing token file | Create `pacs/<pac-name>-pac.txt` |
| `Environment file not found` | Missing `.env.<project_name>` file | Create file in `envs/` directory or use `generate_project_env.py` |
| `Permission denied` | SSH key permissions | Run `chmod 400 key.pem` |
| `Authentication failed` | Invalid GitHub token | Generate new token with correct permissions |
| `Host key verification failed` | SSH host key not trusted | Accept host key or add to known_hosts |
| `No public IP address found` | Instance has no public IP | Use Elastic IP or check instance networking |
| `SCP command failed` | Network or permission issue | Check SSH connectivity and permissions |
| `Branch not found` | Invalid branch name | Verify branch exists on remote repository |
| `Docker Compose restart failed` | Docker service issue | Check Docker logs and service status |
| `Nginx configuration test failed` | Configuration syntax error | Run `nginx -t` to identify issues |
| `no space left on device` | Docker disk space full | Use Docker cleanup script or manual cleanup |
| `AWS credentials not found` | Missing credentials | Set environment variables or credential files |

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

## 📚 Additional Resources

### Nginx Configuration Examples

#### Basic HTTP Setup
```bash
# Deploy HTTP configuration
python replace_nginx_conf_file.py --instance-name jalusi-db-1 --config-type http
```

#### Let's Encrypt Setup
```bash
# Deploy Let's Encrypt configuration
python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_http.lets_encrypt.conf

# Obtain certificates
certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com

# Deploy HTTPS configuration
python replace_nginx_conf_file.py --instance_name jalusi-dev-1 --config_file nginx_https.conf
```

### Update Project Workflow

```bash
# List all available instances
python update_project_directory.py --list

# List instances with filter
python update_project_directory.py --list --filter jalusi

# Update all projects on instance
python update_project_directory.py --instance-name jalusi-dev-1

# Update specific project
python update_project_directory.py --instance-name jalusi-dev-1 --project agritech

# Update specific project with branch
python update_project_directory.py \
  --instance-name jalusi-dev-1 \
  --project agritech \
  --branch develop

# Update with GitHub token from PAC file
python update_project_directory.py \
  --instance-name jalusi-dev-1 \
  --project agritech \
  --pac-name jalusi-pac
```

## 🐛 VS Code Launch Configurations

All scripts have pre-configured launch configurations in `.vscode/launch.json` for easy debugging in VS Code:

### Available Launch Configurations

#### Docker Manager (`unified_docker_manager.py`)
- **Build Environment**: Install Docker and Docker Compose
- **Restart Docker**: Restart Docker daemon
- **Up/Down/Restart**: Start, stop, or restart services
- **Logs**: View logs (streaming or recent)
- **Status**: Check service status
- **Cleanup**: Clean up Docker resources
- **Info/Disk Usage**: System information

#### Project Repository (`create_project_repository.py`)
- **List Instances**: List all available instances
- **Create Repository**: Create project directory structure
- **With PAC Authentication**: Using GitHub token files

#### Update Project Directory (`update_project_directory.py`)
- **List Instances**: List all available instances
- **Update All Projects**: Update all projects on instance
- **Update Specific Project**: Update single project
- **Update with Branch**: Specify branch to checkout
- **With PAC Authentication**: Using GitHub token files

#### Deploy Project Env (`deploy_project_env.py`)
- **Basic Deployment**: Deploy to default location
- **Custom Remote Directory**: Deploy to custom path
- **With Custom SSH Key**: Specify SSH key path
- **Different Region**: Deploy to different AWS region

#### Replace Nginx Config (`replace_nginx_conf_file.py`)
- **Basic**: Default HTTP configuration
- **HTTP/HTTPS**: Specific configuration types
- **Let's Encrypt**: SSL setup configuration
- **Different Instance**: Multiple instance examples

### Using Launch Configurations

1. Open VS Code
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select configuration from dropdown
4. Press F5 to start debugging

All configurations use:
- `debugpy` debugger
- `integratedTerminal` console
- Appropriate default arguments
- `justMyCode: false` for full debugging

---

**Last Updated**: December 2024  
**Version**: 2.0.0  
**Compatibility**: Python 3.7+, AWS CLI, Git 2.0+, Docker Compose, Nginx

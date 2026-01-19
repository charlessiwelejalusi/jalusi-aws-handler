# EC2 Instance Manager

A Python project using boto3 to manage AWS EC2 instances and projects deployed to those instances. This tool provides a simple command-line interface to start, stop, restart, and monitor EC2 instances and services.

## Features

- ✅ Start EC2 instances
- ✅ Stop EC2 instances  
- ✅ Restart EC2 instances
- ✅ Check instance status
- ✅ List all instances with details
- ✅ Support for multiple AWS regions
- ✅ Comprehensive error handling
- ✅ Wait for operations to complete
- ✅ Beautiful console output with emojis

## Prerequisites

1. **Python 3.6+** installed on your system
2. **AWS Account** with EC2 instances
3. **AWS Credentials** configured (see setup section below)
4. **IAM Permissions** for EC2 operations

### Required IAM Permissions

Your AWS user/role needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:DescribeInstanceStatus"
            ],
            "Resource": "*"
        }
    ]
}
```

## Installation

1. **Clone or download** the script files to your local machine

2. **Create a Python virtual environment** (recommended):
   ```bash
   # For Python 3.3+ (recommended)
   python -m venv venv

   # For older Python versions
   virtualenv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure AWS credentials** (choose one method):

   **Method 1: AWS CLI (Recommended)**
   ```bash
   aws configure
   ```
   Enter your AWS Access Key ID, Secret Access Key, default region, and output format.

   **Method 2: Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

       **Method 3: IAM Role** (if running on EC2)
    - Attach an IAM role to your EC2 instance with the required permissions

    **Method 4: Command Line Arguments** (for testing)
    ```bash
    python ec2_manager_with_credentials.py --action list --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY
    ```

    **Method 5: Hardcoded in Code** (⚠️ Development only)
    - Use the `example_with_credentials.py` file as a template
    - Replace placeholder credentials with your actual AWS credentials
    - ⚠️ **NEVER commit real credentials to version control!**

## Usage

### Basic Commands

**List all EC2 instances:**
```bash
python ec2_manager.py --action list
```

**Check instance status:**
```bash
python ec2_manager.py --action status --instance-id i-1234567890abcdef0
```

**Start an instance:**
```bash
python ec2_manager.py --action start --instance-id i-1234567890abcdef0
```

**Stop an instance:**
```bash
python ec2_manager.py --action stop --instance-id i-1234567890abcdef0
```

**Restart an instance:**
```bash
python ec2_manager.py --action restart --instance-id i-1234567890abcdef0
```

### Commands with Credentials

**List instances with credentials:**
```bash
python ec2_manager_with_credentials.py --action list --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY
```

**Start instance with credentials:**
```bash
python ec2_manager_with_credentials.py --action start --instance-id i-1234567890abcdef0 --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY
```

**Use with session token (for temporary credentials):**
```bash
python ec2_manager_with_credentials.py --action list --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY --session-token YOUR_SESSION_TOKEN
```

### Advanced Usage

**Specify a different AWS region:**
```bash
python ec2_manager.py --action list --region us-west-2
```

**Get help:**
```bash
python ec2_manager.py --help
```

## Output Examples

### Listing Instances
```
✅ Connected to AWS EC2 in region: us-east-1

📋 EC2 Instances:
--------------------------------------------------------------------------------
Instance ID          State           Type         Name                 Public IP     
--------------------------------------------------------------------------------
i-1234567890abcdef0  running         t2.micro     My Web Server       52.23.45.67   
i-0987654321fedcba0  stopped         t3.small     Database Server     N/A           
i-abcdef1234567890   running         t2.micro     Test Instance       18.234.56.78  

Total instances: 3
```

### Instance Status
```
📊 Instance Status: i-1234567890abcdef0
--------------------------------------------------
State: running
Type: t2.micro
Public IP: 52.23.45.67
Private IP: 172.31.16.100
Launch Time: 2024-01-15 10:30:00+00:00
Name: My Web Server
```

### Starting an Instance
```
🚀 Starting instance: i-1234567890abcdef0

📊 Instance Status: i-1234567890abcdef0
--------------------------------------------------
State: stopped
Type: t2.micro
Public IP: N/A
Private IP: 172.31.16.100
Launch Time: 2024-01-15 10:30:00+00:00
Name: My Web Server

⏳ Starting instance...
✅ Instance started successfully!

📊 Instance Status: i-1234567890abcdef0
--------------------------------------------------
State: running
Type: t2.micro
Public IP: 52.23.45.67
Private IP: 172.31.16.100
Launch Time: 2024-01-15 10:30:00+00:00
Name: My Web Server
```

## Error Handling

The script includes comprehensive error handling for common scenarios:

- **Invalid instance ID**: Instance not found
- **Incorrect instance state**: Instance cannot be started/stopped in current state
- **Missing AWS credentials**: Prompts to configure credentials
- **Network timeouts**: Waiter timeouts for long operations
- **Permission errors**: Insufficient IAM permissions

## Troubleshooting

### Common Issues

**1. "AWS credentials not found"**
```bash
# Configure AWS credentials
aws configure
```

**2. "Instance not found"**
- Verify the instance ID is correct
- Check if the instance exists in the specified region
- Ensure you have permissions to view the instance

**3. "Incorrect instance state"**
- Wait for the instance to finish its current operation
- Check the current state with the status command

**4. "Permission denied"**
- Verify your IAM user/role has the required EC2 permissions
- Check if the instance belongs to your AWS account

**5. "Timeout waiting for instance"**
- Some instances take longer to start/stop
- Check the AWS console for the actual instance state
- Retry the operation

### Debug Mode

For more detailed error information, you can modify the script to include debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- **Never commit AWS credentials** to version control
- **Use IAM roles** when possible instead of access keys
- **Follow the principle of least privilege** for IAM permissions
- **Regularly rotate** your AWS access keys
- **Monitor** your AWS CloudTrail logs for API usage

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this script.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Review AWS documentation for EC2 API errors
3. Verify your AWS credentials and permissions
4. Check the AWS Service Health Dashboard for any service issues

## To stop Git from tracking the pems/ folder, you need to remove it from Git's tracking while keeping the local files. Here's the command:
git rm -r --cached pems/

----------

## Common EC2 Instance Types and RAM

The table below lists some commonly used general-purpose and burstable EC2 instance families with their vCPU and memory specs. Use this as a quick reference when choosing instance sizes for your environments:

| Instance Type | vCPUs | RAM (GiB) |
|--------------|-------|-----------|
| t3.micro     | 2     | 1         |
| t3.small     | 2     | 2         |
| t3.medium    | 2     | 4         |
| t3.large     | 2     | 8         |
| t3.xlarge    | 4     | 16        |
| t3.2xlarge   | 8     | 32        |
| t3a.micro    | 2     | 1         |
| t3a.small    | 2     | 2         |
| t3a.medium   | 2     | 4         |
| t3a.large    | 2     | 8         |
| t3a.xlarge   | 4     | 16        |
| t3a.2xlarge  | 8     | 32        |
| m5.large     | 2     | 8         |
| m5.xlarge    | 4     | 16        |
| m5.2xlarge   | 8     | 32        |
| m5.4xlarge   | 16    | 64        |
| m5.8xlarge   | 32    | 128       |

> **Note**: These values are approximate and based on current AWS documentation as of 2026. Always confirm exact specs and pricing in the AWS Console or official AWS EC2 documentation before selecting an instance type for production.


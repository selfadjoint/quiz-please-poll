# Telegram Bot Poll Creator

This project contains an AWS Lambda function and Terraform configuration to create polls about participating in a quiz game in Telegram. The Lambda function sends messages to a Telegram channel, retrieves updates from a connected group, and creates polls based on those updates.

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)

## Project Structure

```plaintext
├── src
│   ├── main.py                # Lambda function code
│   ├── requirements.txt       # Python dependency definitions
│   └── (other source files or folders)
└── terraform
    ├── main.tf                # Terraform configuration
    ├── variables.tf           # Input variables
    ├── backend.hcl            # Backend configuration (not committed; see below)
    └── (other Terraform files)
├── README.md
```

## Prerequisites

- DynamoDB table with game data. Check the [Quiz Please Game Registration](https://github.com/selfadjoint/quiz-please-reg) project for the required DynamoDB table setup.
- [AWS CLI](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/)
- [Python 3.11+](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)

## Setup

### 1. **Clone the repository**:

   ```bash
   git clone https://github.com//selfadjoint/quiz-please-poll.git
   cd quiz-please-poll
  ````

### 2. Install Python Dependencies
The dependencies are not committed to the repository. To install them into the src folder, run:
```bash
pip install --upgrade --target ./src -r src/requirements.txt
```
This command installs all required Python packages into the src directory so that they are included in the Lambda deployment package.

### 3. Configure the Terraform Backend and Variables
Terraform uses an S3 backend for state storage. Since sensitive information should not be committed to the repository, create a separate backend configuration file.

Create a file named `backend.hcl` inside the `terraform` folder with content similar to:

```hcl
bucket       = "your-tf-state-bucket"                  # Replace with your S3 bucket name
key          = "your-resource-name/terraform.tfstate"  # Adjust as needed
region       = "us-east-1"                             # Your AWS region
profile      = "your_aws_profile"                      # The AWS CLI profile to use
encrypt      = true
use_lockfile = true
```
**Create a `terraform.tfvars` file with the necessary variables. Example**:

   ```hcl
   aws_profile                = "your_aws_profile"
   bot_name                   = "YourBotName"
   bot_token                  = "YOUR_BOT_TOKEN"
   channel_id                 = "YOUR_CHANNEL_ID"
   group_id                   = "YOUR_GROUP_ID"
   dynamodb_reg_table_arn     = "arn:aws:dynamodb:us-east-1:123456789012:table/QuizPleaesReg"
   ```

5. **Apply the Terraform configuration**:

   ```bash
   terraform apply
   ```

   Review the changes and type `yes` to confirm.

## Environment Variables

The Lambda function uses the following environment variables:

- `DYNAMODB_REG_TABLE_NAME`: Name of the DynamoDB registration table.
- `DYNAMODB_UPDATE_TABLE_NAME`: Name of the DynamoDB update table (created by Terraform).
- `BOT_NAME`: Name of the Telegram bot.
- `BOT_TOKEN`: Token for the Telegram bot.
- `CHANNEL_ID`: ID of the Telegram channel.
- `GROUP_ID`: ID of the Telegram group.

These variables are set in the Terraform configuration and passed to the Lambda function during deployment.

## Usage

Once deployed, the Lambda function will run every Wednesday and Friday at 15:00 UTC, the schedule may be adjusted in [main.tf](./terraform/main.tf). It will:

1. Load games from the DynamoDB registration table.
2. Send a message to the Telegram channel for each game.
3. Retrieve recent updates from the connected Telegram group.
4. Create a poll in the group based on the updates.
5. Update the DynamoDB table with the poll creation status.

Logs for the Lambda function can be viewed in AWS CloudWatch.

## Clean Up
To remove all resources created by Terraform, run:
```bash
terraform destroy
```
This will tear down the deployed AWS resources.

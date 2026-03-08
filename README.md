# Telegram Bot Poll Creator

This project contains an AWS Lambda function and Terraform configuration to create polls about participating in a quiz game in Telegram. The Lambda function sends messages to a Telegram channel, retrieves updates from a connected group, and creates polls based on those updates.

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Clean Up](#clean-up)

## Project Structure

```plaintext
├── src
│   ├── main.py                # Lambda function code
│   ├── requirements.txt       # Python dependency definitions
│   └── (other source files or folders)
├── sql
│   └── 001_create_telegram_bot_updates.sql  # Postgres DDL for Telegram update offsets
└── terraform
    ├── main.tf                # Terraform configuration
    ├── variables.tf           # Input variables
    ├── backend.hcl            # Backend configuration (not committed; see below)
    └── (other Terraform files)
├── README.md
```

## Prerequisites

- Postgres with the `quizplease.games`, `quizplease.game_registration_tracking`, and `quizplease.game_registration_overview` objects already created.
- Apply [sql/001_create_telegram_bot_updates.sql](./sql/001_create_telegram_bot_updates.sql) to create the table that stores the Telegram update offset previously kept in `QuizPleasePoll`.
- [AWS CLI](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/)
- [Python 3.11+](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)

## Setup

### 1. **Clone the repository**:

```bash
 git clone https://github.com//selfadjoint/quiz-please-poll.git
 cd quiz-please-poll
```

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
aws_credentials_file       = ["~/.aws/credentials"]
aws_profile                = "your_aws_profile"
bot_name                   = "YourBotName"
bot_token                  = "YOUR_BOT_TOKEN"
channel_id                 = "YOUR_CHANNEL_ID"
group_id                   = "YOUR_GROUP_ID"
postgres_host              = "your-postgres-host"
postgres_port              = 5432
postgres_database          = "your_database"
postgres_user              = "your_user"
postgres_password          = "your_password"
```

### 4. Initialize Terraform
Change to the terraform directory and initialize Terraform using the backend configuration:
```bash
cd terraform
terraform init -backend-config=backend.hcl
```
This command sets up the backend and downloads required providers.

### 5. Review and Apply the Terraform Configuration
First, run a plan to see the changes that Terraform will apply:
```bash
terraform plan
```

If everything looks correct, deploy the resources with:
```bash
terraform apply
```
Confirm the apply action when prompted.

## Environment Variables

The Lambda function uses the following environment variables:

- `DB_HOST`: Postgres host name.
- `DB_PORT`: Postgres port.
- `DB_NAME`: Postgres database name.
- `DB_USER`: Postgres user name.
- `DB_PASSWORD`: Postgres password.
- `BOT_NAME`: Name of the Telegram bot.
- `BOT_TOKEN`: Token for the Telegram bot.
- `CHANNEL_ID`: ID of the Telegram channel.
- `GROUP_ID`: ID of the Telegram group.

These variables are set in the Terraform configuration and passed to the Lambda function during deployment.

## Usage

Once deployed, the Lambda function will run every Wednesday and Friday at 15:00 UTC, the schedule may be adjusted in [main.tf](./terraform/main.tf). It will:

1. Load games from `quizplease.game_registration_overview`.
2. Send a message to the Telegram channel for each game.
3. Retrieve recent updates from the connected Telegram group using the offset stored in `quizplease.telegram_bot_updates`.
4. Create a poll in the group based on the updates.
5. Update `quizplease.game_registration_tracking` with the poll creation status.

Logs for the Lambda function can be viewed in AWS CloudWatch.

If the target Postgres instance is only reachable inside a private network, the Lambda must also be attached to the correct VPC, subnets, and security groups. That networking is not managed by the current Terraform in this repository.

## Clean Up
To remove all resources created by Terraform, run:
```bash
terraform destroy
```
This will tear down the deployed AWS resources.

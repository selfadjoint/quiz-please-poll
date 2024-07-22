# Telegram Bot Poll Creator

This project contains an AWS Lambda function and Terraform configuration to create polls about participating in a quiz game in Telegram. The Lambda function sends messages to a Telegram channel, retrieves updates from a connected group, and creates polls based on those updates.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)

## Prerequisites

Before you begin, ensure you have the following installed:

- [AWS CLI](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/)
- [Python 3.11+](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)

## Project Structure

```plaintext
quiz-please-poll/
├── src/
│   ├── main.py
│   ├── requirements.txt
│   ├── dependencies
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars
│   └── lambda.zip
├── README.md
```

## Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-repo/telegram-bot-poll-creator.git
   cd telegram-bot-poll-creator
   
2. **Navigate to the Terraform directory**:

   ```bash
   cd ../terraform
   ```

3. **Initialize Terraform**:

   ```bash
   terraform init
   ```

4. **Create a `terraform.tfvars` file with the necessary variables. Example**:

   ```hcl
   aws_region                 = "us-east-1"
   lambda_function_name       = "TelegramBotFunction"
   bot_name                   = "YourBotName"
   bot_token                  = "YOUR_BOT_TOKEN"
   channel_id                 = "YOUR_CHANNEL_ID"
   group_id                   = "YOUR_GROUP_ID"
   dynamodb_reg_table_name    = "TelegramBotReg"
   dynamodb_update_table_name = "TelegramBotUpdates"
   dynamodb_reg_table_arn     = "arn:aws:dynamodb:us-east-1:123456789012:table/TelegramBotReg"
   use_existing_role          = true
   existing_role_name         = "lambda_execution_role"
   ```

5. **Apply the Terraform configuration**:

   ```bash
   terraform apply
   ```

   Review the changes and type `yes` to confirm.

## Environment Variables

The Lambda function uses the following environment variables:

- `DYNAMODB_REG_TABLE_NAME`: Name of the DynamoDB registration table.
- `DYNAMODB_UPDATE_TABLE_NAME`: Name of the DynamoDB update table.
- `BOT_NAME`: Name of the Telegram bot.
- `BOT_TOKEN`: Token for the Telegram bot.
- `CHANNEL_ID`: ID of the Telegram channel.
- `GROUP_ID`: ID of the Telegram group.

These variables are set in the Terraform configuration and passed to the Lambda function during deployment.

## Usage

Once deployed, the Lambda function will run every day at 15:00 UTC. It will:

1. Load games from the DynamoDB registration table.
2. Send a message to the Telegram channel for each game.
3. Retrieve recent updates from the connected Telegram group.
4. Create a poll in the group based on the updates.
5. Update the DynamoDB table with the poll creation status.

Logs for the Lambda function can be viewed in AWS CloudWatch.

## Important Note

This project uses a DynamoDB table with game registration data that should be created separately. Ensure that the `TelegramBotReg` table exists and is correctly populated with game registration data before running the Lambda function.

## License

This project is licensed under the MIT License.

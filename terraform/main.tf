terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.26"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region                   = var.aws_region
  shared_credentials_files = var.aws_credentials_file
  profile                  = var.aws_profile
}

resource "aws_iam_role" "lambda_execution_role" {
  name = var.resource_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Sid    = "",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dynamodb_policy" {
  name = var.resource_name
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ],
        Resource = [
          aws_dynamodb_table.telegram_bot_updates.arn, # Allow access to the updates table
          var.dynamodb_reg_table_arn,                  # Allow access to the registration data table created separately
          "${var.dynamodb_reg_table_arn}/index/*"      # Allow access to the GSIs in the registration data table
        ]
      }
    ]
  })
}

resource "aws_dynamodb_table" "telegram_bot_updates" {
  name         = var.resource_name
  hash_key     = "bot_name"
  billing_mode = "PAY_PER_REQUEST"

  attribute {
    name = "bot_name"
    type = "S"
  }

  tags = var.tags
}

resource "aws_lambda_function" "telegram_bot" {
  description      = "Create polls about participating in a quiz game in Telegram"
  filename         = "${path.module}/lambda.zip"
  function_name    = var.resource_name
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  timeout          = 300

  environment {
    variables = {
      DYNAMODB_REG_TABLE_NAME    = var.dynamodb_reg_table_name
      DYNAMODB_UPDATE_TABLE_NAME = aws_dynamodb_table.telegram_bot_updates.name
      BOT_NAME                   = var.bot_name
      BOT_TOKEN                  = var.bot_token
      CHANNEL_ID                 = var.channel_id
      GROUP_ID                   = var.group_id
    }
  }

  tags = var.tags
}

resource "aws_lambda_permission" "allow_execution" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telegram_bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule_rule.arn
}

resource "aws_cloudwatch_event_rule" "schedule_rule" {
  name                = var.resource_name
  description         = "Scheduled rule to trigger telegram bot Lambda on Wednesdays and Fridays"
  schedule_expression = "cron(0 15 ? * WED,FRI *)" # Runs every Wednesday and Friday at 15:00 UTC
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule_rule.name
  target_id = var.resource_name
  arn       = aws_lambda_function.telegram_bot.arn
}

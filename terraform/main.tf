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

# Data source to reference existing IAM role
data "aws_iam_role" "existing_lambda_execution_role" {
  count = var.use_existing_role ? 1 : 0
  name  = var.existing_role_name
}

resource "aws_iam_role" "lambda_execution_role" {
  count = var.use_existing_role ? 0 : 1

  name = var.new_role_name

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
  role       = var.use_existing_role ? data.aws_iam_role.existing_lambda_execution_role[0].name : aws_iam_role.lambda_execution_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dynamodb_policy" {
  name = "dynamodb_policy"
  role = var.use_existing_role ? data.aws_iam_role.existing_lambda_execution_role[0].id : aws_iam_role.lambda_execution_role[0].id

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
          aws_dynamodb_table.telegram_bot_updates.arn,
          var.dynamodb_reg_table_arn
        ]
      }
    ]
  })
}

resource "aws_dynamodb_table" "telegram_bot_updates" {
  name         = var.dynamodb_update_table_name
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
  function_name    = var.lambda_function_name
  role             = var.use_existing_role ? data.aws_iam_role.existing_lambda_execution_role[0].arn : aws_iam_role.lambda_execution_role[0].arn
  handler          = "main.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  timeout          = 300

  environment {
    variables = {
      DYNAMODB_REG_TABLE_NAME    = var.dynamodb_reg_table_name
      DYNAMODB_UPDATE_TABLE_NAME = var.dynamodb_update_table_name
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
  name                = "telegram_bot_schedule_rule"
  description         = "Scheduled rule to trigger telegram bot Lambda"
  schedule_expression = "cron(0 15 ? * WED,FRI *)" # Runs every Wednesday and Friday at 15:00 UTC
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule_rule.name
  target_id = "lambda_target"
  arn       = aws_lambda_function.telegram_bot.arn
}

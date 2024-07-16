variable "tags" {
  type = map(string)
  default = {
    Name    = "QuizPleasePoll"
    Project = "QuizPlease"
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_credentials_file" {
  type    = list(string)
  default = ["$HOME/.aws/credentials"]
}

variable "aws_profile" {
  type    = string
  default = "default"
}

variable "dynamodb_reg_table_arn" {
  type = string
}

variable "dynamodb_reg_table_name" {
  type    = string
  default = "QuizPleaseReg"
}

variable "dynamodb_update_table_name" {
  type    = string
  default = "QuizPleasePollUpdates"
}

variable "lambda_function_name" {
  type    = string
  default = "QuizPleasePoll"
}

variable "bot_token" {
  type = string
}

variable "bot_name" {
  type = string
}

variable "channel_id" {
  type = string
}

variable "group_id" {
  type = string
}

variable "use_existing_role" {
  description = "Boolean to determine whether to use an existing IAM role"
  type        = bool
  default     = false
}

variable "existing_role_name" {
  description = "The name of the existing IAM role to use"
  type        = string
  default     = "lambda_execution_role"
}

variable "new_role_name" {
  description = "The name of the new IAM role to create if not using an existing one"
  type        = string
  default     = "lambda_execution_role"
}
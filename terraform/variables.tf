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

variable "resource_name" {
  description = "The prefix for all resource names"
  type        = string
  default     = "QuizPleasePoll"
}

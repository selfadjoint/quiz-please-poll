output "lambda_function_name" {
  value = aws_lambda_function.telegram_bot.function_name
}

output "dynamodb_updates_table_name" {
  value = aws_dynamodb_table.telegram_bot_updates.name
}

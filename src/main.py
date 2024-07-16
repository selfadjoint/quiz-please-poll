import json
import logging
import os

import boto3
import pendulum as pdl
import requests as req

# Set up logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up constants
DYNAMODB_REG_TABLE_NAME = os.environ['DYNAMODB_REG_TABLE_NAME']
DYNAMODB_UPDATE_TABLE_NAME = os.environ['DYNAMODB_UPDATE_TABLE_NAME']
BOT_NAME = os.environ['BOT_NAME']
BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
GROUP_ID = os.environ['GROUP_ID']

# Initialize a DynamoDB client
dynamodb = boto3.client('dynamodb')


def get_games(_table):
    """
    Loads the games we have already registered at from a DynamoDB table to create a poll.
    """
    try:
        response = dynamodb.query(
            TableName=_table,
            IndexName='poll_created_index',
            KeyConditionExpression='is_poll_created = :val',
            ProjectionExpression='game_id, game_date, game_type',
            ExpressionAttributeValues={':val': {'N': '0'}},
        )
        games = [[x['game_id']['N'], x['game_date']['S'], x['game_type']['S']] for x in response['Items'] if
                 pdl.parse(x['game_date']['S']) <= pdl.today().add(days=5)]
        logger.info(f'Loaded {len(games)} game(s) from the reg table')
        return games

    except Exception as e:
        logger.error(f'Failed to load games: {e}')
        return None


def send_message(_bot_token, _channel_id, _message):
    """
    Sends a message to a channel.
    """
    url = f'https://api.telegram.org/bot{_bot_token}/sendMessage'
    body = {'chat_id': _channel_id, 'text': _message}
    response = req.post(url, json=body)

    if response.status_code == 200:
        message_data = response.json()
        logger.info(f'Message sent successfully! Message: {message_data["result"]["text"]}')
        return message_data['result']
    else:
        logger.error(f'Failed to send message. Status code: {response.status_code}')
        logger.info(f'Response: {response.json()}')
        return None


def get_last_update_id(_table, _bot_name):
    """
    Gets the last update ID from a DynamoDB table.
    """
    try:
        response = dynamodb.get_item(TableName=_table, Key={'bot_name': {'S': _bot_name}})
        if 'Item' in response and 'update_id' in response['Item']:
            logger.info(f'Last update ID: {response["Item"]["update_id"]["N"]}')
            return int(response['Item']['update_id']['N'])
        else:
            logger.info('No existing update ID found, starting from the beginning.')
            return 0  # Return 0 to indicate no updates have been processed yet
    except Exception as e:
        logger.error(f'Failed to get last update ID: {e}')
        return 0  # Return 0 in case of any exception


def update_last_update_id(_table, _bot_name, _update_id):
    """
    Updates the last update ID in a DynamoDB table.
    """
    try:
        dynamodb.put_item(TableName=_table, Item={'bot_name': {'S': _bot_name}, 'update_id': {'N': str(_update_id)}})
        logger.info(f'Last update ID updated to {str(_update_id)}')
    except Exception as e:
        logger.error(f'Failed to update last update ID: {e}')


def get_group_updates(_bot_token, _table, _bot_name, _timeout=5, _time_window=15):
    """
    Gets recent updates from a group connected to the channel.
    """
    url = f'https://api.telegram.org/bot{_bot_token}/getUpdates'
    cutoff_time = pdl.now().subtract(seconds=_time_window).int_timestamp
    last_update_id = get_last_update_id(_table, _bot_name)
    recent_updates = []

    while True:
        body = {'allowed_updates': json.dumps(['message']), 'timeout': _timeout, 'offset': last_update_id}
        response = req.get(url, params=body)
        if response.status_code == 200:
            logger.info(f'Updates for {last_update_id} received successfully!')
        else:
            logger.error(f'Failed to get updates for {last_update_id}. Status code: {response.status_code}')
            logger.info(f'Response: {response.json()}')
            break

        result = response.json().get('result', [])
        if not result:
            break

        for update in result:
            message_date = update['message']['date']
            if message_date >= cutoff_time:
                recent_updates.append(update)
            last_update_id = update['update_id'] + 1

        update_last_update_id(_table, _bot_name, last_update_id)

    return recent_updates


def get_message_ids(_updates):
    """
    Parses the updates and returns the ID of the last bot message.
    """
    if not _updates:
        logger.info('No updates to parse.')
        return None

    filtered_updates = sorted(
        item['message']['message_id'] for item in _updates if item.get('message', {}).get('is_automatic_forward')
    )

    if filtered_updates:
        last_bot_message_id = filtered_updates[-1]
        logger.info(f'Last bot message ID: {last_bot_message_id}')
        return last_bot_message_id
    return None


def send_poll(_bot_token, _group_id, _question, _options, _reply_to_message_id):
    """
    Sends a poll to a group.
    """
    url = f'https://api.telegram.org/bot{_bot_token}/sendPoll'
    body = {
        'chat_id': _group_id,
        'question': _question,
        'options': json.dumps(_options),
        'is_anonymous': False,
        'allows_multiple_answers': True,
        'reply_to_message_id': _reply_to_message_id,
    }
    headers = {'Content-Type': 'application/json'}
    response = req.post(url, json=body, headers=headers)

    if response.status_code == 200:
        logger.info('Poll sent successfully!')
        return response.json()['ok']
    else:
        logger.error(f'Failed to send poll. Status code: {response.status_code}')
        logger.info(f'Response: {response.json()}')
        return response.json()['ok']


def update_item(_table, _game_id):
    """
    Updates an item in a DynamoDB table.
    """
    try:
        response = dynamodb.update_item(
            TableName=_table,
            Key={'game_id': {'N': _game_id}},
            UpdateExpression='SET is_poll_created = :P, poll_date = :D',
            ExpressionAttributeValues={':P': {'N': '1'}, ':D': {'S': pdl.today().format('YYYY-MM-DD')}},
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f'Game {_game_id} updated successfully')
        return response['ResponseMetadata']
    except Exception as e:
        logger.error(f'Failed to update item {_game_id} in table {_table}: {e}')
        return None


# Main function
def lambda_handler(event=None, context=None):
    games = get_games(DYNAMODB_REG_TABLE_NAME)
    if not games:
        logger.error('No games loaded.')
        return {'statusCode': 500, 'body': json.dumps('No games to process')}

    for game in games:
        game_id, game_date, game_type = game
        game_day = pdl.parse(game_date).format('dd, DD MMMM', locale='ru').capitalize()

        message = f'{game_day}, {game_type}'
        message_res = send_message(BOT_TOKEN, CHANNEL_ID, message)

        if not message_res:
            logger.error(f'Failed to send message for game {game_id}.')
            continue

        recent_updates = get_group_updates(BOT_TOKEN, DYNAMODB_UPDATE_TABLE_NAME, BOT_NAME)
        reply_id = get_message_ids(recent_updates)

        if not reply_id:
            logger.error(f'Failed to get reply ID for game {game_id}.')
            continue

        poll_question = 'Голосуем'
        poll_options = ['Иду', '+1', 'Не иду']
        poll_response = send_poll(BOT_TOKEN, GROUP_ID, poll_question, poll_options, reply_id)

        if poll_response:
            update_item(DYNAMODB_REG_TABLE_NAME, game_id)
            logger.info(f'Game {game_id} has been processed')
        else:
            logger.error(f'Failed to send poll for game {game_id}.')

    return {'statusCode': 200, 'body': json.dumps('All games processed successfully')}

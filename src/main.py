import json
import logging
import os
import time

import pendulum as pdl
import requests as req

# Set up logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

QUIZPLEASE_SCHEMA = 'quizplease'

# Set up constants
BOT_NAME = os.environ['BOT_NAME']
BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
GROUP_ID = os.environ['GROUP_ID']


def get_db_connection():
    try:
        import psycopg2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            'psycopg2 is not installed. Install src/requirements.txt before running the Lambda locally.'
        ) from exc

    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )


class PostgresStore:
    def __init__(self):
        self.connection = get_db_connection()

    def close(self):
        self.connection.close()

    def get_games(self):
        """
        Loads the games we have already registered at from Postgres to create a poll.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                SELECT game_id, game_date, COALESCE(game_time, ''), COALESCE(game_venue, ''), COALESCE(game_type, '')
                FROM {QUIZPLEASE_SCHEMA}.game_registration_overview
                WHERE reg_date IS NOT NULL
                  AND is_poll_created = FALSE
                  AND game_date <= CURRENT_DATE + 5
                ORDER BY game_date, COALESCE(game_time, ''), game_id
                '''
            )
            games = [
                [str(game_id), game_date.isoformat(), game_time, game_venue, game_type]
                for game_id, game_date, game_time, game_venue, game_type in cursor.fetchall()
            ]
            logger.info(f'Loaded {len(games)} game(s) from Postgres')
            return games
        except Exception as e:
            logger.error(f'Failed to load games: {e}')
            return None
        finally:
            cursor.close()

    def get_last_update_id(self, bot_name):
        """
        Gets the last update ID from Postgres.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                SELECT update_id
                FROM {QUIZPLEASE_SCHEMA}.telegram_bot_updates
                WHERE bot_name = %s
                ''',
                (bot_name,),
            )
            row = cursor.fetchone()
            if row:
                logger.info(f'Last update ID: {row[0]}')
                return int(row[0])

            logger.info('No existing update ID found, starting from the beginning.')
            return 0
        except Exception as e:
            logger.error(f'Failed to get last update ID: {e}')
            return 0
        finally:
            cursor.close()

    def update_last_update_id(self, bot_name, update_id):
        """
        Updates the last update ID in Postgres.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {QUIZPLEASE_SCHEMA}.telegram_bot_updates (bot_name, update_id)
                VALUES (%s, %s)
                ON CONFLICT (bot_name)
                DO UPDATE
                SET update_id = EXCLUDED.update_id,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (bot_name, update_id),
            )
            self.connection.commit()
            logger.info(f'Last update ID updated to {update_id}')
        except Exception as e:
            self.connection.rollback()
            logger.error(f'Failed to update last update ID: {e}')
        finally:
            cursor.close()

    def get_active_poll_ids(self):
        """Return set of all known poll_ids."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(f'SELECT poll_id FROM {QUIZPLEASE_SCHEMA}.polls')
            return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f'Failed to get active poll IDs: {e}')
            return set()
        finally:
            cursor.close()

    def store_poll_answer(self, poll_id, user_id, username, first_name, last_name, option_ids, update_id=None):
        """Insert a poll_answer event into poll_answers."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {QUIZPLEASE_SCHEMA}.poll_answers
                    (poll_id, user_id, username, first_name, last_name, option_ids, update_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (poll_id, user_id, username, first_name, last_name, option_ids, update_id),
            )
            self.connection.commit()
            logger.info(f'Stored poll_answer: poll={poll_id} user={user_id} options={option_ids}')
        except Exception as e:
            self.connection.rollback()
            logger.error(f'Failed to store poll_answer for poll {poll_id}: {e}')
        finally:
            cursor.close()

    def store_poll(self, poll_id, game_id, message_id):
        """
        Stores poll metadata returned by Telegram for later answer tracking.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {QUIZPLEASE_SCHEMA}.polls (poll_id, game_id, message_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (poll_id) DO NOTHING
                ''',
                (poll_id, int(game_id), message_id),
            )
            self.connection.commit()
            logger.info(f'Poll {poll_id} stored for game {game_id}')
        except Exception as e:
            self.connection.rollback()
            logger.error(f'Failed to store poll {poll_id}: {e}')
        finally:
            cursor.close()

    def mark_poll_created(self, game_id):
        """
        Marks a game as having a created poll in Postgres.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                UPDATE {QUIZPLEASE_SCHEMA}.game_registration_tracking
                SET poll_created = TRUE,
                    poll_date = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE game_id = %s
                RETURNING game_id
                ''',
                (int(game_id),),
            )
            row = cursor.fetchone()
            self.connection.commit()
            if row:
                logger.info(f'Game {game_id} updated successfully')
                return True

            logger.error(f'Game {game_id} was not updated')
            return False
        except Exception as e:
            self.connection.rollback()
            logger.error(f'Failed to update game {game_id}: {e}')
            return False
        finally:
            cursor.close()


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


def get_group_updates(_bot_token, _store, _bot_name, _timeout=5, _time_window=15):
    """
    Gets recent updates from a group connected to the channel.
    Handles message updates (for reply_id lookup) and poll_answer updates (persisted to DB).
    """
    url = f'https://api.telegram.org/bot{_bot_token}/getUpdates'
    cutoff_time = pdl.now().subtract(seconds=_time_window).int_timestamp
    last_update_id = _store.get_last_update_id(_bot_name)
    active_poll_ids = _store.get_active_poll_ids()
    recent_updates = []

    while True:
        body = {'allowed_updates': json.dumps(['message', 'poll_answer']), 'timeout': _timeout, 'offset': last_update_id}
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
            if 'poll_answer' in update:
                pa = update['poll_answer']
                if pa['poll_id'] in active_poll_ids:
                    user = pa.get('user') or {}
                    _store.store_poll_answer(
                        poll_id=pa['poll_id'],
                        user_id=user.get('id'),
                        username=user.get('username'),
                        first_name=user.get('first_name', ''),
                        last_name=user.get('last_name'),
                        option_ids=pa.get('option_ids', []),
                        update_id=update['update_id'],
                    )
            elif 'message' in update:
                if update['message']['date'] >= cutoff_time:
                    recent_updates.append(update)

            last_update_id = update['update_id'] + 1

        _store.update_last_update_id(_bot_name, last_update_id)

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
        return response.json()['result']
    else:
        logger.error(f'Failed to send poll. Status code: {response.status_code}')
        logger.info(f'Response: {response.json()}')
        return None


def lambda_handler(event=None, context=None):
    try:
        store = PostgresStore()
    except Exception as e:
        logger.error(f'Failed to connect to Postgres: {e}')
        return {'statusCode': 500, 'body': json.dumps('Failed to connect to Postgres')}

    try:
        games = store.get_games()
        if games is None:
            return {'statusCode': 500, 'body': json.dumps('Failed to load games')}

        if not games:
            logger.info('No games to process.')
            return {'statusCode': 200, 'body': json.dumps('No games to process')}

        for game in games:
            game_id, game_date, game_time, game_venue, game_type = game
            game_day = pdl.parse(game_date).format('dd, DD MMMM', locale='ru').capitalize()
            game_schedule = f'{game_day}, {game_time}' if game_time else game_day

            message = f'⏰ {game_schedule}\n\n📍 {game_venue}\n\n🎰 {game_type}'
            message_res = send_message(BOT_TOKEN, CHANNEL_ID, message)

            if not message_res:
                logger.error(f'Failed to send message for game {game_id}.')
                continue

            time.sleep(2)
            recent_updates = get_group_updates(BOT_TOKEN, store, BOT_NAME, _timeout=10)
            reply_id = get_message_ids(recent_updates)

            if not reply_id:
                logger.error(f'Failed to get reply ID for game {game_id}.')
                continue

            poll_question = 'Голосуем'
            poll_options = ['Иду', '+1', 'Не иду']
            poll_response = send_poll(BOT_TOKEN, GROUP_ID, poll_question, poll_options, reply_id)

            if not poll_response:
                logger.error(f'Failed to send poll for game {game_id}.')
                continue

            store.store_poll(
                poll_id=poll_response['poll']['id'],
                game_id=game_id,
                message_id=poll_response['message_id'],
            )

            if store.mark_poll_created(game_id):
                logger.info(f'Game {game_id} has been processed')
            else:
                logger.error(f'Poll was sent for game {game_id}, but Postgres was not updated.')

        return {'statusCode': 200, 'body': json.dumps('All games processed successfully')}
    finally:
        store.close()

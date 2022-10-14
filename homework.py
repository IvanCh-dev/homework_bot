import requests
import os
import time
import telegram
import logging
from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения ботом."""
    logging.info('Попытка бота отправить сообщение в чат')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Бот отправил сообщение в чат')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения ботом: {error}')


def get_api_answer(current_timestamp=int(time.time())):
    """Получения ответа от API Практикума."""
    params = {'from_date': current_timestamp}
    logging.info('Попытка получить ответ от API Практикума')
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error('Недоступность эндпоинта API Практикума')
            raise Exception('Недоступность эндпоинта API Практикума')
        return homework_statuses.json()
    except Exception as error:
        logging.error(f'Ошибка получить ответ от API Практикума: {error}')
        raise Exception(f'Ошибка получить ответ от API Практикума: {error}')


def check_response(response):
    """Проверка ответа от API Практикума."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарём')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response.keys():
        raise Exception('В ответе API отсутствует ключ "homeworks"')
    if 'current_date' not in response.keys():
        raise Exception('В ответе API отсутствует ключ "current_date"')
    if not isinstance(homeworks, list):
        raise Exception('Значение ключа "homeworks" не список')
    return homeworks


def parse_status(homework):
    """Получение статуса домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутсвует в ответе API Практикума')
    if 'status' not in homework:
        raise KeyError('Ключ status отсутвует в ответе API Практикума')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = 0
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if homeworks:
                    status = parse_status(homeworks[0])
                    send_message(bot, status)
                else:
                    logging.info('Изменения в домашних работах отсутствуют')
            except Exception as error:
                logging.error(f'Ошибка: {error}')
            finally:
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
    else:
        logging.critical('Отсутствие обязательных переменных окружения')
        raise Exception('Отсутствие обязательных переменных окружения')


if __name__ == '__main__':
    main()

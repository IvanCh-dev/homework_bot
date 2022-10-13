import requests
import os
import time
import telegram
import logging
from dotenv import load_dotenv


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
    '''Отправка сообщения ботом'''
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Бот отправил сообщение в чат')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения ботом: {error}')


def get_api_answer(current_timestamp=int(time.time())):
    '''Получения ответа от API Практикума'''
    params = {'from_date': current_timestamp}
    homework_statuses = requests.get(
        ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        logging.error('Недоступность эндпоинта API Практикума')
        raise Exception('Недоступность эндпоинта API Практикума')
    return homework_statuses.json()


def check_response(response):
    '''Проверка ответа от API Практикума'''
    if type(response) == dict:
        if len(response) == 0:
            logging.error('API вернул пустой словарь')
            raise Exception('API вернул пустой словарь')
        if 'homeworks' not in response.keys():
            logging.error('В ответе API отсутствует ключ "homeworks"')
            raise Exception('В ответе API отсутствует ключ "homeworks"')
        if 'current_date' not in response.keys():
            logging.error('В ответе API отсутствует ключ "current_date"')
            raise Exception('В ответе API отсутствует ключ "current_date"')
        if type(response['homeworks']) != list:
            logging.error('Значение ключа "homeworks" не список')
            raise Exception('Значение ключа "homeworks" не список')
        return response.get('homeworks')
    return response


def parse_status(homework):
    '''Получение статуса домашней работы'''
    if 'homework_name' not in homework:
        logging.error('Ключ homework_name отсутсвует в ответе API Практикума')
        raise KeyError('Ключ homework_name отсутсвует в ответе API Практикума')
    if 'status' not in homework:
        logging.error('Ключ status отсутвует в ответе API Практикума')
        raise KeyError('Ключ status отсутвует в ответе API Практикума')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(f'Неизвестный статус {homework_status}')
        raise Exception(f'Неизвестный статус {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    '''Проверка наличия токенов'''
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logging.critical('Отсутствие обязательных переменных окружения')
    return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    homeworks_dct = {}
    prev_response = None
    while True:
        try:
            response = get_api_answer(current_timestamp=current_timestamp)
            if response != prev_response:
                for homework in response.get('homeworks'):
                    homework_name = homework.get('homework_name')
                    homework_status = homework.get('status')
                    if homework_name in homeworks_dct:
                        if homework_status != homeworks_dct.get(homework_name):
                            homeworks_dct[homework_name] = homework_status
                            status = parse_status(homework)
                            send_message(bot, status)
                    else:
                        homeworks_dct[homework_name] = homework_status
                        status = parse_status(homework)
                        send_message(bot, status)
            prev_response = response
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

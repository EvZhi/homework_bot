import os
from http import HTTPStatus
import logging
import time
import requests
import sys
import exceptions
from telebot import TeleBot
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """Функция проверки доступности переменных окружения."""
    env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name_var, var in env_vars.items():
        if var is None or var == '':
            logging.critical(
                'Отуствует одна из обязательных переменных окружения: '
                f'"{name_var}". '
                'Программа принудительно остановлена!'
            )
            sys.exit()


def send_message(bot: TeleBot, message: str) -> None:
    """Функция отправки сообщения в ТГ-бот."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug('Сообщение успешно отправлено.')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(timestamp: int) -> dict:
    """Функция получения ответа от API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        logging.error(f'При запросе к API возникает исключение {error}')
    if response.status_code != HTTPStatus.OK:
        raise exceptions.StatusNotOkException(
            'Ошибка ответа. Статус код не равен 200'
        )
    return response.json()


def check_response(response: dict) -> None:
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'В ответе API структура данных не словарь.'
        )
    elif response.get('homeworks') is None:
        raise exceptions.NotKeyHomeworksException(
            ' в ответе API домашки нет ключа "homeworks"'
        )
    elif not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'В ответе API под ключом homeworks - не список'
        )


def parse_status(homework: dict) -> str:
    """Функция парсит статус из последней домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise exceptions.NotHomeworkNameException(
            'В ответе API домашней работы отсутвует ключ "homework_name"'
        )
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    if verdict is None:
        raise exceptions.NotStatusHomeworkException(
            'В ответе API домашней работы отсутвует статус.'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, [%(levelname)s], %(message)s'
    )
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if len(homeworks) == 0:
                logging.debug('Обновлений нет. Список домашних работ пуст.')
            else:
                send_message(
                    bot,
                    parse_status(homeworks[0])
                )
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

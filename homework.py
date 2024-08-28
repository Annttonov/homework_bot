import os
import time
import requests
from http import HTTPStatus

from dotenv import load_dotenv
from telebot import TeleBot
import logging
from logging.handlers import RotatingFileHandler

from constants import (
    ONE_DAY_AGO,
    RETRY_PERIOD,
    ENDPOINT,
    HOMEWORK_VERDICTS,
)
from exceptions import TokenError

load_dotenv()


logger = logging.getLogger('homework status TGbot')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%d.%m.%Y time: %H:%M',
)

strHandler = logging.StreamHandler()
rotHandler = RotatingFileHandler(
    filename='.log',
    mode='a',
    maxBytes=10000,
    encoding='utf-8',
)

strHandler.setFormatter(formatter)
rotHandler.setFormatter(formatter)
rotHandler.setLevel(logging.DEBUG)
logger.addHandler(strHandler)
logger.addHandler(rotHandler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def check_tokens():
    """Проверят наличие переменных окржения.

    В случае отсутствия хотя-бы одной из них - закрывает программу.
    """
    environment_variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    not_token = []
    for var in environment_variables:
        if not environment_variables[var]:
            not_token.append(var)
    try:
        if len(not_token) != 0:
            raise TokenError(not_token)
    except Exception as error:
        logger.critical(f'Отсутствует обязательная переменная окружения: '
                        f'{error} Программа принудительно остановлена.')
        raise SystemExit


def send_message(bot, message):
    """Отпраляет сообщение в телеграм-бот.

    Принимает объект телеграм-бота, и сообщение для отпраки.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f'Сообщение не отправлено!, возникла ошибка [{e}]')
        return
    logger.debug('Сообщение отправлено!')


def get_api_answer(timestamp=0):
    """Делает запрос к API практикума.

    Принимает временную метку, возвращет JSON-ответа.
    """
    params = {'from_date': timestamp}
    try:
        resp = requests.get(ENDPOINT, params=params, headers=HEADERS)
        if resp.status_code != HTTPStatus.OK:
            raise requests.exceptions.HTTPError()
    except requests.RequestException:
        logger.error(f'Некорректный запрос к API [{resp.url}]')
        raise requests.RequestException(f'Некорректный запрос к API '
                                        f'[{resp.url}]')
    return resp.json()


def check_response(response):
    """Проверяет запрос на валидность данных.

    Принимает объект запроса, возвращает объект домашки.
    """
    try:
        if not isinstance(response['homeworks'], list):
            raise TypeError
        result = response['homeworks'][0]
    except TypeError:
        message = 'Ошибка данных! Ожидался словарь.'
        logger.error(message)
        raise TypeError(message)
    except KeyError as error:
        message = f'Ошибка ключа. Ключ [{error}] не найден.'
        logger.error(message)
        raise KeyError(message)
    except IndexError:
        message = 'Нет заданий для проверки.'
        logger.debug(message)
        return message
    else:
        return result


def parse_status(homework):
    """проверят данные и формирует сообщение для отправки.

    Принимает объект домашки и возвращает сформированное сообщение
    """
    try:
        status = homework['status']
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        message = f'Ошибка ключа. Ключ {error} не найден!'
        logger.error(message)
        raise KeyError(message)
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    logger.debug(message)
    return message


def main():
    """Основная логика работы бота."""
    not_homeworks_message = 'Нет заданий для проверки.'
    message = None
    bot = TeleBot(token=TELEGRAM_TOKEN)

    while True:
        check_tokens()
        try:
            response = get_api_answer(ONE_DAY_AGO)
            data = check_response(response)
            if data == not_homeworks_message:
                send_message(bot, not_homeworks_message)
            else:
                result = parse_status(data)
                if result != message:
                    message = result
                    send_message(bot, message)
                else:
                    send_message(bot, 'Статус домашки не изменен.')
        except Exception as error:
            print(error)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

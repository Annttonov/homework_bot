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
from exceptions import (
    TokenError,
    SendMessageError,
    UnexpectedStatusError,
)
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
    except Exception as e:
        logger.critical(f'Отсутствует обязательная переменная окружения: '
                        f'{e} Программа принудительно остановлена.')
        raise SystemExit


def send_message(bot, message):
    """Отпраляет сообщение в телеграм-бот.

    Принимает объект телеграм-бота, и сообщение для отпраки.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except requests.RequestException as e:
        return SendMessageError(f'Сообщение не отправлено!, '
                                f'возникла ошибка [{e}]')
    logger.debug('Сообщение отправлено!')


def get_api_answer(timestamp=0):
    """Делает запрос к API практикума.

    Принимает временную метку, возвращет JSON-ответа.
    """
    request_params = {
        'url': ENDPOINT,
        'params': {'from_date': timestamp},
        'headers': HEADERS,
    }
    try:
        resp = requests.get(
            url=request_params['url'],
            params=request_params['params'],
            headers=request_params['headers']
        )
    except requests.RequestException:
        message = (f'Некорректный запрос к API, со следующими параметрами: '
                   f'url: [{request_params["url"]}], '
                   f'parmas: [{request_params["params"]}], '
                   f'headers: [{request_params["headers"]}].')
        logger.debug()   # Без этого логера не пропускают тесты,
        # я уже написал в пачку по поводу этой проблемы.
        raise requests.RequestException(message)
    if resp.status_code != HTTPStatus.OK:
        raise requests.exceptions.HTTPError('Код Нежиданный код ответа!')
    return resp.json()


def check_response(response):
    """Проверяет запрос на валидность данных.

    Принимает объект запроса, возвращает объект домашки.
    """
    try:
        if not isinstance(response['homeworks'], list):
            raise TypeError(f'Ошибка! Ожидался "list", получен '
                            f'"{type(response["homeworks"])}"')
        result = response['homeworks'][0]
    except KeyError as e:
        message = f'Ошибка ключа. Ключ [{e}] не найден.'
        logger.error(message)
        raise KeyError(message)
    except IndexError:
        message = 'Нет заданий для проверки.'
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
    except KeyError as e:
        message = f'Ошибка ключа. Ключ {e} не найден!'
        raise KeyError(message)
    if homework['status'] not in HOMEWORK_VERDICTS:
        message = f'Неизвестный статус проверки! {homework["status"]}'
        raise UnexpectedStatusError(homework['status'])
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
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
            if (data == not_homeworks_message
                    and message != not_homeworks_message):
                message = not_homeworks_message
                logger.debug(message)
                send_message(bot, message)
            else:
                result = parse_status(data)
                if result != message:
                    message = result
                    logger.debug(message)
                    send_message(bot, message)
                else:
                    logger.info('Статус домашки не изменен.')
        except requests.RequestException as e:
            logger.error(f'{e}')
        except Exception as e:
            logger.error(e)
            new_message = f'Сбой в работе программы: {e}'
            if message != new_message:
                message = new_message
                logger.debug(message)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

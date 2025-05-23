import time

timestamp = int(time.time())
ONE_DAY = 86400
ONE_MONTH = 2629743
ONE_MONTH_AGO = timestamp - ONE_MONTH
ONE_DAY_AGO = timestamp - ONE_DAY

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

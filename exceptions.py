class TokenError(NameError):
    """Исключение при отсутствии токена."""

    pass


class SendMessageError(Exception):
    """Исключение при ошибки стороннего API."""

    pass


class UnexpectedStatusError(KeyError):
    """Исключение при неожиданном статусе проверки домашки."""

    pass
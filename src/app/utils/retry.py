"""
Retry механизм с экспоненциальным backoff и jitter
"""
import time
import random
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Исключение после исчерпания всех попыток"""
    def __init__(self, message: str, last_exception: Exception):
        super().__init__(message)
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    Декоратор для повторных попыток вызова функции

    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для экспоненциального backoff
        jitter: Случайная добавка к задержке (0.1 = ±10%)
        exceptions: Какие исключения перехватывать
        logger: Логгер для записи попыток
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # Если это последняя попытка
                    if attempt == max_attempts:
                        error_msg = (f"Функция {func.__name__} завершилась с ошибкой "
                                   f"после {max_attempts} попыток. "
                                   f"Последняя ошибка: {str(e)}")
                        if logger:
                            logger.error(error_msg, exc_info=True)
                        raise RetryError(error_msg, last_exception)

                    # Рассчитываем задержку с экспоненциальным backoff
                    wait_time = delay * (backoff ** (attempt - 1))

                    # Добавляем jitter (случайность)
                    jitter_amount = wait_time * jitter
                    wait_time += random.uniform(-jitter_amount, jitter_amount)
                    wait_time = max(0, wait_time)  # Не может быть отрицательной

                    # Логируем информацию о повторной попытке
                    log_msg = (f"Попытка {attempt}/{max_attempts} функции "
                             f"{func.__name__} неудачна: {str(e)}. "
                             f"Повтор через {wait_time:.2f} секунд...")

                    if logger:
                        logger.warning(log_msg)
                    else:
                        # Единый формат для всех сообщений
                        print(f"WARNING: {log_msg}")

                    # Ждем перед следующей попыткой
                    time.sleep(wait_time)

            # Эта строка никогда не должна выполняться, но на всякий случай
            raise RetryError(f"Неизвестная ошибка в retry механизме", last_exception)

        return wrapper
    return decorator


# Специализированные декораторы для разных случаев
def retry_network(
        max_attempts: int = 3,
        delay: float = 2.0,
        backoff: float = 2.0,
        logger=None  # Добавляем параметр logger
):
    """Retry для сетевых ошибок"""
    import socket
    import requests

    return retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=(
            requests.exceptions.RequestException,
            socket.error,
            TimeoutError,
            ConnectionError,
            ValueError,
            RuntimeError,
            OSError
        ),
        logger=logger  # Передаём logger
    )

def retry_api(
    max_attempts: int = 5,
    delay: float = 1.0,
    backoff: float = 2.0
):
    """Retry для API ошибок (429 Too Many Requests, 500 Internal Server Error)"""
    import requests

    return retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=(
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )


def retry_imap(
    max_attempts: int = 3,
    delay: float = 3.0,
    backoff: float = 2.0
):
    """Retry для IMAP соединений"""
    return retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=(ConnectionError, TimeoutError)
    )

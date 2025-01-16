import os
import sys
import tempfile
import logging
import fcntl

logger = logging.getLogger(__name__)

def ensure_single_instance():
    """
    Гарантирует, что только один экземпляр бота может быть запущен одновременно.
    
    Использует блокировку файла для предотвращения множественного запуска.
    В Windows может потребоваться альтернативная реализация.
    """
    try:
        # Создаем файл блокировки во временной директории
        lock_file_path = os.path.join(tempfile.gettempdir(), 'telegram_bot.lock')
        
        # Открываем файл с эксклюзивной блокировкой
        lock_file = open(lock_file_path, 'w')
        
        try:
            # Пытаемся захватить блокировку
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, BlockingIOError):
            logger.error("Другой экземпляр бота уже запущен. Завершение.")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке единственного экземпляра: {e}")
        sys.exit(1)

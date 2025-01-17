import logging
import time
import psutil
import sentry_sdk
from typing import Dict, Any
import multiprocessing
import os
import signal

class SystemMonitor:
    def __init__(self, check_interval: int = 300):  # Увеличим интервал до 5 минут
        # Настройка Sentry для мониторинга ошибок
        sentry_sdk.init(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",  # Замените на ваш Sentry DSN
            traces_sample_rate=0.1,  # Уменьшаем частоту трассировки
            profiles_sample_rate=0.1,  # Уменьшаем частоту профилирования
        )
        self.check_interval = check_interval
        self.last_metrics = None
        self.log_file = '/app/logs/system_monitoring.log'
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик системы с минимальной нагрузкой
        """
        try:
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),  # Замер за 1 секунду
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": self._get_network_io(),
                "timestamp": time.time()
            }
        except Exception as e:
            logging.error(f"Error getting system metrics: {e}")
            return {}

    def _get_network_io(self) -> Dict[str, float]:
        """
        Получение метрик сетевого трафика
        """
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            }
        except Exception as e:
            logging.error(f"Error getting network IO: {e}")
            return {"bytes_sent": 0, "bytes_recv": 0}

    def log_system_metrics(self):
        """
        Логирование системных метрик с минимальной нагрузкой
        """
        try:
            metrics = self.get_system_metrics()
            
            if not metrics:
                return

            # Логирование в файл с ограничением размера
            self._rotate_log_file()
            
            with open(self.log_file, 'a') as f:
                log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - System Metrics: {metrics}\n"
                f.write(log_entry)

            # Проверка критических ресурсов
            self._check_critical_resources(metrics)

        except Exception as e:
            logging.error(f"Error in system metrics logging: {e}")

    def _rotate_log_file(self, max_size_mb: int = 10):
        """
        Ротация лог-файла для предотвращения чрезмерного роста
        """
        try:
            if os.path.exists(self.log_file):
                size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
                if size_mb > max_size_mb:
                    # Создаем архивную копию
                    archive_file = f"{self.log_file}.old"
                    os.replace(self.log_file, archive_file)
        except Exception as e:
            logging.error(f"Error rotating log file: {e}")

    def _check_critical_resources(self, metrics: Dict[str, Any]):
        """
        Проверка критических ресурсов с уведомлениями
        """
        try:
            if metrics.get('cpu_usage', 0) > 90:
                logging.warning(f"High CPU usage: {metrics['cpu_usage']}%")
                sentry_sdk.capture_message(f"High CPU usage: {metrics['cpu_usage']}%", level="warning")

            if metrics.get('memory_usage', 0) > 85:
                logging.warning(f"High memory usage: {metrics['memory_usage']}%")
                sentry_sdk.capture_message(f"High memory usage: {metrics['memory_usage']}%", level="warning")

            if metrics.get('disk_usage', 0) > 90:
                logging.warning(f"High disk usage: {metrics['disk_usage']}%")
                sentry_sdk.capture_message(f"High disk usage: {metrics['disk_usage']}%", level="warning")
        except Exception as e:
            logging.error(f"Error checking critical resources: {e}")

def monitor_process():
    """
    Функция для запуска мониторинга в отдельном процессе
    """
    monitor = SystemMonitor()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logging.info("Monitoring process received stop signal")
        exit(0)

    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            monitor.log_system_metrics()
            time.sleep(monitor.check_interval)
        except Exception as e:
            logging.error(f"Unexpected error in monitoring process: {e}")
            time.sleep(monitor.check_interval)

def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/app/logs/monitoring_process.log'),
            logging.StreamHandler()
        ]
    )

    # Запуск мониторинга в отдельном процессе
    process = multiprocessing.Process(target=monitor_process)
    process.start()
    process.join()

if __name__ == "__main__":
    main()

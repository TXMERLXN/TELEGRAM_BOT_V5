import logging
import time
import psutil
import sentry_sdk
from typing import Dict, Any

class SystemMonitor:
    def __init__(self):
        # Настройка Sentry для мониторинга ошибок
        sentry_sdk.init(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",  # Замените на ваш Sentry DSN
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик системы
        """
        return {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": self._get_network_io(),
            "timestamp": time.time()
        }

    def _get_network_io(self) -> Dict[str, float]:
        """
        Получение метрик сетевого трафика
        """
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }

    def log_system_metrics(self):
        """
        Логирование системных метрик
        """
        metrics = self.get_system_metrics()
        logging.info(f"System Metrics: {metrics}")
        
        # Отправка метрик в Sentry
        with sentry_sdk.start_transaction(name="system_metrics"):
            sentry_sdk.set_context("system", metrics)

    def check_critical_resources(self):
        """
        Проверка критических ресурсов
        """
        metrics = self.get_system_metrics()
        
        if metrics['cpu_usage'] > 90:
            logging.warning(f"High CPU usage: {metrics['cpu_usage']}%")
            sentry_sdk.capture_message("High CPU Usage", level="warning")
        
        if metrics['memory_usage'] > 90:
            logging.warning(f"High Memory usage: {metrics['memory_usage']}%")
            sentry_sdk.capture_message("High Memory Usage", level="warning")

def setup_logging():
    """
    Настройка логирования
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    monitor = SystemMonitor()
    
    while True:
        monitor.log_system_metrics()
        monitor.check_critical_resources()
        time.sleep(60)  # Опрос каждую минуту

if __name__ == "__main__":
    main()

import logging
import time
import psutil
import sentry_sdk
from typing import Dict, Any
import multiprocessing
import os
import signal
import traceback
import random

class AdaptiveSystemMonitor:
    def __init__(self, base_interval: int = 300, max_interval: int = 1800):
        """
        Адаптивный монитор системных ресурсов
        
        :param base_interval: Базовый интервал между замерами (секунды)
        :param max_interval: Максимальный интервал между замерами
        """
        sentry_sdk.init(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )
        
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.current_interval = base_interval
        self.log_file = '/app/logs/system_monitoring.log'
        
        # Создание директории для логов
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получение системных метрик с минимальной нагрузкой
        """
        try:
            # Используем статистику без блокировки
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            metrics = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": disk.percent,
                "network_sent": net_io.bytes_sent,
                "network_recv": net_io.bytes_recv,
                "timestamp": time.time()
            }
            
            return metrics
        
        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")
            logging.error(traceback.format_exc())
            return {}

    def adjust_monitoring_interval(self, metrics: Dict[str, Any]) -> None:
        """
        Динамическая регулировка интервала мониторинга
        """
        cpu_usage = metrics.get('cpu_usage', 0)
        
        if cpu_usage > 80:
            # При высокой нагрузке увеличиваем интервал
            self.current_interval = min(self.current_interval * 2, self.max_interval)
        elif cpu_usage < 20:
            # При низкой нагрузке уменьшаем интервал
            self.current_interval = max(self.current_interval // 2, self.base_interval)
        
        # Добавляем небольшой случайный джиттер
        jitter = random.uniform(0.8, 1.2)
        self.current_interval *= jitter

    def log_system_metrics(self):
        """
        Логирование системных метрик с адаптивным интервалом
        """
        try:
            metrics = self.get_system_metrics()
            
            if not metrics:
                return

            # Ротация лог-файла
            self._rotate_log_file()
            
            # Запись метрик в лог-файл
            with open(self.log_file, 'a') as f:
                log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Metrics: {metrics}\n"
                f.write(log_entry)

            # Проверка критических ресурсов
            self._check_critical_resources(metrics)
            
            # Адаптация интервала мониторинга
            self.adjust_monitoring_interval(metrics)

        except Exception as e:
            logging.error(f"Error in system metrics logging: {e}")
            logging.error(traceback.format_exc())

    def _rotate_log_file(self, max_size_mb: int = 10):
        """
        Ротация лог-файла с ограничением размера
        """
        try:
            if os.path.exists(self.log_file):
                size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
                if size_mb > max_size_mb:
                    archive_file = f"{self.log_file}.old"
                    os.replace(self.log_file, archive_file)
        except Exception as e:
            logging.error(f"Error rotating log file: {e}")

    def _check_critical_resources(self, metrics: Dict[str, Any]):
        """
        Проверка критических ресурсов с расширенной диагностикой
        """
        try:
            cpu_usage = metrics.get('cpu_usage', 0)
            memory_usage = metrics.get('memory_usage', 0)
            disk_usage = metrics.get('disk_usage', 0)

            if cpu_usage > 90:
                message = f"🚨 High CPU Usage: {cpu_usage}% - Potential Performance Issue"
                logging.warning(message)
                sentry_sdk.capture_message(message, level="error")

            if memory_usage > 85:
                message = f"🚨 High Memory Usage: {memory_usage}% - Low Memory Available"
                logging.warning(message)
                sentry_sdk.capture_message(message, level="warning")

            if disk_usage > 90:
                message = f"🚨 High Disk Usage: {disk_usage}% - Low Disk Space"
                logging.warning(message)
                sentry_sdk.capture_message(message, level="warning")

        except Exception as e:
            logging.error(f"Error checking critical resources: {e}")

def monitor_process():
    """
    Функция для запуска мониторинга в отдельном процессе
    """
    monitor = AdaptiveSystemMonitor()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logging.info("🛑 Monitoring process received stop signal")
        exit(0)

    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            monitor.log_system_metrics()
            time.sleep(monitor.current_interval)
        except Exception as e:
            logging.error(f"Unexpected error in monitoring process: {e}")
            logging.error(traceback.format_exc())
            time.sleep(monitor.current_interval)

def main():
    # Запуск мониторинга в отдельном процессе
    process = multiprocessing.Process(target=monitor_process)
    process.start()
    process.join()

if __name__ == "__main__":
    main()

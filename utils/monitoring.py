import logging
import time
import psutil
import sentry_sdk
from typing import Dict, Any
import threading
import queue
import os

class SystemMonitor:
    def __init__(self, check_interval: int = 60):
        # Настройка Sentry для мониторинга ошибок
        sentry_sdk.init(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",  # Замените на ваш Sentry DSN
            traces_sample_rate=0.1,  # Уменьшаем частоту трассировки
            profiles_sample_rate=0.1,  # Уменьшаем частоту профилирования
        )
        self.check_interval = check_interval
        self.last_metrics = None
        self.metrics_queue = queue.Queue()
        self.stop_event = threading.Event()

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик системы с кэшированием и минимальной нагрузкой
        """
        current_metrics = {
            "cpu_usage": psutil.cpu_percent(interval=1),  # Замер за 1 секунду
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": self._get_network_io(),
            "timestamp": time.time()
        }
        return current_metrics

    def _get_network_io(self) -> Dict[str, float]:
        """
        Получение метрик сетевого трафика
        """
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }

    def _is_metrics_changed(self, current_metrics: Dict[str, Any]) -> bool:
        """
        Проверка значительных изменений в метриках
        """
        if not self.last_metrics:
            self.last_metrics = current_metrics
            return True
        
        # Проверяем изменения с погрешностью
        changes = [
            abs(current_metrics['cpu_usage'] - self.last_metrics['cpu_usage']) > 10,
            abs(current_metrics['memory_usage'] - self.last_metrics['memory_usage']) > 5,
            abs(current_metrics['disk_usage'] - self.last_metrics['disk_usage']) > 2
        ]
        
        self.last_metrics = current_metrics
        return any(changes)

    def check_critical_resources(self, metrics: Dict[str, Any]):
        """
        Проверка критических ресурсов с более мягкими порогами
        """
        if metrics['cpu_usage'] > 90:
            logging.warning(f"High CPU usage: {metrics['cpu_usage']}%")
        
        if metrics['memory_usage'] > 85:
            logging.warning(f"High memory usage: {metrics['memory_usage']}%")
        
        if metrics['disk_usage'] > 90:
            logging.warning(f"High disk usage: {metrics['disk_usage']}%")

    def _metrics_logger(self):
        """
        Поток для логирования метрик
        """
        while not self.stop_event.is_set():
            try:
                metrics = self.metrics_queue.get(timeout=self.check_interval)
                logging.info(f"System Metrics: {metrics}")
                
                # Отправка метрик в Sentry только при значительных изменениях
                if self._is_metrics_changed(metrics):
                    with sentry_sdk.start_transaction(name="system_metrics"):
                        sentry_sdk.set_context("system", metrics)
                
                # Проверка критических ресурсов
                self.check_critical_resources(metrics)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error in system metrics logging: {e}")

    def start_monitoring(self):
        """
        Запуск мониторинга в отдельном потоке
        """
        # Поток для логирования метрик
        logger_thread = threading.Thread(target=self._metrics_logger, daemon=True)
        logger_thread.start()

        # Основной поток сбора метрик
        while not self.stop_event.is_set():
            try:
                metrics = self.get_system_metrics()
                self.metrics_queue.put(metrics)
                time.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
                time.sleep(self.check_interval)

    def stop_monitoring(self):
        """
        Остановка мониторинга
        """
        self.stop_event.set()

def setup_logging():
    """
    Настройка логирования
    """
    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'system_monitoring.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    monitor = SystemMonitor(check_interval=60)  # Проверка каждую минуту
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()

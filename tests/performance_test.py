from locust import HttpUser, task, between

class BotPerformanceTest(HttpUser):
    wait_time = between(1, 5)  # Время между запросами

    @task(1)
    def test_webhook(self):
        """
        Тестирование webhook эндпоинта
        """
        self.client.post("/webhook", json={
            "message": "Performance test"
        })

    @task(2)
    def test_status(self):
        """
        Проверка статуса приложения
        """
        self.client.get("/status")

    def on_start(self):
        """
        Действия перед началом теста
        """
        pass

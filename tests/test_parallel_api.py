import asyncio
import logging
import sys
import os

# Добавляем родительскую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.runninghub import RunningHubAPI
from config import load_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_parallel_requests():
    """
    Тестирование параллельных запросов к RunningHub API
    """
    config = load_config()
    api = RunningHubAPI()
    
    # Пути к тестовым изображениям
    product_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_images", "product.jpg")
    background_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_images", "background.jpg")
    
    if not os.path.exists(product_file) or not os.path.exists(background_file):
        logger.error("Test images not found")
        return
    
    # Запускаем 3 параллельных запроса
    tasks = []
    for i in range(3):
        user_id = i + 1  # Используем числовой ID
        logger.info(f"Creating task for user {user_id}")
        
        with open(product_file, 'rb') as f_product, open(background_file, 'rb') as f_background:
            task = api.generate_product_photo(
                user_id=user_id,
                product_image=f_product.read(),
                background_image=f_background.read()
            )
            tasks.append(task)
    
    try:
        # Запускаем все задачи параллельно
        results = await asyncio.gather(*tasks)
        
        # Анализируем результаты
        for i, task_id in enumerate(results):
            if task_id:
                logger.info(f"Task {i} created successfully with ID: {task_id}")
            else:
                logger.error(f"Task {i} creation failed")
                
        # Ждем завершения всех задач
        for i, task_id in enumerate(results):
            if task_id:
                logger.info(f"Waiting for task {task_id} completion...")
                status = "processing"
                while status == "processing":
                    status, result_url = await api.get_generation_status(task_id)
                    if status == "completed":
                        logger.info(f"Task {task_id} completed successfully")
                    elif status == "failed":
                        logger.error(f"Task {task_id} failed")
                    else:
                        await asyncio.sleep(5)  # Ждем 5 секунд перед следующей проверкой
                        
    except Exception as e:
        logger.error(f"Error during parallel testing: {str(e)}")

if __name__ == "__main__":
    # Запускаем тест
    logger.info("Starting parallel API test")
    asyncio.run(test_parallel_requests())
    logger.info("Test completed")

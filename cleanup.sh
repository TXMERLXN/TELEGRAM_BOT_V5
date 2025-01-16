#!/bin/bash

# Удаление устаревших файлов
rm -f bot.py
rm -f amvera.yaml
rm -f "RunningHub API Readme 17d409acaae080da85a6f50695c64f62.md"

# Удаление тестовых изображений
rm -f image\ 1.png
rm -f image\ 2.png
rm -f image\ 3.png
rm -f image\ 4.png
rm -f image\ 5.png
rm -f image.png

# Удаление служебных директорий
rm -rf .pytest_cache
rm -rf .venv
rm -rf __pycache__
rm -rf sentry
rm -rf temp

# Очистка кэша Python в поддиректориях
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete

echo "Cleanup completed successfully!"

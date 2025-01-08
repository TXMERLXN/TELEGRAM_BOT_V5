from aiogram.utils.markdown import hbold, hitalic, hcode

def WELCOME_MESSAGE(name: str) -> str:
    return (
        f"👋 Привет, {name}!\n\n"
        f"Я помогу тебе с обработкой изображений. Выбери нужную функцию:\n\n"
        f"📷 Сгенерировать фото продукта - создам фото для вашего продукта\n"
        f"❓ Помощь - подробная информация о работе бота"
    )

def HELP_MESSAGE() -> str:
    return (
        "🤖 Как пользоваться ботом:\n\n"
        "1. Выберите функцию 'Сгенерировать фото продукта'\n"
        "2. Отправьте фотографию вашего продукта\n"
        "3. Отправьте фотографию с референсом фона/окружения\n"
        "4. Дождитесь результата генерации\n\n"
        "Бот создаст новое изображение вашего продукта с выбранным фоном.\n"
        "Для лучшего результата:\n"
        "• Фото продукта должно быть качественным и четким\n"
        "• Фон на фото продукта желательно должен быть однородным\n"
        "• Референс фона должен соответствовать желаемому результату"
    )

# Сообщения о генерации
def GENERATION_STARTED() -> str:
    return "🔄 Начинаю генерацию изображения...\n\nДля отмены нажмите кнопку ниже"

def GENERATION_CANCELLED() -> str:
    return "❌ Генерация отменена"

def GENERATION_COMPLETE() -> str:
    return "✨ Готово! Вот результат генерации:"

def GENERATION_ERROR() -> str:
    return "❌ Произошла ошибка при генерации. Пожалуйста, попробуйте еще раз."
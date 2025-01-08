from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import asyncio
from typing import Optional

from services.runninghub import RunningHubAPI
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_result_keyboard, get_cancel_keyboard
from messages import (
    GENERATION_STARTED,
    GENERATION_COMPLETE,
    GENERATION_ERROR,
    GENERATION_CANCELLED
)

router = Router()
runninghub = RunningHubAPI()
logger = logging.getLogger(__name__)

# Словарь для хранения задач генерации
generation_tasks: dict[int, asyncio.Task] = {}

class GenerationState(StatesGroup):
    waiting_for_product_image = State()
    waiting_for_background_image = State()
    generating = State()

@router.callback_query(F.data == "product")
async def product_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации фото продукта"""
    logger.info("Начало генерации фото продукта")
    # Сначала очищаем состояние, чтобы начать с чистого листа
    await state.clear()
    await state.set_state(GenerationState.waiting_for_product_image)
    await state.update_data(workflow="product", message_id=callback.message.message_id)
    await callback.answer()
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer(
        "Отправьте фотографию продукта",
        reply_markup=get_back_keyboard()
    )

@router.message(GenerationState.waiting_for_product_image, F.photo)
async def process_product_image(message: Message, state: FSMContext):
    """Обработка фотографии продукта"""
    logger.info("Получена фотография продукта")
    await state.update_data(product_image=message.photo[-1].file_id)
    await state.set_state(GenerationState.waiting_for_background_image)
    await message.answer(
        "Теперь отправьте фотографию с референсом фона/окружения",
        reply_markup=get_back_keyboard()
    )

@router.message(GenerationState.waiting_for_background_image, F.photo)
async def process_background_image(message: Message, state: FSMContext):
    """Обработка фотографии фона"""
    logger.info("Получена фотография фона")
    data = await state.get_data()
    product_image = data["product_image"]
    
    # Отправляем сообщение о начале генерации с кнопкой отмены
    status_message = await message.answer(
        GENERATION_STARTED(),
        reply_markup=get_cancel_keyboard()
    )
    
    # Создаем и сохраняем задачу генерации
    task = asyncio.create_task(
        generate_photo(message, state, product_image, message.photo[-1].file_id, status_message)
    )
    generation_tasks[message.from_user.id] = task
    
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Задача генерации отменена пользователем")
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        await status_message.edit_text(
            GENERATION_ERROR(),
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        # Удаляем задачу из словаря
        generation_tasks.pop(message.from_user.id, None)
        await state.clear()

async def generate_photo(
    message: Message,
    state: FSMContext,
    product_image: str,
    background_image: str,
    status_message: Message
) -> Optional[str]:
    """Генерация фото с возможностью отмены"""
    try:
        # Устанавливаем состояние генерации
        await state.set_state(GenerationState.generating)
        
        # Генерируем фото
        result = await runninghub.generate_product_photo(product_image, background_image)
        if result:
            logger.info("Фото успешно сгенерировано")
            # Отправляем результат с клавиатурой
            await message.answer_photo(
                result,
                caption=GENERATION_COMPLETE(),
                reply_markup=get_result_keyboard()
            )
            # Удаляем сообщение о генерации
            await status_message.delete()
            return result
        else:
            logger.error("Ошибка генерации: результат пустой")
            await status_message.edit_text(
                GENERATION_ERROR(),
                reply_markup=get_main_menu_keyboard()
            )
            return None
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        await status_message.edit_text(
            GENERATION_ERROR(),
            reply_markup=get_main_menu_keyboard()
        )
        return None

@router.callback_query(F.data == "cancel_generation")
async def cancel_generation(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены генерации"""
    user_id = callback.from_user.id
    if user_id in generation_tasks:
        # Отменяем задачу генерации
        generation_tasks[user_id].cancel()
        # Обновляем сообщение
        await callback.message.edit_text(
            GENERATION_CANCELLED(),
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer("Генерация отменена")
    else:
        await callback.answer("Нет активной генерации для отмены")

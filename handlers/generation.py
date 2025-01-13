import asyncio
import logging
import os
from typing import Optional, Union

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, CallbackQuery, URLInputFile

from config import config
from services.account_manager import account_manager
from services.runninghub import RunningHubAPI
from services.task_queue import task_queue
from states.generation import GenerationState
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_result_keyboard, get_cancel_keyboard
from messages import (
    GENERATION_STARTED,
    GENERATION_FAILED,
    SEND_PRODUCT_PHOTO,
    SEND_BACKGROUND_PHOTO,
    PROCESSING_STARTED,
    PROCESSING_COMPLETE,
    PROCESSING_FAILED,
)

router = Router()

# Инициализация API и очереди задач
@router.startup()
async def setup_api():
    """Инициализация API и очереди задач"""
    # Инициализируем очередь задач
    task_queue.add_account(
        api_key=os.getenv('RUNNINGHUB_API_KEY'),
        workflow_id=os.getenv('RUNNINGHUB_WORKFLOW_PRODUCT'),
        max_tasks=1
    )

logger = logging.getLogger(__name__)

@router.message(Command("generate"))
@router.callback_query(F.data == "generate")
async def start_generation(event: Union[Message, CallbackQuery], state: FSMContext):
    """Начало процесса генерации"""
    logger.info(f"User {event.from_user.id} started generation")
    
    # Очищаем предыдущее состояние
    await state.clear()
    await state.set_state(GenerationState.waiting_for_product)
    
    # Отправляем сообщение в зависимости от типа события
    if isinstance(event, CallbackQuery):
        await event.message.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())

@router.message(GenerationState.waiting_for_product, F.photo)
async def handle_product_photo(message: Message, state: FSMContext):
    """Обработка фото продукта"""
    logger.info(f"User {message.from_user.id} sent product photo")
    await state.update_data(product_photo_id=message.photo[-1].file_id)
    await state.set_state(GenerationState.waiting_for_background)
    await message.answer(SEND_BACKGROUND_PHOTO, reply_markup=get_back_keyboard())

@router.message(GenerationState.waiting_for_background, F.photo)
async def handle_background_photo(message: Message, state: FSMContext):
    """Обработка фото фона"""
    logger.info(f"User {message.from_user.id} sent background photo")
    
    # Получаем сохраненные данные
    data = await state.get_data()
    product_photo_id = data.get('product_photo_id')
    background_photo_id = message.photo[-1].file_id
    
    if not product_photo_id:
        await message.answer(GENERATION_FAILED)
        await state.clear()
        return
    
    await state.update_data(background_photo_id=background_photo_id)
    
    # Устанавливаем состояние обработки
    await state.set_state(GenerationState.processing)
    await process_photos(message, state)

async def process_photos(message: Message, state: FSMContext) -> None:
    """Обработка фотографий"""
    data = await state.get_data()
    product_photo_id = data.get('product_photo_id')
    background_photo_id = data.get('background_photo_id')
    
    if not product_photo_id or not background_photo_id:
        await message.answer("Ошибка: не найдены фотографии для обработки")
        return
        
    processing_message = await message.answer("⏳ Обрабатываю фотографии...")
    
    try:
        # Используем TaskQueue для обработки фотографий
        result_url = await task_queue.process_photos(
            message.from_user.id,
            product_photo_id,
            background_photo_id
        )
        
        if result_url:
            await processing_message.delete()
            await message.answer_photo(
                URLInputFile(result_url),
                caption="✅ Готово! Вот результат обработки.",
                reply_markup=get_result_keyboard()
            )
        else:
            await processing_message.edit_text(
                "❌ Не удалось обработать фотографии. Попробуйте еще раз.",
                reply_markup=get_result_keyboard()
            )
    except Exception as e:
        logger.error(f"Error processing photos: {str(e)}")
        await processing_message.edit_text(
            "❌ Произошла ошибка при обработке фотографий. Попробуйте еще раз.",
            reply_markup=get_result_keyboard()
        )
    finally:
        await state.clear()

@router.message(GenerationState.waiting_for_product)
@router.message(GenerationState.waiting_for_background)
async def handle_invalid_photo(message: Message):
    """Обработка неверного формата фото"""
    await message.answer("Пожалуйста, отправьте фотографию")

@router.callback_query(F.data == "cancel")
async def cancel_generation(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса генерации"""
    logger.info(f"User {callback.from_user.id} cancelled generation")
    await state.clear()
    await callback.message.answer("Генерация отменена", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему шагу"""
    logger.info(f"User {callback.from_user.id} went back")
    current_state = await state.get_state()
    
    if current_state == GenerationState.waiting_for_background:
        await state.set_state(GenerationState.waiting_for_product)
        await callback.message.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())
    
    await callback.answer()

@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    logger.info(f"User {callback.from_user.id} returned to menu")
    await state.clear()
    await callback.message.answer("Вы вернулись в главное меню", reply_markup=get_main_menu_keyboard())
    await callback.answer()

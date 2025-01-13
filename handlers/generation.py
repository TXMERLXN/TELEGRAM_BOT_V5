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
async def setup_api() -> None:
    """Настройка API клиента"""
    try:
        api = RunningHubAPI(
            api_url=config.runninghub.api_url,
            api_key=config.runninghub.accounts[0].api_key,
            workflow_id=config.runninghub.accounts[0].workflows["product"]
        )
        # Проверяем статус аккаунта перед добавлением
        if await api._check_account_status():
            task_queue.add_account(api, config.runninghub.max_tasks)
            logger.info("Successfully initialized RunningHub API client")
        else:
            logger.error("Failed to initialize RunningHub API: invalid account status")
            raise ValueError("Invalid RunningHub account status")
    except Exception as e:
        logger.error(f"Failed to setup RunningHub API: {str(e)}", exc_info=True)
        raise

logger = logging.getLogger(__name__)

@router.message(Command("generate"))
@router.callback_query(F.data == "generate")
async def start_generation(event: Union[Message, CallbackQuery], state: FSMContext):
    """Начало процесса генерации"""
    logger.info(f"User {event.from_user.id} started generation")
    
    # Проверяем доступность API
    if not task_queue.accounts:
        error_msg = "Generation service is temporarily unavailable"
        logger.error(error_msg)
        if isinstance(event, CallbackQuery):
            await event.message.answer(error_msg)
            await event.answer()
        else:
            await event.answer(error_msg)
        return
    
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
    try:
        if not message.photo:
            await handle_invalid_photo(message)
            return
            
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Сохраняем информацию в состоянии
        await state.update_data(product_photo=file_info.file_id)
        await state.set_state(GenerationState.waiting_for_background)
        
        await message.answer(
            SEND_BACKGROUND_PHOTO,
            reply_markup=get_cancel_keyboard()
        )
    except Exception as e:
        logger.error(f"Error handling product photo: {str(e)}", exc_info=True)
        await message.answer(GENERATION_FAILED)
        await state.clear()

@router.message(GenerationState.waiting_for_background, F.photo)
async def handle_background_photo(message: Message, state: FSMContext):
    """Обработка фото фона"""
    try:
        if not message.photo:
            await handle_invalid_photo(message)
            return
            
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Получаем предыдущие данные
        data = await state.get_data()
        product_photo = data.get("product_photo")
        
        if not product_photo:
            logger.error("Product photo not found in state")
            await message.answer(GENERATION_FAILED)
            await state.clear()
            return
            
        # Сохраняем информацию в состоянии
        await state.update_data(background_photo=file_info.file_id)
        await state.set_state(GenerationState.processing)
        
        # Запускаем обработку
        status_message = await message.answer(PROCESSING_STARTED)
        asyncio.create_task(process_photos(message, state, status_message))
    except Exception as e:
        logger.error(f"Error handling background photo: {str(e)}", exc_info=True)
        await message.answer(GENERATION_FAILED)
        await state.clear()

async def process_photos(message: Message, state: FSMContext, status_message: Message) -> None:
    """Обработка фотографий"""
    data = await state.get_data()
    product_photo = data.get("product_photo")
    background_photo = data.get("background_photo")
    
    if not product_photo or not background_photo:
        await status_message.edit_text(
            "❌ Не удалось обработать фотографии. Попробуйте еще раз.",
            reply_markup=get_result_keyboard()
        )
        return
        
    try:
        # Используем TaskQueue для обработки фотографий
        result_url = await task_queue.process_photos(
            message.from_user.id,
            product_photo,
            background_photo
        )
        
        if result_url:
            await status_message.delete()
            await message.answer_photo(
                URLInputFile(result_url),
                caption="✅ Готово! Вот результат обработки.",
                reply_markup=get_result_keyboard()
            )
        else:
            await status_message.edit_text(
                "❌ Не удалось обработать фотографии. Попробуйте еще раз.",
                reply_markup=get_result_keyboard()
            )
    except Exception as e:
        logger.error(f"Error processing photos: {str(e)}")
        await status_message.edit_text(
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

import asyncio
import logging
from typing import Optional

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
runninghub = None

async def init_runninghub(bot: Bot):
    """Инициализация RunningHub API"""
    global runninghub
    runninghub = RunningHubAPI(
        bot=bot,
        api_url=config.runninghub.api_url,
        task_timeout=config.runninghub.task_timeout,
        retry_delay=config.runninghub.retry_delay,
        max_retries=config.runninghub.max_retries,
        polling_interval=config.runninghub.polling_interval
    )
    await runninghub.initialize()

logger = logging.getLogger(__name__)

@router.message(Command("generate"))
@router.callback_query(F.data == "generate")
async def start_generation(event: Message | CallbackQuery, state: FSMContext):
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
    await state.update_data(product_photo=message.photo[-1].file_id)
    await state.set_state(GenerationState.waiting_for_background)
    await message.answer(SEND_BACKGROUND_PHOTO, reply_markup=get_back_keyboard())

@router.message(GenerationState.waiting_for_background, F.photo)
async def handle_background_photo(message: Message, state: FSMContext):
    """Обработка фото фона"""
    logger.info(f"User {message.from_user.id} sent background photo")
    
    # Получаем сохраненные данные
    data = await state.get_data()
    product_photo_id = data.get('product_photo')
    
    if not product_photo_id:
        await message.answer(GENERATION_FAILED)
        await state.clear()
        return
    
    # Устанавливаем состояние обработки
    await state.set_state(GenerationState.processing)
    processing_message = await message.answer(PROCESSING_STARTED)
    
    try:
        # Добавляем задачу в очередь
        task = await task_queue.add_task(
            runninghub.process_photos,
            product_photo_id,
            message.photo[-1].file_id,
            message.from_user.id
        )
        
        # Сохраняем ID сообщения для обновления
        await state.update_data(processing_message_id=processing_message.message_id)
        
        # Запускаем задачу
        asyncio.create_task(process_generation_task(message, state, task))
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        await message.answer(GENERATION_FAILED)
        await state.clear()

async def process_generation_task(message: Message, state: FSMContext, task):
    """Обработка задачи генерации"""
    try:
        result = await task
        if result and isinstance(result, str):
            # Отправляем результат
            await message.answer_photo(
                FSInputFile(result),
                caption=PROCESSING_COMPLETE,
                reply_markup=get_result_keyboard()
            )
        else:
            await message.answer(PROCESSING_FAILED)
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        await message.answer(PROCESSING_FAILED)
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

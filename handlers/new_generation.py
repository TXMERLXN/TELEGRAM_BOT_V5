import asyncio
import logging
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, URLInputFile
from aiogram.fsm.state import State, StatesGroup

from services.integration import integration_service
from keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_result_keyboard
from messages import (
    GENERATION_STARTED,
    GENERATION_FAILED,
    SEND_PRODUCT_PHOTO,
    SEND_BACKGROUND_PHOTO,
    PROCESSING_COMPLETE,
    PROCESSING_FAILED,
    IN_QUEUE
)

router = Router()
router.callback_query()

class GenerationStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_background = State()
    processing = State()

@router.callback_query(F.data == "generate")
async def start_generation(callback: CallbackQuery, state: FSMContext):
    """Начало процесса генерации"""
    await state.clear()
    await state.set_state(GenerationStates.waiting_for_product)
    await callback.message.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(Command("generate"))
async def start_generation_command(message: Message, state: FSMContext):
    """Альтернативный способ запуска генерации через команду"""
    await start_generation(message, state)

@router.message(F.photo, GenerationStates.waiting_for_product)
async def process_product_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка фотографии продукта"""
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    # Сохраняем временный файл и получаем URL
    temp_file_path = f"temp/product_{photo.file_id}.jpg"
    file_data = await bot.download_file(file.file_path)
    with open(temp_file_path, "wb") as f:
        f.write(file_data.read())

    if not temp_file_path:
        raise ValueError("Temp file path is not defined")
        
    if not temp_file_path:
        raise ValueError("Failed to generate product photo URL")
        
    # Сохраняем URL и ID в состоянии
    await state.update_data(
        product_photo_url=f"file://{temp_file_path}",
        product_photo_id=photo.file_id
    )
    await state.set_state(GenerationStates.waiting_for_background)
    await message.answer(SEND_BACKGROUND_PHOTO, reply_markup=get_cancel_keyboard())

@router.message(F.photo, GenerationStates.waiting_for_background)
async def process_background_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка фонового изображения и запуск генерации"""
    data = await state.get_data()
    product_photo_url = data.get("product_photo_url")
    if not product_photo_url:
        raise ValueError("Product photo URL is not defined")

    background_photo = message.photo[-1]
    background_file = await bot.get_file(background_photo.file_id)
    # Сохраняем временный файл и получаем URL
    temp_file_path = f"temp/background_{background_photo.file_id}.jpg"
    file_data = await bot.download_file(background_file.file_path)
    with open(temp_file_path, "wb") as f:
        f.write(file_data.read())

    background_url = f"file://{temp_file_path}"

    try:
        # Добавляем задачу в очередь через IntegrationService
        await integration_service.add_generation_task(
            product_image_url=product_photo_url,
            background_image_url=background_url,
            callback=lambda result: handle_generation_result(result, message, state)
        )

        await message.answer(GENERATION_STARTED, reply_markup=get_cancel_keyboard())
        await message.answer(IN_QUEUE)
    except Exception as e:
        logging.error(f"Generation error: {str(e)}")
        await message.answer(GENERATION_FAILED)
        await state.clear()

async def handle_generation_result(result: dict, message: Message, state: FSMContext):
    """Обработка результата генерации"""
    if result.get("status") == "SUCCESS":
        for image_url in result.get("output_urls", []):
            await message.answer_photo(
                URLInputFile(image_url),
                caption=PROCESSING_COMPLETE,
                reply_markup=get_result_keyboard()
            )
    else:
        await message.answer(PROCESSING_FAILED)
    
    await state.clear()

@router.callback_query(F.data == "cancel")
async def cancel_generation(callback: CallbackQuery, state: FSMContext):
    """Отмена генерации"""
    data = await state.get_data()
    task_id = data.get("task_id")
    
    if task_id:
        await integration_service.cancel_task(task_id)
    
    await state.clear()
    await callback.message.answer("Генерация отменена", reply_markup=get_main_menu_keyboard())
    await callback.answer()

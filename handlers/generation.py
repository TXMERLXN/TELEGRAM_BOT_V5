import asyncio
import logging
import os
from typing import Optional, Union

from uuid import uuid4
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, CallbackQuery, URLInputFile
from aiogram.fsm.state import State, StatesGroup

from config import config
from services.account_manager import account_manager
from services.runninghub import RunningHubAPI
from services.task_queue import task_queue
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_result_keyboard, get_cancel_keyboard
from messages import (
    GENERATION_STARTED,
    GENERATION_FAILED,
    SEND_PRODUCT_PHOTO,
    SEND_BACKGROUND_PHOTO,
    PROCESSING_STARTED,
    PROCESSING_COMPLETE,
    PROCESSING_FAILED,
    SEND_BACKGROUND_PHOTO,
    IN_QUEUE,
    GENERATION_STARTED,
)
from states.generation import GenerationState
from handlers.generation import GenerationStates, process_product_photo, process_background_photo, cancel_generation, regenerate_image
from keyboards import Keyboards

router = Router()

class GenerationStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_background = State()
    processing = State()

@router.message(Command("generate"))
@router.callback_query(F.data == "generate")
async def start_generation(event: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()
    await state.set_state(GenerationStates.waiting_for_product)
    if isinstance(event, CallbackQuery):
        await event.message.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(SEND_PRODUCT_PHOTO, reply_markup=get_cancel_keyboard())

@router.message(F.photo, GenerationStates.waiting_for_product)
async def process_product_photo(message: Message, state: FSMContext, bot: Bot):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_data = await bot.download_file(file.file_path)

    await state.update_data(
        product_photo_data=photo_data,
        product_photo_id=photo.file_id
    )
    await state.set_state(GenerationStates.waiting_for_background)
    await message.answer(SEND_BACKGROUND_PHOTO, reply_markup=get_cancel_keyboard())

@router.message(F.photo, GenerationStates.waiting_for_background)
async def process_background_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    product_photo_data = data.get("product_photo_data")

    background_photo = message.photo[-1]
    background_file = await bot.get_file(background_photo.file_id)
    background_data = await bot.download_file(background_file.file_path)

    # Получаем свободный аккаунт
    account = account_manager.get_free_account()
    if not account:
        await message.answer(GENERATION_FAILED)
        await state.clear()
        return

    # Создаем клиент RunningHub
    client = RunningHubAPI()

    try:
        # Загружаем изображения
        product_filename = await client.upload_image(account.api_key, product_photo_data)
        background_filename = await client.upload_image(account.api_key, background_data)

        if not product_filename or not background_filename:
            await message.answer(GENERATION_FAILED)
            await state.clear()
            return

        # Создаем задачу
        task_status = await client.create_task(
            account.api_key,
            account.workflow_id,
            product_filename,
            background_filename
        )
        
        if task_status == "QUEUED":
            await message.answer(IN_QUEUE)
            return
            
        if not task_status:
            await message.answer(GENERATION_FAILED)
            await state.clear()
            return

        # Добавляем задачу в очередь
        await task_queue.add_task(
            task_id=task_status,
            user_id=message.from_user.id,
            account=account,
            client=client
        )

        await message.answer(GENERATION_STARTED, reply_markup=get_cancel_keyboard())

        # Запускаем мониторинг задачи
        asyncio.create_task(monitor_task(message, task_status, state, client))

    except Exception as e:
        logging.error(f"Error during generation: {str(e)}", exc_info=True)
        await message.answer(GENERATION_FAILED)
        await state.clear()

async def monitor_task(message: Message, task_id: str, state: FSMContext, client: RunningHubAPI):
    account = task_queue.get_account_for_task(task_id)
    if not account:
        await message.answer(PROCESSING_FAILED)
        await state.clear()
        return

    start_time = asyncio.get_event_loop().time()
    timeout = 300  # 5 minutes timeout
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            result = await client.get_task_outputs(account.api_key, task_id)
            
            if result.code == 0:  # Success
                if result.data:
                    for output in result.data:
                        if output.fileType == "image":
                            await message.answer_photo(
                                URLInputFile(output.fileUrl),
                                caption=PROCESSING_COMPLETE,
                                reply_markup=get_result_keyboard()
                            )
                    break
                else:
                    await message.answer(PROCESSING_FAILED)
                    break

            elif result.code in [804, 805]:  # Task is running or queued
                await asyncio.sleep(5)
                continue

            else:  # Other error codes
                await message.answer(PROCESSING_FAILED)
                break

        except Exception as e:
            logging.error(f"Error monitoring task {task_id}: {str(e)}", exc_info=True)
            await message.answer(PROCESSING_FAILED)
            break

    # Если вышли по таймауту
    if asyncio.get_event_loop().time() - start_time >= timeout:
        await message.answer(PROCESSING_FAILED)
        logging.warning(f"Task {task_id} timed out after {timeout} seconds")
        
    await state.clear()
    task_queue.remove_task(task_id)
    account_manager.release_account(account)

@router.callback_query(F.data == "cancel")
async def cancel_generation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    if task_id:
        task_queue.remove_task(task_id)

    await state.clear()
    await callback.message.answer("Генерация отменена", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "regenerate")
async def regenerate_image(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("product_photo_data") or not data.get("background_photo_data"):
        await callback.message.answer(
            "Для повторной генерации отправьте изображения заново",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
        return

    await process_background_photo(callback.message, state, callback.bot)
    await callback.answer()
    await callback.message.answer(IN_QUEUE)
    await callback.answer()

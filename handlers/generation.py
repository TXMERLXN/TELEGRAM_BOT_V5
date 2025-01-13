from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, URLInputFile
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
    GENERATION_CANCELLED,
    GENERATION_QUEUED
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
    # Отправляем обычное сообщение вместо анимации
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
    # Отправляем сообщение с анимацией
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
    
    try:
        # Запускаем генерацию
        result_url = await runninghub.generate_product_photo(
            message.from_user.id,
            product_image,
            message.photo[-1].file_id
        )
        
        if not result_url:
            raise Exception("Failed to generate image")
            
        # Отправляем результат
        await message.answer_photo(
            URLInputFile(result_url),
            caption=GENERATION_COMPLETE(),
            reply_markup=get_main_menu_keyboard()
        )
        await status_message.delete()
        
    except Exception as e:
        logger.error("Не удалось создать задачу генерации")
        await status_message.edit_text(
            GENERATION_ERROR(),
            reply_markup=get_main_menu_keyboard()
        )
    finally:
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
        
        # Запускаем генерацию и получаем ID задачи
        task_id = await runninghub.generate_product_photo(message.from_user.id, product_image, background_image)
        if not task_id:
            logger.error("Не удалось создать задачу генерации")
            await status_message.edit_text(
                GENERATION_ERROR(),
                reply_markup=get_main_menu_keyboard()
            )
            return None

        # Сохраняем task_id в состоянии
        await state.update_data(task_id=task_id)
        
        # Обновляем сообщение о статусе
        await status_message.edit_text(
            GENERATION_QUEUED(),
            reply_markup=get_cancel_keyboard()
        )
        
        # Ожидаем завершения генерации
        while True:
            status, result_url = await runninghub.get_generation_status(task_id)
            
            if status == "completed" and result_url:
                logger.info("Фото успешно сгенерировано")
                # Отправляем результат с клавиатурой
                await message.answer_photo(
                    result_url,
                    caption=GENERATION_COMPLETE(),
                    reply_markup=get_result_keyboard()
                )
                # Удаляем сообщение о генерации
                await status_message.delete()
                return result_url
            
            elif status == "failed":
                logger.error("Ошибка генерации")
                await status_message.edit_text(
                    GENERATION_ERROR(),
                    reply_markup=get_main_menu_keyboard()
                )
                return None
            
            elif status == "queued":
                # Продолжаем ждать
                pass
            
            elif status == "not_found":
                logger.error("Задача не найдена")
                await status_message.edit_text(
                    GENERATION_ERROR(),
                    reply_markup=get_main_menu_keyboard()
                )
                return None
            
            # Ждем 2 секунды перед следующей проверкой
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        await status_message.edit_text(
            GENERATION_ERROR(),
            reply_markup=get_main_menu_keyboard()
        )
        return None

@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    """
    Обработчик получения фотографий от пользователя
    """
    current_state = await state.get_state()
    
    if current_state is None:
        # Начинаем процесс генерации
        await message.answer("Отлично! Теперь отправьте фотографию желаемого фона")
        await state.set_state(GenerationState.waiting_for_background_image)
        await state.update_data(product_file_id=message.photo[-1].file_id)
        logger.info("Начало генерации фото продукта")
        
    elif current_state == GenerationState.waiting_for_background_image:
        # Получаем file_id сохраненной фотографии продукта
        user_data = await state.get_data()
        product_file_id = user_data.get("product_file_id")
        
        if not product_file_id:
            await message.answer("Произошла ошибка. Пожалуйста, начните сначала")
            await state.clear()
            return
            
        logger.info("Получена фотография фона")
        background_file_id = message.photo[-1].file_id
        
        # Отправляем сообщение о начале генерации
        status_message = await message.answer(
            "Генерирую изображение, это может занять некоторое время...",
            reply_markup=get_cancel_keyboard()
        )
        
        # Начинаем генерацию
        try:
            # Запускаем генерацию в отдельной задаче
            task = asyncio.create_task(
                runninghub.generate_product_photo(
                    message.from_user.id,
                    product_file_id,
                    background_file_id
                )
            )
            generation_tasks[message.from_user.id] = task
            
            result_url = await task
            if not result_url:
                raise Exception("Failed to generate image")
                
            # Отправляем результат
            await message.answer_photo(
                URLInputFile(result_url),
                caption="Готово! Вот ваше изображение",
                reply_markup=get_main_menu_keyboard()
            )
            await status_message.delete()
            
        except asyncio.CancelledError:
            logger.info("Задача генерации отменена пользователем")
            await status_message.edit_text(
                "Генерация отменена",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка генерации: {str(e)}")
            await status_message.edit_text(
                "Произошла ошибка при генерации изображения. Пожалуйста, попробуйте еще раз",
                reply_markup=get_main_menu_keyboard()
            )
        finally:
            # Удаляем задачу из словаря
            generation_tasks.pop(message.from_user.id, None)
            await state.clear()

@router.callback_query(F.data == "back_to_main", GenerationState.waiting_for_product_image)
@router.callback_query(F.data == "back_to_main", GenerationState.waiting_for_background_image)
async def back_to_main_during_upload(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню во время загрузки фотографий"""
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "Генерация отменена. Возвращаемся в главное меню...",
        reply_markup=get_main_menu_keyboard()
    )

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

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from services.runninghub import RunningHubAPI
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_result_keyboard
from messages import GENERATION_STARTED, GENERATION_COMPLETE, GENERATION_ERROR

router = Router()
runninghub = RunningHubAPI()
logger = logging.getLogger(__name__)

class GenerationState(StatesGroup):
    waiting_for_product_image = State()
    waiting_for_background_image = State()

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
    
    # Отправляем сообщение о начале генерации
    status_message = await message.answer(GENERATION_STARTED())
    
    try:
        # Генерируем фото
        result = await runninghub.generate_product_photo(product_image, message.photo[-1].file_id)
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
        else:
            logger.error("Ошибка генерации: результат пустой")
            await status_message.edit_text(
                GENERATION_ERROR(),
                reply_markup=get_main_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        await status_message.edit_text(
            GENERATION_ERROR(),
            reply_markup=get_main_menu_keyboard()
        )
    # Очищаем состояние только после генерации
    await state.clear()

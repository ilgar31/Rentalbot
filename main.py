import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router
from aiogram.filters import Command, StateFilter
import sqlite3


# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Состояния для регистрации
class Registration(StatesGroup):
    phone = State()
    first_name = State()
    last_name = State()
    company = State()
    email = State()




# Инициализация подключения к SQLite
async def create_db():
    conn = sqlite3.connect('users.db')  # Локальная база данных users.db
    cursor = conn.cursor()
    # Создаем таблицу, если её нет
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        chat_id INTEGER,
                        phone_number TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        company TEXT,
                        email TEXT)''')
    conn.commit()
    conn.close()



# Команда /start и начало регистрации
@router.message(Command(commands=['start']))
async def start_command(message: types.Message, state: FSMContext):
    await state.set_state(Registration.phone)
    share_contact_button = KeyboardButton(text="Поделиться контактом", request_contact=True)
    keyboard = ReplyKeyboardMarkup(keyboard=[[share_contact_button]], resize_keyboard=True)
    await message.answer("Шаг 1 из 5. Введите ваш номер телефона или нажмите кнопку ниже:", reply_markup=keyboard)

# Шаг 1: Ввод или получение номера телефона
@router.message(StateFilter(Registration.phone), lambda message: message.content_type in [ContentType.CONTACT, ContentType.TEXT])
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    await state.update_data(phone=phone)
    await state.set_state(Registration.first_name)
    await message.answer("Шаг 2 из 5. Введите ваше имя:", reply_markup=types.ReplyKeyboardRemove())

# Шаг 2: Ввод имени
@router.message(Registration.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await state.set_state(Registration.last_name)
    await message.answer("Шаг 3 из 5. Введите вашу фамилию:")

# Шаг 3: Ввод фамилии
@router.message(Registration.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await state.set_state(Registration.company)
    await message.answer("Шаг 4 из 5. Наименование вашей компании:")

# Шаг 4: Ввод компании
@router.message(Registration.company)
async def process_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    await state.set_state(Registration.email)
    await message.answer("Последний шаг. Укажите ваш email:")

# Шаг 5: Ввод email и завершение регистрации
@router.message(Registration.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    user_data = await state.get_data()


    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (user_id, chat_id, phone_number, first_name, last_name, company, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (message.from_user.id, message.chat.id, user_data['phone'], user_data['first_name'], user_data['last_name'], user_data['company'], user_data['email'])
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("Регистрация завершена! Теперь вам доступно главное меню.", reply_markup=main_menu())

# Главное меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Правила работы", callback_data="rules")
    builder.button(text="Дома в продаже", callback_data="houses_for_sale")
    builder.button(text="Лот недели", callback_data="lot_of_the_week")
    builder.button(text="Проверить на уникальность", url="https://your-website.com/uniqueness")
    builder.button(text="Записать на презентацию", url="https://your-website.com/presentation")
    builder.button(text="Позвонить", callback_data="call_us")
    builder.button(text="Брокер-тур", callback_data="broker_tour")

    builder.adjust(1)

    return builder.as_markup()

# Обработка кнопок в главном меню
@router.callback_query(lambda call: call.data == "rules")
async def show_rules_menu(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Регламент", callback_data="send_pdf_reglament")
    builder.button(text="Правила работы на стартах продаж", callback_data="send_pdf_start_rules")
    builder.button(text="Агентский договор", callback_data="send_pdf_contract")
    builder.button(text="Правила рекламы", callback_data="send_pdf_ad_rules")
    builder.button(text="Документы для партнёрства", callback_data="send_pdf_partnership")
    builder.button(text="Правила фото и видео", callback_data="send_pdf_photo_video_rules")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)

    await call.message.edit_text("ПРАВИЛА РАБОТЫ", reply_markup=builder.as_markup())

# Возвращаем PDF при нажатии кнопок
@router.callback_query(lambda call: call.data.startswith("send_pdf_"))
async def send_pdf(call: types.CallbackQuery):
    pdf_map = {
        "send_pdf_reglament": "reglament.pdf",
        "send_pdf_start_rules": "start_rules.pdf",
        "send_pdf_contract": "contract.pdf",
        "send_pdf_ad_rules": "ad_rules.pdf",
        "send_pdf_partnership": "partnership_docs.pdf",
        "send_pdf_photo_video_rules": "photo_video_rules.pdf"
    }
    pdf_file = pdf_map.get(call.data)
    if pdf_file:
        await call.message.answer_document(types.InputFile(f'./pdfs/{pdf_file}'))

# Обработка остальных команд в меню
@router.callback_query(lambda call: call.data == "houses_for_sale")
async def show_houses_for_sale(call: types.CallbackQuery):
    await call.message.answer("Дома в продаже", reply_markup=main_menu())

@router.callback_query(lambda call: call.data == "lot_of_the_week")
async def show_lot_of_the_week(call: types.CallbackQuery):
    await call.message.answer("Лот недели", reply_markup=main_menu())

@router.callback_query(lambda call: call.data in ["call_us", "broker_tour"])
async def contact_us(call: types.CallbackQuery):
    await call.message.answer("Нажимайте, ждем ваш звонок: +74951044080", reply_markup=main_menu())

# Запуск бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

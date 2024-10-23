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
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import InputFile, BufferedInputFile
import sqlite3
from aiogram.types.input_file import FSInputFile


def get_houses_data():
    # Подключаемся к базе данных
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Выполняем запрос для получения всех данных
    cursor.execute("SELECT name, presentation, video, renders, reference, shorts_video, house_sales, dynamics, choose_apartment, recording_presentation FROM houses")
    rows = cursor.fetchall()

    # Закрываем соединение с базой данных
    conn.close()

    # Преобразуем данные в словарь
    houses = {}
    for row in rows:
        house_name = row[0]
        houses[house_name] = {
            "presentation": row[1],
            "video": row[2],
            "renders": row[3],
            "reference": row[4],
            "shorts_video": row[5],
            "house_sales": row[6],
            "dynamics": row[7],
            "choose_apartment": row[8],
            "recording_presentation": row[9]
        }

    return houses


def add_house(house_name, presentation, video, renders, reference, shorts_video, house_sales, dynamics, choose_apartment, recording_presentation):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Выполняем вставку данных в таблицу
    cursor.execute('''
        INSERT INTO houses (name, presentation, video, renders, reference, shorts_video, house_sales, dynamics, choose_apartment, recording_presentation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (house_name, presentation, video, renders, reference, shorts_video, house_sales, dynamics, choose_apartment, recording_presentation))

    # Сохраняем изменения
    conn.commit()
    conn.close()


def delete_house(house_name):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Удаляем запись, соответствующую имени дома
    cursor.execute('DELETE FROM houses WHERE name = ?', (house_name,))

    # Сохраняем изменения
    conn.commit()
    conn.close()


def update_house(house_name, field, new_value):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Обновляем конкретное поле дома
    query = f'UPDATE houses SET {field} = ? WHERE name = ?'
    cursor.execute(query, (new_value, house_name))

    # Сохраняем изменения
    conn.commit()
    conn.close()


def add_favorite_house(house_name):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Находим id дома по имени
    cursor.execute('SELECT id FROM houses WHERE name = ?', (house_name,))
    house_id = cursor.fetchone()

    if house_id:
        # Вставляем в таблицу избранных домов
        cursor.execute('INSERT INTO favorite_houses (house_id) VALUES (?)', (house_id[0],))
        conn.commit()
    else:
        print(f"Дом с названием '{house_name}' не найден.")

    conn.close()


def remove_favorite_house(house_name):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Находим id дома по имени
    cursor.execute('SELECT id FROM houses WHERE name = ?', (house_name,))
    house_id = cursor.fetchone()

    if house_id:
        # Удаляем дом из таблицы избранных домов
        cursor.execute('DELETE FROM favorite_houses WHERE house_id = ?', (house_id[0],))
        conn.commit()
    else:
        print(f"Дом с названием '{house_name}' не найден.")

    conn.close()


def get_favorite_houses():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Получаем информацию о всех избранных домах
    cursor.execute('''
        SELECT houses.name, houses.presentation, houses.video, houses.renders, houses.reference,
               houses.shorts_video, houses.house_sales, houses.dynamics, houses.choose_apartment, houses.recording_presentation
        FROM houses
        INNER JOIN favorite_houses ON houses.id = favorite_houses.house_id
    ''')

    favorite_houses = cursor.fetchall()
    conn.close()

    # Преобразуем результат в удобный формат словаря
    favorite_houses_dict = {}
    for house in favorite_houses:
        house_name = house[0]
        favorite_houses_dict[house_name] = {
            "presentation": house[1],
            "video": house[2],
            "renders": house[3],
            "reference": house[4],
            "shorts_video": house[5],
            "house_sales": house[6],
            "dynamics": house[7],
            "choose_apartment": house[8],
            "recording_presentation": house[9]
        }

    return favorite_houses_dict


def get_pdf_files():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Получаем все записи из таблицы pdf_files
    cursor.execute('SELECT command, filename FROM pdf_files')
    pdf_files = cursor.fetchall()

    conn.close()

    # Преобразуем результат в словарь
    pdf_map = {row[0]: row[1] for row in pdf_files}
    print(pdf_map)
    return pdf_map


def update_pdf_file(command, new_filename):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Обновляем запись в таблице по команде
    cursor.execute('UPDATE pdf_files SET filename = ? WHERE command = ?', (new_filename, command))

    # Сохраняем изменения
    conn.commit()
    conn.close()


extra_dict = {
    "send_pdf_reglament": "Регламент",
    "send_pdf_contract": "Агентский договор",
    "send_pdf_ad_rules": "Правила рекламы",
    "send_pdf_photo_video_rules": "Правила фото и видео"
}

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

# Сохранение данных пользователя в SQLite
async def save_user_data(user_data, message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Вставка данных
    cursor.execute(
        "INSERT INTO users (user_id, chat_id, phone_number, first_name, last_name, company, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (message.from_user.id, message.chat.id, user_data['phone'], user_data['first_name'], user_data['last_name'], user_data['company'], user_data['email'])
    )
    conn.commit()
    conn.close()



# Инициализация подключения к SQLite
async def check_user(chat_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в базе данных
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user = cursor.fetchone()
    if user:
        return user[3]
    else:
        return False

    conn.close()


# Команда /start и начало регистрации
@router.message(Command(commands=['start']))
async def start_command(message: types.Message, state: FSMContext):
    first_name = await check_user(message.chat.id)
    if not first_name:
        await state.set_state(Registration.phone)
        share_contact_button = KeyboardButton(text="Поделиться контактом", request_contact=True)
        keyboard = ReplyKeyboardMarkup(keyboard=[[share_contact_button]], resize_keyboard=True)
        await message.answer("Шаг 1 из 5. Введите ваш номер телефона или нажмите кнопку ниже:", reply_markup=keyboard)
    else:
        await message.answer(f"Добро пожаловать, {first_name}!", reply_markup=types.ReplyKeyboardRemove())

        
@router.message(StateFilter(Registration.phone), lambda message: message.content_type in [ContentType.CONTACT, ContentType.TEXT])
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    await state.update_data(phone=phone)
    await state.set_state(Registration.first_name)
    await message.answer("Шаг 2 из 5. Введите ваше имя:", reply_markup=types.ReplyKeyboardRemove())

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

    await save_user_data(user_data, message)

    await state.clear()
    await message.answer("Регистрация завершена! Теперь вам доступно главное меню.", reply_markup=main_menu())

# Главное меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Правила работы", callback_data="rules")
    builder.button(text="Дома в продаже", callback_data="houses_for_sale")
    builder.button(text="Лот недели", callback_data="lot_of_the_week")
    builder.button(text="Проверить на уникальность", url="https://tavrida-development.ru/business/partner/uniqueness/")
    builder.button(text="Записать на презентацию", url="https://tavrida-development.ru/business/partner/presentation/")
    builder.button(text="Позвонить", callback_data="call_us")
    builder.button(text="Брокер-тур", callback_data="broker_tour")

    builder.adjust(1)

    return builder.as_markup()

# Возвращаем PDF при нажатии кнопок
@router.callback_query(lambda call: call.data.startswith("send_pdf_"))
async def send_pdf(call: types.CallbackQuery):
    pdf_map = get_pdf_files()
    pdf_file = pdf_map.get(call.data)
    if pdf_file:
        await call.message.answer_document(FSInputFile(pdf_file))


# Возвращаем PDF при нажатии кнопок
@router.callback_query(lambda call: call.data.startswith("presentation@"))
async def send_presentation(call: types.CallbackQuery):
    houses = get_houses_data()
    house = call.data.split('@')[1]
    pdf_file = f"{house}/{houses[house]['presentation']}" 
    if pdf_file:
        file_path = f'./{pdf_file}'
        await call.message.answer_document(FSInputFile(file_path))

@router.callback_query(lambda call: call.data.startswith("house_"))
async def show_house(call: types.CallbackQuery):
    houses = get_houses_data()
    house = call.data.split('_')[1]
    builder = InlineKeyboardBuilder()

    if houses[house]['presentation']:
        builder.row(InlineKeyboardButton(text="Презентация", callback_data=f"presentation@{house}"))
    
    if houses[house]['video']:
        builder.row(InlineKeyboardButton(text="Видео о проекте", url=houses[house]['video']))

    if houses[house]['renders']:
        builder.row(InlineKeyboardButton(text="Рендеры", url=houses[house]['renders']))

    if houses[house]['reference']:
        builder.row(InlineKeyboardButton(text="Эталонные тексты", url=houses[house]['reference']))

    if houses[house]['shorts_video']:
        builder.row(InlineKeyboardButton(text="Видео для stories", url=houses[house]['shorts_video']))

    if houses[house]['house_sales']:
        builder.row(InlineKeyboardButton(text="Дом продаж", url=houses[house]['house_sales']))

    if houses[house]['dynamics']:
        builder.row(InlineKeyboardButton(text="Динамика строительства", url=houses[house]['dynamics']))

    if houses[house]['choose_apartment']:
        builder.row(InlineKeyboardButton(text="Выбрать квартиру", url=houses[house]['choose_apartment']))

    if houses[house]['recording_presentation']:
        builder.row(InlineKeyboardButton(text="Запись на презентацию", url=houses[house]['recording_presentation']))

    builder.row(
        InlineKeyboardButton(text="НАЗАД", callback_data="houses_for_sale"),
        InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu"),
    )
    
    await call.message.answer(f'Информация о проекте {house}', reply_markup=builder.as_markup())



# Обработка команд из меню
@router.message(Command(commands=['rules', 'homes', 'lots', 'call', 'tour', 'shedule', 'check']))
async def handle_commands(message: types.Message):
    if message.text == '/rules':
        await show_rules_menu(message)
    elif message.text == '/homes':
        await show_houses(message)
    elif message.text == '/lots':
        await show_houses(message)
    elif message.text == '/tour':
        await show_broker_tour(message)
    elif message.text == '/call':
        await show_call(message)
    elif message.text == '/shedule' or message.text == '/check':
        await show_check(message)





# Редактирование конкретного дома
@router.callback_query(lambda call: call.data.startswith("edit_house_"))
async def edit_house_command(call: types.CallbackQuery):
    house = call.data.split('_')[2]
    builder = InlineKeyboardBuilder()

    builder.button(text="Изменить Презентацию", callback_data=f"edit@presentation@{house}")
    builder.button(text="Изменить Видео", callback_data=f"editlink@video@{house}")
    builder.button(text="Изменить Рендоры", callback_data=f"editlink@renders@{house}")
    builder.button(text="Изменить Эталонные текста", callback_data=f"editlink@reference@{house}")
    builder.button(text="Изменить Видео для stories", callback_data=f"editlink@shorts_video@{house}")
    builder.button(text="Изменить Дом продаж", callback_data=f"editlink@house_sales@{house}")
    builder.button(text="Изменить Динамику", callback_data=f"editlink@dynamics@{house}")
    builder.button(text="Изменить Выбрать квартиру", callback_data=f"editlink@choose_apartment@{house}")
    builder.button(text="Изменить Запись на презу", callback_data=f"editlink@recording_presentation@{house}")


    builder.button(text="НАЗАД", callback_data="edit_homes")
    builder.adjust(1)

    await call.message.answer(f'Редактирование проекта {house}', reply_markup=builder.as_markup())

# Добавление нового дома
@router.callback_query(lambda call: call.data == "add_house")
async def add_house_command(call: types.CallbackQuery, state: FSMContext):
    await state.set_state("add_house_name")
    await call.message.answer("Введите название нового дома:")

@router.message(StateFilter("add_house_name"))
async def process_add_house_name(message: types.Message, state: FSMContext):
    await state.update_data(house_name=message.text)
    if '/' in message.text or '_' in message.text:
        await state.clear()
        builder = InlineKeyboardBuilder()
        builder.button(text="НАЗАД", callback_data="edit_homes")
        builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
        builder.adjust(1)
        await message.answer(f"Недопустимое название!", reply_markup=builder.as_markup())
    else:
        add_house(message.text, "", "", "",  "", "", "", "", "", "")
        await state.clear()
        builder = InlineKeyboardBuilder()
        builder.button(text="НАЗАД", callback_data="edit_homes")
        builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
        builder.adjust(1)
        await message.answer(f"Новый дом '{message.text}' добавлен!", reply_markup=builder.as_markup())

@router.callback_query(lambda call: call.data == "delete_house")
async def delete_house_command(call: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    houses = get_houses_data()
    for house in houses:
        builder.button(text=f"Удалить {house}", callback_data=f"confirm_delete_{house}")
    
    builder.button(text="НАЗАД", callback_data="edit_homes")
    builder.adjust(1)
    
    await call.message.answer('Выберите дом для удаления:', reply_markup=builder.as_markup())

@router.callback_query(lambda call: call.data.startswith("confirm_delete_"))
async def confirm_delete_house(call: types.CallbackQuery):
    house = call.data.split('_')[2]
    delete_house(house)
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_homes")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)
    await call.message.answer(f"Дом {house} удален!", reply_markup=builder.as_markup())


@router.callback_query(lambda call: call.data == "delete_lot")
async def delete_lot_command(call: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    lots = get_favorite_houses()
    for house in lots:
        builder.button(text=f"Удалить {house} из лота", callback_data=f"confirm_lot_delete_{house}")
    
    builder.button(text="НАЗАД", callback_data="edit_lots")
    builder.adjust(1)
    
    await call.message.answer('Выберите лот для удаления:', reply_markup=builder.as_markup())

@router.callback_query(lambda call: call.data.startswith("confirm_lot_delete_"))
async def confirm_delete_lot(call: types.CallbackQuery):
    house = call.data.split('_')[3]
    lots = get_favorite_houses()
    del lots[house]
    remove_favorite_house(house)
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_lots")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)
    await call.message.answer(f"Дом {house} удален из лота недели!", reply_markup=builder.as_markup())


@router.callback_query(lambda call: call.data == "add_lot")
async def add_lot_command(call: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    lots = get_favorite_houses()
    houses = get_houses_data()
    flag = False
    for house in houses:
        if house not in lots:
            flag = True
            builder.button(text=f"Добавить {house} в лоты", callback_data=f"confirm_add_lot_{house}")
    
    builder.button(text="НАЗАД", callback_data="edit_lots")
    builder.adjust(1)
    
    if flag:
        await call.message.answer('Выберите лот для добавления:', reply_markup=builder.as_markup())
    else:
        await call.message.answer('Все дома доступные в продаже уже добавлены в "Лоты недели"', reply_markup=builder.as_markup())

@router.callback_query(lambda call: call.data.startswith("confirm_add_lot_"))
async def confirm_add_lot(call: types.CallbackQuery):
    house = call.data.split('_')[3]
    add_favorite_house(house)
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_lots")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)
    await call.message.answer(f"Дом {house} добавлен в лоты!", reply_markup=builder.as_markup())


# Обработка нажатия на кнопку для редактирования презентации
@router.callback_query(lambda call: call.data.startswith("edit@presentation@"))
async def edit_presentation(call: types.CallbackQuery, state: FSMContext):
    house = call.data.split('@')[2]
    await state.update_data(house=house)
    await call.message.answer(f"Отправьте новый файл для презентации для {house}.")
    await state.set_state("waiting_for_presentation_file")

# Обработка отправки нового файла презентации
@router.message(StateFilter("waiting_for_presentation_file"))
async def process_presentation_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    house = data.get("house")
    document = message.document
    
    file_name = f"{document.file_name}"
    file_path = f"./{house}/{file_name}"
    if not os.path.exists(house):
        os.makedirs(house)
    await bot.download(document, destination=file_path)
    houses = get_houses_data()
    houses[house]["presentation"] = file_name
    update_house(house, "presentation", file_name)
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_homes")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)

    await message.answer(f"Презентация для {house} обновлена.", reply_markup=builder.as_markup())


# Обработка нажатия на кнопку для редактирования презентации
@router.callback_query(lambda call: call.data.startswith("edit@rule@"))
async def edit_rule_file(call: types.CallbackQuery, state: FSMContext):
    rule = call.data.split('@')[2]
    await state.update_data(rule=rule)
    await call.message.answer(f"Отправьте новый файл для {extra_dict[rule]}.")
    await state.set_state("waiting_for_rule_file")

# Обработка отправки нового файла презентации
@router.message(StateFilter("waiting_for_rule_file"))
async def process_rule_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    rule = data.get("rule")
    document = message.document
    
    file_name = f"{document.file_name}"
    file_path = f"./rules/{file_name}"

    await bot.download(document, destination=file_path)
    update_pdf_file(rule, file_path)
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_rules")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)

    await message.answer(f"Документ для {extra_dict[rule]} обновлен.", reply_markup=builder.as_markup())



@router.callback_query(lambda call: call.data.startswith("editlink@"))
async def edit_link(call: types.CallbackQuery, state: FSMContext):
    arg = call.data.split('@')[1]
    house = call.data.split('@')[2]
    await state.update_data(house=house)
    await state.update_data(arg=arg)
    await call.message.answer(f"Отправьте новую ссылку.")
    await state.set_state("waiting_for_link")


@router.message(StateFilter("waiting_for_link"))
async def process_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    house = data.get("house")
    arg = data.get("arg")
    new_link = message.text

    houses = get_houses_data()

    houses[house][arg] = new_link
    update_house(house, arg, new_link)
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="НАЗАД", callback_data="edit_homes")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    builder.adjust(1)

    await message.answer(f"Данные для {house} обновлены.", reply_markup=builder.as_markup())




# Обработка нажатий на кнопки в главном меню
@router.callback_query()
async def handle_callback_query(call: CallbackQuery):
    if call.data == "rules":
        await show_rules_menu(call.message)
    elif call.data == "houses_for_sale":
        await show_houses(call.message)
    elif call.data == "lot_of_the_week":
        await show_lots(call.message)
    elif call.data == "call_us":
        await show_call(call.message)
    elif call.data == "broker_tour":
        await show_broker_tour(call.message)
    elif call.data =='edit_homes':
        await edit_homes_command(call.message)
    elif call.data =='edit_lots':
        await edit_lots_command(call.message)
    elif call.data =='edit_rules':
        await edit_rules_command(call.message)
        
    elif call.data == "main_menu":  # Добавляем обработку для кнопки "ГЛАВНОЕ МЕНЮ"
        await call.message.answer("ГЛАВНОЕ МЕНЮ", reply_markup=main_menu())


# Показ Запись на презентацию
async def show_check(message: types.Message):
    builder = InlineKeyboardBuilder()

    builder.button(text="Проверить на уникальность", url="https://tavrida-development.ru/business/partner/uniqueness/")
    builder.button(text="Записать на презентацию", url="https://tavrida-development.ru/business/partner/presentation/")

    builder.adjust(1)

    await message.answer("Проверьте на уникальность и запишите клиента на презентацию", reply_markup=builder.as_markup())

# Показ Дома в продаже
async def show_houses(message: types.Message):
    builder = InlineKeyboardBuilder()
    houses = get_houses_data()
    for house in houses:
        builder.button(text=house, callback_data=f"house_{house}")


    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)

    await message.answer('🏠 ДОМА В ПРОДАЖЕ', reply_markup=builder.as_markup())

async def show_lots(message: types.Message):
    builder = InlineKeyboardBuilder()
    lots = get_favorite_houses()
    for house in lots:
        builder.button(text=house, callback_data=f"house_{house}")


    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)
    
    if lots:
        await message.answer('💫 ЛОТ НЕДЕЛИ', reply_markup=builder.as_markup())
    else:
        await message.answer('💫 ЛОТ НЕДЕЛИ ОТСУТСТВУЕТ', reply_markup=builder.as_markup())

# Показ Брокер-тура
async def show_broker_tour(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)

    await message.answer('Запись на брокер-тур — https://tavrida-development.ru/business/partner/tour/\nНажимайте, ждем ваш звонок: +74994330801', reply_markup=builder.as_markup())


# Показ Позвонить
async def show_call(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)

    await message.answer('Нажимайте, ждем ваш звонок: +74994330801', reply_markup=builder.as_markup())

# Показ правил
async def show_rules_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Регламент", callback_data="send_pdf_reglament")
    builder.button(text="Агентский договор", callback_data="send_pdf_contract")
    builder.button(text="Правила рекламы", callback_data="send_pdf_ad_rules")
    builder.button(text="Правила фото и видео", callback_data="send_pdf_photo_video_rules")
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)

    await message.answer("ПРАВИЛА РАБОТЫ", reply_markup=builder.as_markup())




@router.message(Command(commands=['edit_homes']))
async def edit_homes_command(message: types.Message):
    builder = InlineKeyboardBuilder()

    houses = get_houses_data()
    
    for house in houses:
        builder.button(text=f"Редактировать {house}", callback_data=f"edit_house_{house}")
    
    builder.button(text="Добавить новый дом", callback_data="add_house")
    builder.button(text="Удалить существующий дом", callback_data="delete_house")
    
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)
    await message.answer('Редактирование домов', reply_markup=builder.as_markup())


@router.message(Command(commands=['edit_lots']))
async def edit_lots_command(message: types.Message):
    builder = InlineKeyboardBuilder()
            
    builder.button(text="Добавить новый лот", callback_data="add_lot")
    builder.button(text="Удалить существующий лот", callback_data="delete_lot")
    
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)
    await message.answer('Редактирование лота недели', reply_markup=builder.as_markup())


@router.message(Command(commands=['edit_rules']))
async def edit_rules_command(message: types.Message):
    builder = InlineKeyboardBuilder()

    rules = get_pdf_files() 
    
    for rule in rules:        
        builder.button(text=f"Редактировать {extra_dict[rule]}", callback_data=f"edit@rule@{rule}")
    
    builder.button(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    builder.adjust(1)
    await message.answer('Редактирование Правила работы', reply_markup=builder.as_markup())


@router.message(Command(commands=['give_array']))
async def get_array(message: types.Message):
    houses = get_houses_data()
    await message.answer(str(houses))


# Запуск бота
async def main():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Создаем таблицу избранных домов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS favorite_houses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        FOREIGN KEY (house_id) REFERENCES houses (id) ON DELETE CASCADE
    )
    ''')

    # Сохраняем изменения
    conn.commit()
    conn.close()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

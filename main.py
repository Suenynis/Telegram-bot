import asyncio
import time
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types, executor
import os

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from app import keyboards as kb
from app import database as db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from app.database import cur

# main.py - Main application

import asyncio
from config import config

async def check_config_changes():
    while True:
        await asyncio.sleep(300)  # Check for changes every 5 minutes
        # Implement logic to check for changes in the .env file or config file
        # If changes are detected, update the configuration using config.update_config()



class MyState(StatesGroup):
    waiting_for_course = State()
    waiting_for_course_id = State()
    waiting_for_student = State()
    waiting_for_student_id = State()
    waiting_for_stream = State()
    waiting_for_stream_id = State()
    waiting_for_message = State()
    waiting_for_confirmation = State()
    waiting_for_admin_id = State()
    update_for_course_id = State()


day_mapping = {
    "ПН": 0,
    "ВТ": 1,
    "СР": 2,
    "ЧТ": 3,
    "ПТ": 4,
    "СБ": 5,
    "ВС": 6
}
load_dotenv()
bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher(bot=bot, storage=MemoryStorage())

def get_course_names():
    cur.execute("SELECT id, name FROM course")
    result = cur.fetchall()
    return result  # Returns a list of (course_id, course_name) tuples

# Function to fetch stream numbers and names based on the selected course
def get_streams_for_course(course_id):
    cur.execute("SELECT name FROM stream WHERE course_id=? ORDER BY name", (course_id,))
    result = cur.fetchall()
    return result  # Returns a list of (stream_id, stream_name) tuples

# is it admin function
def is_admin(user_id):
    #os.getenv('ADMIN_ID') gives in format admin1id, admin2id, admin3id
    admins = os.getenv('ADMIN_ID').split(', ')
    if str(user_id) in admins:
        return True
    else:
        return False


async def on_startup(_):
    await db.db_start()
    print("Бот запущен")
    asyncio.create_task(check_config_changes())

    # Schedule the send_messages_to_accounts function to run every 60 seconds
    asyncio.create_task(periodic_send_messages())

async def periodic_send_messages():
    while True:
        await send_messages_to_accounts()
        await asyncio.sleep(60)



@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await db.cmd_start_db(message.from_user.id, message.from_user.first_name)
    await message.answer(f"Привет {message.from_user.first_name}!\nДобро пожаловать в Nimbl Academy. Это бот для учеников ", reply_markup=kb.main)
    courses = get_course_names()
    course_list = InlineKeyboardMarkup(row_width=1)
    for course_id, course_name in courses:
        course_list.add(InlineKeyboardButton(text=course_name, callback_data=f'course_{course_id}_{course_name}'))
    if is_admin(message.from_user.id):
        await message.answer('Вы авторилизовались как админ', reply_markup=kb.main_admin)
        await db.cmd_start_db(message.from_user.id, message.from_user.first_name)
        await message.answer("Выберите на каком направлении обучаетесь",
                             reply_markup=course_list)
    else:
        await message.answer("Выберите на каком направлении обучаетесь",
                             reply_markup=course_list)

'''-----------------------------------------------------------------------------------------------------------'''
@dp.message_handler(text='Admin-panel')
async def profile(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer('Вы вошли в админ панель', reply_markup=kb.admin_panel)
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text='Студенты')
async def profile(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer('Студенты', reply_markup=kb.student_list)
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text=['Список Студентов'])
async def show_all_courses(message: types.Message):
    if is_admin(message.from_user.id):
        try:
            cur.execute("""
                SELECT
                    accounts.id,
                    accounts.tg_id,
                    accounts.name,
                    course.name AS course_name,
                    accounts.stream
                FROM
                    accounts
                LEFT JOIN
                    course ON accounts.course_id = course.id
                """)
            students = cur.fetchall()

            if not students:
                await message.answer('Нет активных студентов.')
            else:
                response = 'Список активных студентов:\n'
                response += "{:<5} {:<15} {:<20} {:<20} {:<10}\n".format("ID", "tg_id", "Имя", "Курс", "Поток")
                for student in students:
                    ID, tg_id, name, course_name, stream = student
                    response += "{:<5} {:<15} {:<20} {:<20} {:<10}\n".format(ID, tg_id, name, course_name, stream)

                await message.answer(response)

        except Exception as e:
            await message.answer(f'Произошла ошибка: {str(e)}')
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text=['Удалить студента'])
async def delete_student(message: types.Message):
    # Check if the user is an admin (you can use your own admin check logic)
    if is_admin(message.from_user.id):
        await message.answer("Введите ID студента, которого вы хотите удалить.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for student ID
        await MyState.waiting_for_student_id.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

# Create a handler for receiving student ID to deletу
@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_student_id)
async def process_student_id(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили удаление студента :(")
            await state.finish()
            return
        student_id = int(message.text)

        # Check if the student with the specified ID exists
        cur.execute("SELECT id FROM accounts WHERE id=?", (student_id,))
        existing_student = cur.fetchone()

        if not existing_student:
            await message.answer("Студент с указанным ID не найден.")
        else:
            # Delete the student from the database
            cur.execute("DELETE FROM accounts WHERE id=?", (student_id,))
            db.db.commit()
            await message.answer(f"Студент с ID {student_id} успешно удален из базы данных.")
    except ValueError:
        await message.answer("Введите корректный ID студента.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()


@dp.message_handler(text=['Назад_'])
async def Back(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer('back', reply_markup=kb.admin_panel)
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')



@dp.message_handler(text='Курсы')
async def profile(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer('Курсы', reply_markup=kb.course_func)
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text=['Все курсы'])
async def show_all_courses(message: types.Message):
    if is_admin(message.from_user.id):
        try:
            cur.execute("SELECT id , name, description FROM course")
            courses = cur.fetchall()

            if not courses:
                await message.answer('Нет доступных курсов.')
            else:
                response = 'Список доступных курсов:\n'
                response += "{:<5} {:<30} {:<50}\n".format("ID", "Название", "Описание")
                for course in courses:
                    course_id, name, description = course
                    response += "{:<5} {:<30} {:<50}\n".format(course_id, name, description)

                await message.answer(response)

        except Exception as e:
            await message.answer(f'Произошла ошибка: {str(e)}')
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text=['Добавить курс'])
async def create_course(message: types.Message):
    # Check if the user is an admin (you can use your own admin check logic)
    if is_admin(message.from_user.id):
        await message.answer("Введите данные для нового курса в формате:\nНазвание, Описание\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for course details
        await MyState.waiting_for_course.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_course)
async def process_course_input(message: types.Message, state: FSMContext):
    try:
        # Parse the user's input for course details
        if message.text == 'stop':
            await message.answer("Вы отменили создание курса :(")
            await state.finish()
            return

        course_data = message.text.split(', ')
        if len(course_data) != 2:
            await message.answer("Пожалуйста, введите данные в правильном формате: Название, Описание")
            return

        name, description = course_data

        # Insert the course data into the database
        cur.execute("INSERT INTO course (name, description) VALUES (?, ?)",
                    (name, description))
        db.db.commit()

        await message.answer(f"Курс '{name}' успешно добавлен в базу данных.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()


@dp.message_handler(text=['Изменить курс'])
async def update_course(message: types.Message):
    # Check if the user is an admin (you can use your own admin check logic)
    if is_admin(message.from_user.id):
        await message.answer("Введите ID курса, который вы хотите изменить.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for course ID
        await MyState.update_for_course_id.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

# Create a handler for receiving course ID to update
@dp.message_handler(lambda message: message.text, state=MyState.update_for_course_id)
async def process_course_id(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили создание курса :(")
            await state.finish()
            return
        course_id = int(message.text)

        # Check if the course with the specified ID exists
        cur.execute("SELECT id FROM course WHERE id=?", (course_id,))
        existing_course = cur.fetchone()

        if not existing_course:
            await message.answer("Курс с указанным ID не найден.")
        else:
            # Here we take information course from database
            cur.execute("SELECT name, description FROM course WHERE id=?", (course_id,))
            course = cur.fetchone()
            name, description = course
            await message.answer(f"Данные для изменение:\n {name}, {description}\n\nЕсли хотите отменить оперцию, введите 'stop'.")
            await MyState.update_for_course_id.set()
            await state.update_data(course_id=course_id)
    except ValueError:
        await message.answer("Введите корректный ID курса.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()


@dp.message_handler(lambda message: message.text and message.text != 'stop', state=MyState.update_for_course_id)
async def process_course_input(message: types.Message, state: FSMContext):
    try:
        # Parse the user's input for course details
        if message.text == 'stop':
            await message.answer("Вы отменили создание курса :(")
            await state.finish()
            return

        course_data = message.text.split(', ')
        if len(course_data) != 2:
            await message.answer("Пожалуйста, введите данные в правильном формате: Название, Описание")
            return

        name, description = course_data

        # Insert the course data into the database
        cur.execute("UPDATE course SET name=?, description=? WHERE id=?",
                    (name, description, state['course_id']))
        db.db.commit()

        await message.answer(f"Курс '{name}' успешно изменен в базе данных.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()


@dp.message_handler(text=['Удалить курс'])
async def delete_course(message: types.Message):
    # Check if the user is an admin (you can use your own admin check logic)
    if is_admin(message.from_user.id):
        await message.answer("Введите ID курса, который вы хотите удалить.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for course ID
        await MyState.waiting_for_course_id.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

# Create a handler for receiving course ID to deletу
@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_course_id)
async def process_course_id(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили создание курса :(")
            await state.finish()
            return
        course_id = int(message.text)

        # Check if the course with the specified ID exists
        cur.execute("SELECT id FROM course WHERE id=?", (course_id,))
        existing_course = cur.fetchone()


        if not existing_course:
            await message.answer("Курс с указанным ID не найден.")
        else:
            # Delete the course from the database
            cur.execute("DELETE FROM course WHERE id=?", (course_id,))
            db.db.commit()
            await message.answer(f"Курс с ID {course_id} успешно удален из базы данных.")
    except ValueError:
        await message.answer("Введите корректный ID курса.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()


@dp.message_handler(text=['Все расписания'])
async def show_all_schedules(message: types.Message):
    if is_admin(message.from_user.id):
        try:
            cur.execute("""
                SELECT
                    stream.name AS stream_name,
                    course.name AS course_name,
                    stream.days,
                    stream.hours || ':' || stream.minutes AS time
                FROM
                    stream
                JOIN
                    course ON stream.course_id = course.id
                """)

            schedule = cur.fetchall()

            if not schedule:
                await message.answer('Нет доступного расписания.')
            else:
                response = 'Список всех расписаний:\n'
                response += "{:<10} {:<30} {:<20} {:<10}\n".format("Поток", "Курс", "Дни", "Время")
                for entry in schedule:
                    stream_name, course_name, days, time = entry
                    if time.endswith(':0'):
                        response += "{:<10} {:<30} {:<20} {:<10}\n".format(stream_name, course_name, days, time+'0')
                    else:
                        response += "{:<10} {:<30} {:<20} {:<10}\n".format(stream_name, course_name, days, time)
                await message.answer(response)

        except Exception as e:
            await message.answer(f'Произошла ошибка: {str(e)}')
    else:
        await message.answer('У вас нет доступа к этой команде.')


@dp.message_handler(text='Потоки')
async def profile(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer('Потоки', reply_markup=kb.stream_func)
    else:
        await message.answer('Я тебя не понимаю. Напиши /start')

@dp.message_handler(text=['Все потоки'])
async def show_all_streams(message: types.Message):
    if is_admin(message.from_user.id):
            try:
                cur.execute("""
                    SELECT
                        stream.id,
                        stream.name AS stream_name,
                        course.name AS course_name,
                        stream.days,
                        stream.hours || ':' || stream.minutes AS time
                    FROM
                        stream
                    JOIN
                        course ON stream.course_id = course.id
                    ORDER BY stream.name 
                    """)

                streams = cur.fetchall()

                if not streams:
                    await message.answer('Нет доступных потоков.')
                else:
                    response = 'Список всех потоков:\n'
                    response += "{:<5} {:<10} {:<30} {:<20} {:<10}\n".format("ID", "Поток", "Курс", "Дни", "Время")
                    for entry in streams:
                        stream_id, stream_name, course_name, days, time = entry
                        if time.endswith(':0'):
                            response += "{:<5} {:<10} {:<30} {:<20} {:<10}\n".format(stream_id, stream_name, course_name, days, time+'0')
                        else:
                            response += "{:<5} {:<10} {:<30} {:<20} {:<10}\n".format(stream_id, stream_name, course_name, days, time)
                    await message.answer(response)

            except Exception as e:
                await message.answer(f'Произошла ошибка: {str(e)}')
    else:
        await message.answer('У вас нет доступа к этой команде.')

@dp.message_handler(text=['Добавить поток'])
async def create_stream(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("Введите данные для нового потока в формате:\nНомер потока, ID курса, Дни (ПН ВТ СР), Час, Минут\n"
                             "\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for stream details
        await MyState.waiting_for_stream.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_stream)
async def process_stream_input(message: types.Message, state: FSMContext):
    try:
        # Parse the user's input for stream details
        if message.text == 'stop':
            await message.answer("Вы отменили создание потока :(")
            await state.finish()
            return

        stream_data = message.text.split(', ')
        if len(stream_data) != 5:
            await message.answer("Пожалуйста, введите данные в правильном формате: Номер потока, ID курса, Дни (ПН СР ПТ), Час, Минут")
            return
        name, course_id, days_input, hours, minutes = stream_data
        courses_ids = get_course_names()
        courses_ids = [course_id[0] for course_id in courses_ids]
        if not course_id.isdigit() or int(course_id) not in courses_ids:
            await message.answer("Пожалуйста, введите корректный ID курса.")
            return

        if not hours.isdigit() or not minutes.isdigit():
            await message.answer("Пожалуйста, введите корректное время.")
            return


        # Extract days within parentheses and remove spaces
        days = [day.strip() for day in days_input.strip('()').split()]
        if not all([day in day_mapping for day in days]):
            await message.answer("Пожалуйста, введите корректные дни в правильном формате: ПН ВТ СР")
            return

        # Insert the stream data into the database
        cur.execute("INSERT INTO stream (name, course_id, days, hours, minutes) VALUES (?, ?, ?, ?, ?)",
                    (name, course_id, ', '.join(days), hours, minutes))
        print("INSERT INTO stream (name, course_id, days, hours, minutes) VALUES (?, ?, ?, ?, ?)",
                    (name, course_id, ', '.join(days), hours, minutes))
        db.db.commit()

        await message.answer(f"Поток '{name}' успешно добавлен в базу данных.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()

@dp.message_handler(text=['Удалить поток'])
async def delete_stream(message: types.Message):
# Check if the user is an admin (you can use your own admin check logic)
    if is_admin(message.from_user.id):
        await message.answer("Введите ID потока, который вы хотите удалить.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for stream ID
        await MyState.waiting_for_stream_id.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

# Create a handler for receiving stream ID to deletу
@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_stream_id)
async def process_stream_id(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили создание потока :(")
            await state.finish()
            return
        stream_id = int(message.text)

        # Check if the stream with the specified ID exists
        cur.execute("SELECT id FROM stream WHERE id=?", (stream_id,))
        existing_stream = cur.fetchone()

        if not existing_stream:
            await message.answer("Поток с указанным ID не найден.")
        else:
            # Delete the stream from the database
            cur.execute("DELETE FROM stream WHERE id=?", (stream_id,))
            db.db.commit()
            await message.answer(f"Поток с ID {stream_id} успешно удален из базы данных.")
    except ValueError:
        await message.answer("Введите корректный ID потока.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()

@dp.message_handler(text=['Рассылка для всех'])
async def send_message_to_all(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("Введите сообщение для рассылки.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for message
        await MyState.waiting_for_message.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили рассылку :(")
            await state.finish()
            return

        # Store the message in the state
        async with state.proxy() as data:
            data['message'] = message.text

        # Ask for confirmation
        await message.answer("Вот в таком виде будет выглядеть ваше сообщение. Если вы хотите изменить сообщение, введите 'stop' и попробуйте еще раз.")
        await message.answer(message.text)
        await message.answer("Для подтверждения рассылки, введите 'да'. Для отмены, введите 'отмена'.")
        # Set the state to wait for confirmation
        await MyState.waiting_for_confirmation.set()
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')


@dp.message_handler(lambda message: message.text.lower(), state=MyState.waiting_for_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text == 'да':
        async with state.proxy() as data:
            message_text = data['message']

        # Get all the active accounts
        cur.execute("SELECT tg_id FROM accounts")
        accounts = cur.fetchall()

        if not accounts:
            await message.answer("Нет активных аккаунтов.")
        else:
            # Send a message to each account
            for account in accounts:
                await bot.send_message(account[0], message_text)
            await message.answer(f"Сообщение успешно отправлено {len(accounts)} аккаунтам.")
    elif message.text == 'отмена':
        await message.answer("Вы отменили рассылку :(")

    # Reset the state to none
    await state.finish()

#Добавить админа по ID
@dp.message_handler(text=['Добавить админа'])
async def add_admin(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("Введите ID пользователя, которого вы хотите сделать админом.\nЕсли хотите отменить оперцию, введите 'stop'.")
        # Set the state to wait for student ID
        await MyState.waiting_for_admin_id.set()
    else:
        await message.answer('У вас нет доступа к этой команде.')

# Create a handler for receiving student ID to deletу
def add_admin_id(admin_id):
    # Read the existing ADMIN_IDS variable from the .env file
    with open('.env', 'r') as env_file:
        lines = env_file.readlines()

    updated_lines = []
    for line in lines:
        if line.startswith('ADMIN_ID='):
            # Extract the existing admin IDs
            existing_ids = line.strip().split('=')[1]
            existing_ids_list = [id.strip() for id in existing_ids.split(',')]

            # Append the new admin ID (if it's not already present)
            if admin_id not in existing_ids_list:
                existing_ids_list.append(admin_id)

            # Join the updated admin IDs and update the line
            updated_ids = ', '.join(existing_ids_list)
            updated_line = f'ADMIN_ID={updated_ids}\n'
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    # Write the updated lines back to the .env file
    with open('.env', 'w') as env_file:
        env_file.writelines(updated_lines)

# Create a handler for receiving student ID to deletу
@dp.message_handler(lambda message: message.text, state=MyState.waiting_for_admin_id)
async def process_student_id(message: types.Message, state: FSMContext):
    try:
        if message.text == 'stop':
            await message.answer("Вы отменили добавление админа :(")
            await state.finish()
            return
        student_id = int(message.text)

        add_admin_id(str(student_id))
        await message.answer(f"Пользователь с ID {student_id} успешно добавлен в админы.")
    except ValueError:
        await message.answer("Введите корректный ID студента.")
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')

    # Reset the state to none
    await state.finish()




'''-----------------------------------------------------------------------------------------------------------'''


@dp.message_handler(commands=['id'])
async def cmd_id(message: types.Message):
    await message.answer(message.from_user.id)

@dp.message_handler(lambda message: message.text == 'О нас')
async def cmd_about(message: types.Message):
    await message.answer('Nimbl Academy- первая в СНГ обучающая платформа Web 3 разработке. \n \n   На данный момент мы обучаем специалистов на профессии интегратор Искусственного Интеллекта и Блокчейн разработчика.', reply_markup= kb.aboutus_link)

@dp.message_handler(lambda message: message.text == 'Мой курс')
async def cmd_my_course(message: types.Message):
    await message.answer('Мой курс')



@dp.callback_query_handler()
async def callback_query_keyboard(call: types.CallbackQuery):
    # Fetch streams for the selected course
    if call.data.startswith('course_'):
        course_id = int(call.data.split('_')[1])
        course_name = call.data.split('_')[2]
        streams = get_streams_for_course(course_id)
        streams_list = []
        for item in streams:
            if item not in streams_list:
                streams_list.append(item)
        stream_list = InlineKeyboardMarkup(row_width=1)
        for stream_name in streams_list:
            stream_list.add(InlineKeyboardButton(text=stream_name[0], callback_data=f'stream_{course_id}_{stream_name[0]}'))
        stream_list.add(InlineKeyboardButton(text='Назад', callback_data='назад_в_меню'))
        await db.change_account_course(call.from_user.id, course_id)
        await bot.send_message(call.from_user.id,f'Вы выбрали курс {course_name}')
        await bot.send_message(call.from_user.id,'Выберите поток', reply_markup=stream_list)
    elif call.data.startswith('stream_'):
        stream_name = int(call.data.split('_')[2])
        await db.change_account_stream(call.from_user.id, stream_name)
        await bot.send_message(call.from_user.id,f'Вы выбрали поток {stream_name}')
        await bot.send_message(call.from_user.id,'Oтлично, этот бот будет уведомлять вас о занятия.Пока вы можете ознокомится дополнительными материалами и узнать график занятияx', reply_markup=kb.anyn_list)
    elif call.data == 'назад_в_меню':
        courses = get_course_names()
        course_list = InlineKeyboardMarkup(row_width=1)
        for course_id, course_name in courses:
            course_list.add(InlineKeyboardButton(text=course_name, callback_data=f'course_{course_id}_{course_name}'))
        await bot.send_message(call.from_user.id, 'Выберите на каком направлении обучаетесь',
                             reply_markup=course_list)
    elif call.data == 'Дополнительные материалы':
        await bot.send_message(call.from_user.id, 'Дополнительные материалы', reply_markup=kb.additional_materials)
    elif call.data == 'Расписание':
        user_id = call.from_user.id
        cur.execute("SELECT course_id, stream FROM accounts WHERE tg_id = ?", (user_id,))
        user_data = cur.fetchone()

        if user_data is None:
            await call.answer('У вас нет назначенного курса и потока.')
            return

        course_id, stream_id = user_data
        cur.execute("""
                   SELECT
                       stream.name AS stream_name,
                       stream.days,
                       stream.hours || ':' || stream.minutes AS time
                   FROM
                       stream
                   WHERE
                       stream.course_id = ?
                       AND
                       stream.name = ?
                   """, (course_id, stream_id))

        schedule = cur.fetchall()
        cur.execute("SELECT name FROM course WHERE id = ?", (course_id,))
        course_name = cur.fetchone()[0]
        if not schedule:
            await bot.send_message(call.from_user.id,'Нет расписания для вашего курса и потока.')
        else:
            response = f'Ваше расписание по курсу:{course_name}\n'
            response += "{:<15} {:<20} {:<10}\n".format("Поток", "Дни", "Время")
            for entry in schedule:
                stream_name, days, time = entry
                response += "{:<15} {:<20} {:<10}\n".format(stream_name, days, time)

            await bot.send_message(call.from_user.id , response)
    elif call.data == 'Все курсы':
        if call.from_user.id == int(os.getenv('ADMIN_ID')):
            await bot.send_message(call.from_user.id, 'Все курсы')
        else:
            await bot.send_message(call.from_user.id, 'Я тебя не понимаю. Напиши /start')


@dp.message_handler()
async def answer(message: types.Message):
    await message.reply("Я тебя не понимаю. Напиши /start")

async def send_messages_to_accounts():
    # Retrieve data from the "stream" table
    cur.execute("SELECT id, name, course_id,days, hours, minutes FROM stream")
    streams = cur.fetchall()

    for stream in streams:
        stream_id, stream_name, course_id,target_days_str, target_hour, target_minute = stream

        target_days = [day_mapping[day.strip()] for day in target_days_str.split(",")]
        target_time_1_hour = target_hour - 1
        target_time_5_minute = target_minute-5
        if target_time_5_minute < 0:
            target_time_5_minute = 60 + target_time_5_minute
            target_time_1_hour -= 1
        if target_time_1_hour < 0:
            target_time_1_hour = 24 + target_time_1_hour

        # Get the accounts that match the stream and course
        cur.execute("SELECT tg_id FROM accounts WHERE stream=? AND course_id=?", (stream_name, course_id))
        account_ids = cur.fetchall()
        cur.execute("SELECT name FROM course WHERE id=?", (course_id,))
        course_name = cur.fetchone()


        # Calculate the time to send the message
        current_datetime = datetime.now()
        current_day = current_datetime.weekday() # 0 = Monday, 6 = Sunday
        current_hour, current_minute = current_datetime.hour, current_datetime.minute
        print(current_day in target_days and current_hour == target_time_1_hour and current_minute == target_minute)

        if (current_day in target_days and current_hour == target_time_1_hour and current_minute == target_minute) or (current_day in target_days and current_hour == target_hour and current_minute == target_time_5_minute):
            day_names = [day_name for day_name, day_value in day_mapping.items() if day_value in target_days]
            day_names_str = ", ".join(day_names)
            if current_day in target_days and current_hour == target_hour and current_minute == target_time_5_minute:
                time_until_class_starts = '5 минут'
            else:
                time_until_class_starts = '1 час'
            message = f"Через {time_until_class_starts} начнется ваше занятие по курсу {course_name[0]}!"
            # Send the message to each account
            for account_id in account_ids:
                tg_id = account_id[0]
                await bot.send_message(tg_id, message)
        # Check if it's the right day and time to send the message
        elif current_day in target_days and current_hour == target_hour and current_minute == target_minute and current_hour == target_hour and current_minute == target_minute:
            day_names = [day_name for day_name, day_value in day_mapping.items() if day_value in target_days]
            day_names_str = ", ".join(day_names)
            message = f"It's time for your class on {day_names_str}: {stream_name}!"
            # Send the message to each account
            for account_id in account_ids:
                tg_id = account_id[0]
                await bot.send_message(tg_id, message)




if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
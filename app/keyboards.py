
from aiogram import Bot, Dispatcher, types, executor
import os
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

main = ReplyKeyboardMarkup(resize_keyboard=True)
main.add('О нас')

main_admin = ReplyKeyboardMarkup(resize_keyboard=True)
main_admin.add('О нас', 'Admin-panel')

admin_panel = ReplyKeyboardMarkup(resize_keyboard=True)
admin_panel.add('Студенты', 'Курсы', 'Все расписания', 'Потоки', 'Рассылка для всех', 'Добавить админа', 'Удалить админа')

student_list = ReplyKeyboardMarkup(resize_keyboard=True)
student_list.add('Список Студентов','Удалить студента', 'Назад_')

course_func = ReplyKeyboardMarkup(resize_keyboard=True)
course_func.add('Все курсы', 'Добавить курс','Изменить курс', 'Удалить курс', 'Назад_')

stream_func = ReplyKeyboardMarkup(resize_keyboard=True)
stream_func.add('Все потоки', 'Добавить поток','Изменить поток' ,  'Удалить поток', 'Назад_')


anyn_list = InlineKeyboardMarkup(row_width=2)
anyn_list.add(InlineKeyboardButton(text='Дополнительные материалы', callback_data='Дополнительные материалы'),
                InlineKeyboardButton(text='Расписание', callback_data='Расписание'),
                InlineKeyboardButton(text='Назад', callback_data='назад_в_меню'),)


additional_materials = InlineKeyboardMarkup(row_width=1)
additional_materials.add(InlineKeyboardButton(text='Основы программирования: Легендарный Гарвардский курс CS50', url='https://www.youtube.com/playlist?list=PLawfWYMUziZqyUL5QDLVbe3j5BKWj42E5'))
aboutus_link = InlineKeyboardMarkup(row_width=1)
aboutus_link.add(InlineKeyboardButton(text='Видео о нас', url='https://www.youtube.com/watch?v=QxSyW6EL1OE'), InlineKeyboardButton(text='Назад', callback_data='назад_в_меню'))
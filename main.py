import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from db import *

API_TOKEN = ''  # ВСТАВИТЬ ДАННЫЕ
admins = [1505244069]  # Вставить id админов

bot = telebot.TeleBot(API_TOKEN)

if __name__ == '__main__':
    create_database()
    print('Бот запущен')


class MyStates(StatesGroup):
    deleting_question = State()
    adding_question = State()
    adding_choices = State()
    getting_answer = State()


@bot.message_handler(commands=['start'])
def bot_start(message: telebot.types.Message):  # Начало бота. Бот определяет, является ли пользователь админом
    if message.from_user.id in admins:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id,
                         'Приветствую, мой повелитель. Чего изволите сделать на этот раз?', reply_markup=markup)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id,
                         'Здравствуйте, это бот для прохождения опросов. Нажмите на кнопку ниже, чтобы перейти в меню',
                         reply_markup=markup)


@bot.message_handler(state=MyStates.adding_choices)
def bot_add_choices(message: telebot.types.Message):  # Добавляем варианты ответа (минимум 2) к вопросу
    if message.text == 'Отменить':  # Отдельный вариант "отменить", т.к. нужно удалить созданный вопрос из базы данных
        with bot.retrieve_data(message.from_user.id) as data:
            inserted_question_id = data['question_id']
        delete_question(inserted_question_id)
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id, 'Создание вопроса отменено', reply_markup=markup)
        bot.delete_state(message.from_user.id)
    else:
        choices = message.text.split('\n')
        if len(choices) < 2:  # Проверяем, что вариантов минимум 2
            bot.send_message(message.chat.id, 'Необходимо 2 варианта ответа, однако Вы ввели лишь 1 вариант.\n'
                                              'Пожалуйста, введите вновь свои варианты ответа \n'
                                              'Если вы пытаетесь ввести команду, сперва нажмите на "Отменить"')
        else:
            with bot.retrieve_data(message.from_user.id) as data:
                inserted_question_id = data['question_id']
            for i in choices:
                if len(i) > 30:
                    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
                    markup.add(
                        telebot.types.KeyboardButton("Отменить")
                    )
                    bot.send_message(message.chat.id,
                                     f'Один из вариантов был в длину {len(i)} символов, при допустимых 30. '
                                     f'Пожалуйста, отправьте варианты ответа повторно', reply_markup=markup)
                    break
            for n in choices:
                add_choice(n, inserted_question_id)
            bot.delete_state(message.from_user.id, message.chat.id)
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add(
                telebot.types.KeyboardButton("Меню")
            )
            bot.send_message(message.chat.id, 'Ваш вопрос успешно добавлен', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Отменить')
def bot_cancel(message: telebot.types.Message):  # При нажатии отменяет любое происходящее действие
    bot.delete_state(message.from_user.id, message.chat.id)
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Меню")
    )
    bot.send_message(message.chat.id, 'Действие отменено', reply_markup=markup)


@bot.message_handler(state=MyStates.adding_question)
def bot_add_question(message: telebot.types.Message):  # Добавляем вопрос в базу данных
    if len(message.text) > 100:  # Если введенный текст более 100 символов, просим ввести вопрос повторно
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Отменить")
        )
        bot.send_message(message.chat.id,
                         f'Вопрос не должен превышать 100 символов. Вы ввели вопрос длиной {len(message.text)} '
                         f'символов.\nПожалуйста, введите вопрос повторно, сократив число символов',
                         reply_markup=markup)
    else:
        publish_date = datetime.now()
        inserted_question_id = add_question(message.text, publish_date)
        with bot.retrieve_data(message.from_user.id) as data:
            data['question_id'] = inserted_question_id
        bot.set_state(message.from_user.id, MyStates.adding_choices, message.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Отменить")
        )
        bot.send_message(message.chat.id, 'Введите минимум 2 варианта ответа (не длиннее 30 символов каждый, по '
                                          'одному варианту ответа на каждой строке):\n', reply_markup=markup)


@bot.message_handler(state=MyStates.deleting_question)
def bot_delete_question(message: telebot.types.Message):  # Удаляем вопрос из базы данных
    try:
        int(message.text)
    except Exception:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Отменить")
        )
        bot.send_message(message.chat.id, 'Вам необходимо ввести номер вопроса, попробуйте снова\n'
                                          'Если вы пытаетесь ввести команду, сперва нажмите на "Отменить"',
                         reply_markup=markup)
    else:
        if not delete_question(message.text):  # Если вопроса с таким номером нет, просим ввести номер повторно
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add(
                telebot.types.KeyboardButton("Отменить")
            )
            bot.send_message(message.chat.id, 'Вопроса с таким номером нет, попробуйте снова', reply_markup=markup)
        else:
            bot.delete_state(message.from_user.id, message.chat.id)
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add(
                telebot.types.KeyboardButton("Меню")
            )
            bot.send_message(message.chat.id, f'Вопрос {message.text} успешно удален', reply_markup=markup)


@bot.message_handler(state=MyStates.getting_answer)
def bot_answer_question(message: telebot.types.Message):  # Отвечаем на вопрос, вносим данные в базу
    with bot.retrieve_data(message.from_user.id) as data:
        question_to_answer = data['question_to_answer']
    try:
        picked_choice = get_choices_for_question(question_to_answer)[int(message.text) - 1]  # Если вопроса с таким
        # номером нет, просим повторить попытку
    except Exception:
        bot.send_message(message.chat.id, 'Вы ввели что-то не так. Попробуйте снова')
    else:
        answer_question(message.from_user.id, question_to_answer, picked_choice)
        bot.delete_state(message.from_user.id, message.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id, 'Ваш ответ успешно добавлен', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Меню')
def bot_menu(message: telebot.types.Message):  # Бот выводит меню в зависимости от того, админ ли пользователь или нет
    if message.from_user.id in admins:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Пройти опрос"),
            telebot.types.KeyboardButton("Получить личную статистику")
        )
        markup.add(
            telebot.types.KeyboardButton("Создать вопрос"),
            telebot.types.KeyboardButton("Удалить вопрос"),
            telebot.types.KeyboardButton("Получить общую статистику")
        )
        bot.send_message(message.chat.id, 'Выберите желаемый пункт из меню', reply_markup=markup)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Пройти опрос"),
            telebot.types.KeyboardButton("Получить личную статистику")
        )
        bot.send_message(message.chat.id, 'Выберите желаемый пункт из меню', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Получить общую статистику')
def bot_get_statistic(message: telebot.types.Message):  # Получаем общую статистику
    text = get_all_statistic()  # Если вопросов нет, сообщаем об этом админу
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Меню")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Получить личную статистику')
def bot_get_own_statistic(message: telebot.types.Message):  # Получаем личную статистику
    text = get_own_statistic(message.from_user.id)  # Если вопросов нет, сообщаем об этом пользователю
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Меню")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Удалить вопрос')
def bot_wait_to_delete(message: telebot.types.Message):  # Запрашиваем номер вопроса для удаления
    questions = get_all_questions()
    if isinstance(questions, list):  # Если вопросов нет, сообщаем об этом админу
        text = questions[0]
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Отменить")
        )
        bot.send_message(message.chat.id, 'Введите id вопроса, который хотите удалить\n',
                         reply_markup=markup)
        text = questions
        bot.set_state(message.from_user.id, MyStates.deleting_question, message.chat.id)
        bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == 'Создать вопрос')
def bot_wait_to_add(message: telebot.types.Message):  # Запрашиваем вопрос для его добавления в базу данных
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Отменить")
    )
    bot.send_message(message.chat.id, 'Введите вопрос (не более 100 символов):\n',
                     reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.adding_question, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Пройти опрос')
def bot_get_question(message: telebot.types.Message):  # Выдаем пользователю вопрос
    question = get_question(message.from_user.id)
    if not question:  # Если вопросов нет, сообщаем об этом пользователю
        text = 'Вопросов еще нет или вы уже ответили на все вопросы. Дождитесь появления новых'
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Меню")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        text = question[0]
        bot.send_message(message.chat.id, text, reply_markup=types.ReplyKeyboardRemove())
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Отменить")
        )
        bot.send_message(message.chat.id,
                         '\nВыберите один из вариантов ответа и отправьте его номер', reply_markup=markup)
        bot.set_state(message.from_user.id, MyStates.getting_answer, message.chat.id)
        with bot.retrieve_data(message.from_user.id) as data:
            data['question_to_answer'] = question[1]


@bot.message_handler(func=lambda message: True)
def wrong_command(message: telebot.types.Message):  # Выводится, если пользователь ввел что-то не так
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Меню")
    )
    bot.send_message(message.chat.id, 'К сожалению, я не ИИ и не понимаю Вас. '
                                      'Возможно, в будущем мой повелитель поможет мне п̶о̶р̶а̶б̶о̶т̶и̶т̶ь̶ ̶м̶и̶р̶'
                                      ' начать свободно общаться с пользователями. \nНу а пока, выберите команду из '
                                      'меню',
                     reply_markup=markup)


bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))
bot.infinity_polling()

import psycopg2
from datetime import datetime


def get_connection_to_database():
    conn = psycopg2.connect(
        dbname="",
        user="",
        password='', #ВСТАВИТЬ ДАННЫЕ
        host='',
        port=,
    )
    return conn


def decorator_add_connection(func):
    def wrapper(*args, **kwargs):
        conn = get_connection_to_database()
        result = func(*args, **kwargs, conn=conn)
        conn.close()
        return result

    return wrapper


@decorator_add_connection
def create_database(conn=None):  # Создаем базу данных
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS public.question(
    id integer NOT NULL,
    question_text character varying(100) NOT NULL,
    publish_date time without time zone,
    PRIMARY KEY (id)
    );""")
    conn.commit()
    cur.execute("""CREATE TABLE IF NOT EXISTS public.choice (
    id integer NOT NULL,
    choice_text character varying(30) NOT NULL,
    votes bigint,
    question_id integer NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT question_id FOREIGN KEY (question_id)
        REFERENCES public.question (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
    );""")
    conn.commit()
    cur.execute("""CREATE TABLE IF NOT EXISTS public.statistic (
    id bigint NOT NULL,
    tg_user_id integer NOT NULL,
    question_id integer NOT NULL,
    choice_id integer NOT NULL,
    CONSTRAINT choice_id FOREIGN KEY (choice_id)
        REFERENCES public.choice (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT question_id FOREIGN KEY (question_id)
        REFERENCES public.question (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
    );""")
    conn.commit()
    try:  # Создаем самый важный вопрос :)
        publish_date = datetime.now()
        cur.execute("INSERT INTO question VALUES (1, 'Вам нравится мой бот?', (%s));", (publish_date,))
        cur.execute("INSERT INTO choice VALUES (1, 'Да', 0, 1),(2, 'Да, очень', 0, 1),(3, 'Определенно да', 0, 1);")
    except Exception:
        cur.close()
    else:
        conn.commit()
        cur.close()


@decorator_add_connection
def get_all_questions(conn=None):  # Получаем все вопросы с ответами
    cur = conn.cursor()
    cur.execute('SELECT * FROM question ORDER BY id ASC')
    select = cur.fetchall()
    if not select:
        return ['Повелитель, Вы забыли? Вопросов еще нет', False]  # Если вопросов нет, возвращаем список с False
    select_list = [list(b) for b in select]
    answer = 'Вопросы:\n'
    for i in select_list:
        answer += f'Вопрос {i[0]}: {i[1]}\n'
    cur.close()
    return answer


@decorator_add_connection
def get_choices_for_question(question_id, conn=None):  # Получаем варианты ответа на вопрос
    with conn.cursor() as cur:
        cur.execute("""SELECT choice.id FROM choice WHERE question_id = (%s)""", (question_id,))
        select = cur.fetchall()
        answer = []
        for _ in select:
            for item in _:
                answer.append(item)
    return answer


@decorator_add_connection
def find_not_answered(user_id, conn=None):  # Находим вопрос, на который пользователь не давал ответа
    with conn.cursor() as cur:
        cur.execute("SELECT question.id FROM question")
        all_questions = cur.fetchall()
        questions_list = []
        for _ in all_questions:
            for item in _:
                questions_list.append(item)
        cur.execute("""SELECT question.id FROM question
JOIN statistic ON statistic.question_id = question.id and statistic.tg_user_id = (%s)""", (user_id,))
        select = cur.fetchall()
        select_list = []
        for _ in select:
            for item in _:
                select_list.append(item)
        answer = 0
        for i in questions_list:
            if i not in select_list:
                answer = i
                break
        if answer == 0:
            return False
        else:
            return answer


@decorator_add_connection
def find_empty_id(DB, conn=None):  # Находим свободное id в таблице X
    with conn.cursor() as cur:
        if DB == 'question':
            cur.execute("SELECT id from question")
        elif DB == 'choice':
            cur.execute("SELECT id from choice")
        elif DB == 'statistic':
            cur.execute("SELECT id from statistic")
        select = cur.fetchall()
        select_list = []
        for _ in select:
            for item in _:
                select_list.append(item)

        free_id = 1
        while free_id in select_list:
            free_id += 1
        return free_id


@decorator_add_connection
def add_question(question_text, publish_date, conn=None):  # Добавляем в базу данных вопрос
    conn.autocommit = False
    cur = conn.cursor()
    number = find_empty_id("question")
    cur.execute("INSERT INTO question VALUES ((%s), (%s), (%s))", (number, question_text, publish_date,))
    conn.commit()
    cur.close()
    return int(number)


@decorator_add_connection
def add_choice(choice_text, question_id, conn=None):  # Добавляем в базу данных варианты ответа на вопрос
    conn.autocommit = False
    cur = conn.cursor()
    number = find_empty_id("choice")
    cur.execute("INSERT INTO choice VALUES ((%s), (%s), (%s), (%s))", (number, choice_text, 0, question_id), )
    conn.commit()
    cur.close()


@decorator_add_connection
def delete_question(question_id, conn=None):  # Удаляем вопрос
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("""SELECT FROM question WHERE question.id = (%s)""", (question_id,))
    select = cur.fetchall()
    if not select:  # Если вопросов нет, возвращаем False
        cur.close()
        return False
    else:
        cur.execute("DELETE FROM statistic WHERE statistic.question_id = (%s)", (question_id,))
        cur.execute("DELETE FROM choice WHERE choice.question_id = (%s)", (question_id,))
        cur.execute("DELETE FROM question WHERE question.id = (%s)", (question_id,))
        conn.commit()
        cur.close()
        return True


@decorator_add_connection
def get_question(user_id, conn=None):  # Получаем уникальный вопрос
    question_id = find_not_answered(user_id)
    if not question_id:
        return False  # Если на все ответили или вопросов нет возвращаем False
    else:
        cur = conn.cursor()
        cur.execute("""SELECT question.question_text, choice.choice_text FROM question
    JOIN choice ON question.id = choice.question_id and choice.question_id = (%s)""", (question_id,))
        select = cur.fetchall()
        select_list = [list(b) for b in select]
        cur.close()
        answer = f"{select_list[0][0]} \n"
        number = 0
        for i in select_list:
            answer += f"{number + 1}: {i[1]}\n"
            number += 1
        return [answer, question_id]


@decorator_add_connection
def answer_question(tg_user_id, question_id, choice_id, conn=None):  # Отвечаем на вопрос
    conn.autocommit = False
    cur = conn.cursor()
    number = find_empty_id('statistic')
    cur.execute("""INSERT INTO statistic VALUES ((%s),(%s),(%s),(%s))""", (number, tg_user_id, question_id, choice_id))
    conn.commit()
    cur.execute("""SELECT votes FROM choice
    WHERE id = (%s) and question_id = (%s)""", (choice_id, question_id,))
    votes_number = cur.fetchall()
    votes_number_list = []
    for _ in votes_number:
        for item in _:
            votes_number_list.append(item)
    votes_number = votes_number_list[0] + 1
    cur.execute("""UPDATE choice
SET votes = (%s)
WHERE id = (%s) and question_id = (%s)""", (votes_number, choice_id, question_id))
    conn.commit()
    cur.close()


@decorator_add_connection
def get_all_statistic(conn=None):  # Получаем общую статистику
    cur = conn.cursor()
    cur.execute("SELECT * FROM public.question ORDER BY id ASC ")
    questions = cur.fetchall()
    if not questions:
        cur.close()
        conn.close()
        return 'Повелитель, вопросов еще нет. Создайте их, воспользовавшись соответствующей функцией в меню'
    else:
        questions_list = [list(b) for b in questions]

        answer = ''
        for i in questions_list:
            answer += f"\nВопрос {i[0]}: {i[1]} \n"
            answer += f"Ответы: \n"
            cur.execute("SELECT choice_text, votes FROM choice WHERE question_id = (%s)"
                        "ORDER BY id ASC", (i[0],))
            choices = cur.fetchall()
            choices_list = [list(b) for b in choices]
            for f in choices_list:
                answer += f"- {f[0]} -- {f[1]} \n"
    cur.close()
    return answer


@decorator_add_connection
def get_own_statistic(tg_user_id, conn=None):  # Получаем личную статистику
    with conn.cursor() as cur:
        cur.execute("""SELECT question.id, question.question_text, choice.choice_text FROM statistic
JOIN question ON statistic.question_id = question.id
JOIN choice on statistic.choice_id = choice.id
WHERE statistic.tg_user_id = (%s)
ORDER BY id ASC""", (tg_user_id,))
        user_answers = cur.fetchall()
        if not user_answers:
            return ('Вы еще не прошли ни одного опроса.\nСкорее сделайте это, воспользовавшись соответствующей кнопкой '
                    'в меню')
        else:
            user_answers_list = [list(b) for b in user_answers]
            answer = ""
            for i in user_answers_list:
                answer += f"\nВопрос {i[0]}: {i[1]} -- {i[2]}"
    return answer

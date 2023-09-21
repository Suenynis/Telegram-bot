import sqlite3 as sq
import datetime
db = sq.connect('tg.db')
cur = db.cursor()


async def db_start():
    cur.execute("CREATE TABLE IF NOT EXISTS accounts ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "name TEXT, "
                "tg_id INTEGER, "
                "cart_id TEXT, "
                "course_id INTEGER, "
                "stream INTEGER, "
                "is_admin INTEGER DEFAULT 0)"  # Set the default value to 0
                )

    cur.execute("CREATE TABLE IF NOT EXISTS course ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "name TEXT, "
                "description TEXT) "
                )

    cur.execute("CREATE TABLE IF NOT EXISTS stream ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "name TEXT, "
                "course_id INTEGER ,"
                "days TEXT,"
                "hours INTEGER, "
                "minutes INTEGER "
                ")"
                )

    db.commit()


async def cmd_start_db(user_id, name):
    user = cur.execute("SELECT * FROM accounts WHERE tg_id = ?", (user_id,)).fetchone()
    if not user:
        cur.execute("INSERT INTO accounts (tg_id, name) VALUES (?, ?)", (user_id, name))
        db.commit()

async def change_account_course(tg_id, new_course):
    # Update the course for a specific account
    cur.execute("UPDATE accounts SET course_id=? WHERE tg_id=?", (new_course, tg_id))
    db.commit()

async def change_account_stream(tg_id, new_course):
    # Update the course for a specific account
    cur.execute("UPDATE accounts SET stream=? WHERE tg_id=?", (new_course, tg_id))
    db.commit()

async def get_account_sheadule(tg_id):
    # Get the course for a specific account
    return cur.execute("SELECT stream FROM accounts WHERE tg_id=?", (tg_id,)).fetchone()[0]







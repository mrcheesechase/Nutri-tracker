import sqlite3
import json
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'tracker.db'


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            height_cm REAL,
            start_weight_kg REAL,
            goal_weight_kg REAL,
            activity_level TEXT,
            goal_weeks INTEGER,
            bmr REAL,
            tdee REAL,
            daily_calorie_target REAL,
            protein_target_g REAL,
            fat_target_g REAL,
            carb_target_g REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log_date TEXT,
            weight_kg REAL,
            notes TEXT,
            UNIQUE(user_id, log_date),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log_date TEXT,
            meal_type TEXT,
            food_description TEXT,
            quantity TEXT,
            calories REAL DEFAULT 0,
            protein_g REAL DEFAULT 0,
            fat_g REAL DEFAULT 0,
            carbs_g REAL DEFAULT 0,
            fiber_g REAL DEFAULT 0,
            sugar_g REAL DEFAULT 0,
            saturated_fat_g REAL DEFAULT 0,
            monounsaturated_fat_g REAL DEFAULT 0,
            polyunsaturated_fat_g REAL DEFAULT 0,
            trans_fat_g REAL DEFAULT 0,
            omega3_g REAL DEFAULT 0,
            omega6_g REAL DEFAULT 0,
            vitamins TEXT DEFAULT '{}',
            minerals TEXT DEFAULT '{}',
            amino_acids TEXT DEFAULT '{}',
            confidence TEXT DEFAULT 'medium',
            ai_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS progress_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            photo_date TEXT,
            file_id TEXT,
            caption TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user(data):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users
        (user_id, name, age, gender, height_cm, start_weight_kg, goal_weight_kg,
         activity_level, goal_weeks, bmr, tdee, daily_calorie_target,
         protein_target_g, fat_target_g, carb_target_g, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        data['user_id'], data['name'], data['age'], data['gender'],
        data['height_cm'], data['start_weight_kg'], data['goal_weight_kg'],
        data['activity_level'], data['goal_weeks'],
        data['bmr'], data['tdee'], data['daily_calorie_target'],
        data['protein_target_g'], data['fat_target_g'], data['carb_target_g'],
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def log_weight(user_id, weight_kg, notes=None):
    conn = get_conn()
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('''
        INSERT OR REPLACE INTO weight_logs (user_id, log_date, weight_kg, notes)
        VALUES (?,?,?,?)
    ''', (user_id, today, weight_kg, notes))
    conn.commit()
    conn.close()


def get_weight_logs(user_id, limit=90):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM weight_logs WHERE user_id = ?
        ORDER BY log_date DESC LIMIT ?
    ''', (user_id, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_today_weight(user_id):
    conn = get_conn()
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('SELECT weight_kg FROM weight_logs WHERE user_id=? AND log_date=?', (user_id, today))
    row = c.fetchone()
    conn.close()
    return row['weight_kg'] if row else None


def log_food(user_id, meal_type, food_description, quantity, nd):
    conn = get_conn()
    c = conn.cursor()
    today = date.today().isoformat()
    macros = nd.get('macros', {})
    fats = nd.get('fats', {})
    c.execute('''
        INSERT INTO food_logs
        (user_id, log_date, meal_type, food_description, quantity,
         calories, protein_g, fat_g, carbs_g, fiber_g, sugar_g,
         saturated_fat_g, monounsaturated_fat_g, polyunsaturated_fat_g,
         trans_fat_g, omega3_g, omega6_g,
         vitamins, minerals, amino_acids, confidence, ai_notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        user_id, today, meal_type, food_description, str(quantity),
        nd.get('calories', 0),
        macros.get('protein_g', 0), macros.get('fat_g', 0), macros.get('carbs_g', 0),
        macros.get('fiber_g', 0), macros.get('sugar_g', 0),
        fats.get('saturated_g', 0), fats.get('monounsaturated_g', 0), fats.get('polyunsaturated_g', 0),
        fats.get('trans_g', 0), fats.get('omega3_g', 0), fats.get('omega6_g', 0),
        json.dumps(nd.get('vitamins', {})),
        json.dumps(nd.get('minerals', {})),
        json.dumps(nd.get('amino_acids', {})),
        nd.get('confidence', 'medium'),
        nd.get('notes', '')
    ))
    conn.commit()
    conn.close()


def get_food_logs_date(user_id, log_date=None):
    if log_date is None:
        log_date = date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM food_logs WHERE user_id=? AND log_date=? ORDER BY id', (user_id, log_date))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_food_logs_range(user_id, start_date, end_date):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT log_date,
               SUM(calories) as cal, SUM(protein_g) as pro,
               SUM(fat_g) as fat, SUM(carbs_g) as carb
        FROM food_logs WHERE user_id=? AND log_date BETWEEN ? AND ?
        GROUP BY log_date ORDER BY log_date
    ''', (user_id, start_date, end_date))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def delete_food_log(user_id, food_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM food_logs WHERE id=? AND user_id=?', (food_id, user_id))
    conn.commit()
    conn.close()


def save_progress_photo(user_id, file_id, caption=None):
    conn = get_conn()
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('INSERT INTO progress_photos (user_id, photo_date, file_id, caption) VALUES (?,?,?,?)',
              (user_id, today, file_id, caption))
    conn.commit()
    conn.close()


def get_progress_photos(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM progress_photos WHERE user_id=? ORDER BY photo_date DESC', (user_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def delete_all_user_data(user_id):
    conn = get_conn()
    c = conn.cursor()
    for table in ['food_logs', 'weight_logs', 'progress_photos', 'users']:
        c.execute(f'DELETE FROM {table} WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

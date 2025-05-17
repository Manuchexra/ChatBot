import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
import json

class Database:
    def __init__(self, db_name: str = "knowledge_bot.db"):
        self.db_name = db_name
        self._initialize_database()

    def _initialize_database(self):
        """Ma'lumotlar bazasi jadvallarini yaratish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Foydalanuvchilar jadvali
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'uz',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                total_questions INTEGER DEFAULT 0
            )
            ''')
            
            # Bilimlar bazasi jadvali
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                tags TEXT,
                language TEXT DEFAULT 'uz',
                author_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                views INTEGER DEFAULT 0,
                FOREIGN KEY(author_id) REFERENCES users(user_id)
            )
            ''')
            
            # Statistika jadvali
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            
            # Favoritlar jadvali
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                knowledge_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, knowledge_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(knowledge_id) REFERENCES knowledge(id)
            )
            ''')
            
            conn.commit()

    def _get_connection(self):
        """Bazaga ulanishni olish"""
        return sqlite3.connect(self.db_name)

    # --- USER OPERATIONS ---
    def add_or_update_user(self, user_id: int, username: str, first_name: str, last_name: str, is_admin: bool = False):
        """Foydalanuvchi qo'shish yoki yangilash"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, last_activity, is_admin)
            VALUES (?, ?, ?, ?, datetime('now'), ?)
            ''', (user_id, username, first_name, last_name, is_admin))
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi ma'lumotlarini olish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def update_user_language(self, user_id: int, language: str):
        """Foydalanuvchi tilini yangilash"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
            conn.commit()

    # --- KNOWLEDGE OPERATIONS ---
    def add_knowledge(
        self, 
        question: str, 
        answer: str, 
        author_id: int, 
        tags: List[str] = None, 
        language: str = 'uz'
    ) -> int:
        """Yangi bilim qo'shish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tags_json = json.dumps(tags) if tags else None
            
            cursor.execute('''
            INSERT INTO knowledge 
            (question, answer, tags, language, author_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (question, answer, tags_json, language, author_id))
            
            # Foydalanuvchining savollar sonini yangilash
            cursor.execute('''
            UPDATE users SET total_questions = total_questions + 1 
            WHERE user_id = ?
            ''', (author_id,))
            
            conn.commit()
            return cursor.lastrowid

    def get_knowledge(self, knowledge_id: int) -> Optional[Dict]:
        """Bilimni ID bo'yicha olish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT k.*, u.username as author_username 
            FROM knowledge k
            LEFT JOIN users u ON k.author_id = u.user_id
            WHERE k.id = ?
            ''', (knowledge_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                knowledge = dict(zip(columns, row))
                
                # Ko'rishlar sonini yangilash
                cursor.execute('''
                UPDATE knowledge SET views = views + 1 
                WHERE id = ?
                ''', (knowledge_id,))
                conn.commit()
                
                if knowledge.get('tags'):
                    knowledge['tags'] = json.loads(knowledge['tags'])
                
                return knowledge
            return None

    def search_knowledge(self, query: str, language: str = None, limit: int = 5) -> List[Dict]:
        """Bilimlar bazasidan qidirish"""
        with self._get_connection() as conn:
            # Pandas yordamida qidirish
            df = pd.read_sql('''
            SELECT id, question, answer, tags 
            FROM knowledge 
            WHERE language = ? OR ? IS NULL
            ''', conn, params=(language, language))
            
            if df.empty:
                return []
            
            # TF-IDF vektorizatsiya
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(df['question'])
            
            # Foydalanuvchi so'rovini vektorga aylantirish
            query_vec = vectorizer.transform([query])
            
            # O'xshashlikni hisoblash
            similarities = cosine_similarity(query_vec, tfidf_matrix)
            df['similarity'] = similarities[0]
            
            # Eng yuqori o'xshashlikdagi natijalarni qaytarish
            results = df.nlargest(limit, 'similarity')
            results = results[results['similarity'] > 0.2]  # Kamida 20% o'xshashlik
            
            return results.to_dict('records')

    def get_random_question(self, language: str = None) -> Optional[Dict]:
        """Tasodifiy savol olish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = '''
            SELECT id, question, answer 
            FROM knowledge 
            WHERE language = ? OR ? IS NULL
            ORDER BY RANDOM() 
            LIMIT 1
            '''
            cursor.execute(query, (language, language))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    # --- STATISTICS OPERATIONS ---
    def log_action(self, user_id: int, action: str, details: str = None):
        """Foydalanuvchi harakatini log qilish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO statistics (user_id, action, details)
            VALUES (?, ?, ?)
            ''', (user_id, action, details))
            
            # Foydalanuvchi faolligini yangilash
            cursor.execute('''
            UPDATE users SET last_activity = datetime('now') 
            WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()

    def get_user_stats(self, user_id: int) -> Dict:
        """Foydalanuvchi statistikasini olish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Asosiy statistikalar
            cursor.execute('''
            SELECT 
                COUNT(DISTINCT id) as questions_added,
                SUM(views) as total_views,
                COUNT(DISTINCT f.knowledge_id) as favorites_count
            FROM knowledge k
            LEFT JOIN favorites f ON k.id = f.knowledge_id
            WHERE k.author_id = ?
            ''', (user_id,))
            stats = cursor.fetchone()
            
            # Harakatlar tarixi
            cursor.execute('''
            SELECT action, COUNT(*) as count 
            FROM statistics 
            WHERE user_id = ?
            GROUP BY action
            ''', (user_id,))
            actions = cursor.fetchall()
            
            return {
                'questions_added': stats[0] if stats else 0,
                'total_views': stats[1] if stats else 0,
                'favorites_count': stats[2] if stats else 0,
                'actions': {action: count for action, count in actions}
            }

    # --- FAVORITES OPERATIONS ---
    def add_to_favorites(self, user_id: int, knowledge_id: int):
        """Favoritlarga qo'shish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO favorites (user_id, knowledge_id)
                VALUES (?, ?)
                ''', (user_id, knowledge_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:  # Agar allaqachon mavjud bo'lsa
                return False

    def remove_from_favorites(self, user_id: int, knowledge_id: int):
        """Favoritlardan olib tashlash"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            DELETE FROM favorites 
            WHERE user_id = ? AND knowledge_id = ?
            ''', (user_id, knowledge_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_user_favorites(self, user_id: int) -> List[Dict]:
        """Foydalanuvchi favoritlarini olish"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT k.id, k.question, k.answer
            FROM knowledge k
            JOIN favorites f ON k.id = f.knowledge_id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
            ''', (user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # --- ADMIN OPERATIONS ---
    def export_to_csv(self, file_path: str):
        """Ma'lumotlarni CSV faylga eksport qilish"""
        with self._get_connection() as conn:
            # Bilimlar bazasini eksport qilish
            df_knowledge = pd.read_sql('SELECT * FROM knowledge', conn)
            df_knowledge.to_csv(f'{file_path}/knowledge.csv', index=False)
            
            # Foydalanuvchilarni eksport qilish
            df_users = pd.read_sql('SELECT * FROM users', conn)
            df_users.to_csv(f'{file_path}/users.csv', index=False)
            
            # Statistikani eksport qilish
            df_stats = pd.read_sql('SELECT * FROM statistics', conn)
            df_stats.to_csv(f'{file_path}/statistics.csv', index=False)

    def import_from_csv(self, file_path: str):
        """CSV fayldan ma'lumotlarni import qilish"""
        with self._get_connection() as conn:
            # Bilimlar bazasini import qilish
            df_knowledge = pd.read_csv(f'{file_path}/knowledge.csv')
            df_knowledge.to_sql('knowledge', conn, if_exists='append', index=False)
            
            # Foydalanuvchilarni import qilish
            df_users = pd.read_csv(f'{file_path}/users.csv')
            df_users.to_sql('users', conn, if_exists='append', index=False)
            
            # Statistikani import qilish
            df_stats = pd.read_csv(f'{file_path}/statistics.csv')
            df_stats.to_sql('statistics', conn, if_exists='append', index=False)
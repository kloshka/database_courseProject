import psycopg2
import random
import json
import traceback  
from faker import Faker
from datetime import date, timedelta, datetime
import os
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'animedb'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
    'host': os.getenv('DB_HOST', 'db'),  
    'port': os.getenv('DB_PORT', '5432')
}

fake = Faker('ru_RU')  
fake_en = Faker()     
NUM_USERS = 10000
NUM_TITLES = 30000

def run_seed():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()
    
    print("🚀 Начинаем заполнение базы данных...")
    
    try:
        print("🧹 Очистка старых данных...")
        tables = [
            'reports', 'audit_log', 'reviews', 'user_library',
            'title_authors', 'title_genres', 'title_studios',
            'titles', 'studios', 'genres', 'authors',
            'user_profiles', 'users'
        ]
        
        for table in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception as e:
                print(f"   Не удалось очистить {table}: {e}")
        
        # 1. ЖАНРЫ
        print("📚 Жанры...")
        genres = [
            ('Сёнен', 'Для юношей, экшен, приключения'),
            ('Сёдзе', 'Для девушек, романтика, драма'),
            ('Фэнтези', 'Магия, мифические существа'),
            ('Исекай', 'Попаданцы в другой мир'),
            ('Романтика', 'Любовные истории'),
            ('Комедия', 'Юмористические произведения'),
            ('Драма', 'Эмоциональные, серьезные сюжеты'),
            ('Боевик', 'Экшен, сражения'),
            ('Детектив', 'Расследования, загадки'),
            ('Повседневность', 'Повседневная жизнь'),
            ('Гарем', 'Один главный герой и несколько девушек'),
            ('Хоррор', 'Ужасы, страшные сюжеты'),
            ('Меха', 'Роботы, механизмы'),
            ('Музыкальный', 'Музыка и выступления'),
            ('Спорт', 'Спортивные соревнования'),
            ('Триллер', 'Напряженные сюжеты'),
            ('Научная фантастика', 'Фантастика, технологии будущего')
        ]
        for name, desc in genres:
            cur.execute(
                "INSERT INTO genres (name, description) VALUES (%s, %s)",
                (name, desc)
            )
        
        cur.execute("SELECT id FROM genres")
        genre_ids = [r[0] for r in cur.fetchall()]
        
        # 2. СТУДИИ
        print("🎬 Студии...")
        studio_ids = []
        studios = [
            ('MAPPA', 'studio'),
            ('Wit Studio', 'studio'),
            ('Kyoto Animation', 'studio'),
            ('Bones', 'studio'),
            ('Madhouse', 'studio'),
            ('Toei Animation', 'studio'),
            ('Studio Ghibli', 'studio'),
            ('Ufotable', 'studio'),
            ('A-1 Pictures', 'studio'),
            ('Pierrot', 'studio'),
            ('White Fox', 'studio'),
            ('Shaft', 'studio'),
            ('J.C.Staff', 'studio'),
            ('Production I.G', 'studio'),
            ('Trigger', 'studio')
        ]
        for name, s_type in studios:
            cur.execute("""
                INSERT INTO studios (name, type, country, founded_date) 
                VALUES (%s, %s, 'Japan', %s) RETURNING id
            """, (name, s_type, fake.date_between(start_date='-40y', end_date='-5y')))
            studio_ids.append(cur.fetchone()[0])
        
        # 3. АВТОРЫ
        print("👨‍🎨 Авторы...")
        author_ids = []
        authors = [
            ('Хадзимэ Исаяма', 'mangaka'),
            ('Эйитиро Ода', 'mangaka'),
            ('Масаси Кисимото', 'mangaka'),
            ('Хирохико Араки', 'mangaka'),
            ('Наоко Такэути', 'mangaka'),
            ('Румико Такахаси', 'mangaka'),
            ('Тайто Кубо', 'mangaka'),
            ('Кохэй Хорикоси', 'mangaka'),
            ('Ёсихиро Тогаси', 'mangaka'),
            ('Цутому Ниихэй', 'mangaka'),
            ('Макото Синкай', 'director'),
            ('Хаяо Миядзаки', 'director'),
            ('Сатико Мицуми', 'screenwriter'),
            ('Джэнъитиро Суито', 'screenwriter')
        ]
        for name, role in authors:
            cur.execute(
                "INSERT INTO authors (full_name, role) VALUES (%s, %s) RETURNING id",
                (name, role)
            )
            author_ids.append(cur.fetchone()[0])
        
        print(f"👥 Пользователи ({NUM_USERS})...")
        user_ids = []
        generated_emails = set()  

        for i in range(NUM_USERS):
            max_attempts = 10  
            email = None
            
            for attempt in range(max_attempts):
                username_part = fake.user_name().replace('.', '').replace('-', '')
                email = f"{username_part}{i}{random.randint(1000, 9999)}@example.com"
                
                if email not in generated_emails:
                    generated_emails.add(email)
                    break
                email = None
            
            if email is None:
                email = f"user{i}_{random.randint(10000, 99999)}@example.com"
                generated_emails.add(email)
            
            username = f"{fake.user_name().replace(' ', '_').replace('.', '').lower()}{i}"
            
            cur.execute("""
                INSERT INTO users (username, email, password_hash, avatar_url, created_at) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (
                username,
                email,
                '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
                f'https://i.pravatar.cc/300?img={random.randint(1, 70)}',
                fake.date_time_between(start_date='-2y', end_date='now')
            ))
            uid = cur.fetchone()[0]
            user_ids.append(uid)
            
            # Профиль
            cur.execute("""
                INSERT INTO user_profiles (user_id, birth_date, about_text) 
                VALUES (%s, %s, %s)
            """, (
                uid,
                fake.date_of_birth(minimum_age=14, maximum_age=45),
                fake.text(max_nb_chars=150)
            ))
            
            if i % 100 == 0:
                print(f"   Создано {i} пользователей...")

        print(f"   Всего создано {len(user_ids)} пользователей")
        print(f"🎬 Тайтлы ({NUM_TITLES})...")
        title_ids = []
        
        anime_titles = [
            'Атака титанов', 'Наруто', 'Ван Пис', 'Тетрадь смерти', 'Стальной алхимик',
            'Самурай Чамплу', 'Ковбой Бибоп', 'Евангелион', 'Токийский гуль', 'Берсерк',
            'Ходячий замок', 'Унесённые призраками', 'Мой сосед Тоторо', 'Принцесса Мононоке',
            'Форма голоса', 'Твоё имя', 'Дракон-горничная', 'Волейбол', 'Баскетбол Куроко',
            'Чёрный клевер', 'Моб Психо 100', 'Ванпанчмен', 'Реинкарнация безработного',
            'Восхождение в тени', 'Цепь смерти', 'Магическая битва', 'Демон-убийца'
        ]
        
        for i in range(NUM_TITLES):
            t_type = random.choice(['anime', 'manga'])
            base_title = random.choice(anime_titles)
            
            canonical = f"{base_title} ({fake_en.word().title()}) #{i}"
            russian = f"{fake.word().title()} {fake.word().title()} {i}"
            
            status = random.choice(['announced', 'ongoing', 'released', 'discontinued'])
            start_date = fake.date_between(start_date='-15y', end_date='today')
            
            if status == 'released':
                end_date = fake.date_between(start_date=start_date, end_date='today')
            elif status == 'ongoing':
                end_date = None
            elif status == 'announced':
                start_date = fake.date_between(start_date='today', end_date='+2y')
                end_date = None
            else:  
                end_date = fake.date_between(start_date=start_date, end_date='today')
            
            if t_type == 'anime':
                episodes = random.randint(12, 100)
                volumes = chapters = None
            else:
                episodes = None
                volumes = random.randint(5, 50)
                chapters = random.randint(20, 300)
            
            cur.execute("""
                INSERT INTO titles (
                    type, canonical_title, russian_title, synopsis, poster_url, status,
                    start_date, end_date, episodes_count, volumes_count, chapters_count,
                    total_score, vote_count, average_rating
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                t_type,
                canonical,
                russian,
                fake.paragraph(nb_sentences=3),
                f'https://placehold.co/300x450/2A2A3A/FFF?text={canonical.replace(" ", "+")}',
                status,
                start_date,
                end_date,
                episodes,
                volumes,
                chapters,
                0, 0, None 
            ))
            tid = cur.fetchone()[0]
            title_ids.append(tid)
            
            selected_genres = random.sample(genre_ids, k=random.randint(2, 4))
            for gid in selected_genres:
                cur.execute(
                    "INSERT INTO title_genres (title_id, genre_id) VALUES (%s, %s)",
                    (tid, gid)
                )
            
            selected_studios = random.sample(studio_ids, k=random.randint(1, 2))
            for sid in selected_studios:
                cur.execute("""
                    INSERT INTO title_studios (title_id, studio_id, role) 
                    VALUES (%s, %s, %s)
                """, (tid, sid, random.choice(['Production', 'Animation', 'Licensing'])))
            
            selected_authors = random.sample(author_ids, k=random.randint(1, 3))
            for aid in selected_authors:
                cur.execute("""
                    INSERT INTO title_authors (title_id, author_id, role) 
                    VALUES (%s, %s, %s)
                """, (
                    tid,
                    aid,
                    random.choice(['Original Creator', 'Director', 'Character Design', 'Screenplay'])
                ))
            
            if i % 200 == 0:
                print(f"   Создано {i} тайтлов...")
        
        print(f"   Всего создано {len(title_ids)} тайтлов")
        
        print("📚 Заполняем библиотеки пользователей...")
        library_count = 0
        
        for idx, uid in enumerate(user_ids):
            num_titles = random.randint(10, 50)
            user_titles = random.sample(title_ids, k=num_titles)
            
            for tid in user_titles:
                status = random.choices(
                    ['planned', 'watching', 'completed', 'dropped', 'on_hold'],
                    weights=[15, 25, 40, 10, 10]
                )[0]
                
                if status == 'completed':
                    progress = 100
                    score = random.randint(7, 10) 
                elif status == 'watching':
                    progress = random.randint(1, 80)
                    score = random.randint(5, 9) if random.random() > 0.5 else None
                elif status == 'dropped':
                    progress = random.randint(1, 30)
                    score = random.randint(1, 5) if random.random() > 0.3 else None
                else: 
                    progress = 0
                    score = None
                
                cur.execute("""
                    INSERT INTO user_library 
                    (user_id, title_id, status, progress, user_score, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    uid,
                    tid,
                    status,
                    progress,
                    score,
                    fake.date_time_between(start_date='-1y', end_date='now')
                ))
                
                library_count += 1
            
            if idx % 100 == 0:
                print(f"   Обработано {idx} пользователей, {library_count} записей...")
        
        print(f"   Всего загружено {library_count} записей в библиотеки")
        
        print("📝 Отзывы...")
        cur.execute("""
            SELECT ul.user_id, ul.title_id 
            FROM user_library ul
            WHERE ul.status = 'completed' AND ul.user_score IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 5000
        """)
        review_candidates = cur.fetchall()
        
        for idx, (uid, tid) in enumerate(review_candidates):
            if random.random() > 0.6:
                created_at = fake.date_time_between(start_date='-6m', end_date='now')
                
                cur.execute("""
                    INSERT INTO reviews (user_id, title_id, content, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    uid,
                    tid,
                    '\n\n'.join([fake.paragraph() for _ in range(2)]),
                    created_at,
                    created_at 
                ))
            
            if idx % 1000 == 0:
                print(f"   Создано {idx} отзывов...")
        
        print("⚠️  Жалобы...")
        cur.execute("SELECT id FROM reviews LIMIT 500")
        review_ids = [r[0] for r in cur.fetchall()]
        
        cur.execute("SELECT id FROM users WHERE is_active = TRUE LIMIT 300")
        active_user_ids = [r[0] for r in cur.fetchall()]
        
        for i in range(300):
            reporter_id = random.choice(active_user_ids)
            entity_type = random.choice(['review', 'user_avatar'])
            
            if entity_type == 'review' and review_ids:
                entity_id = random.choice(review_ids)
                cur.execute("SELECT user_id FROM reviews WHERE id = %s", (entity_id,))
                result = cur.fetchone()
                reported_id = result[0] if result else random.choice(active_user_ids)
            else: 
                reported_id = random.choice([uid for uid in active_user_ids if uid != reporter_id])
                entity_id = reported_id
            
            status = random.choice(['pending', 'investigating', 'resolved', 'rejected'])
            
            if status == 'resolved':
                resolution = random.choice(['content_removed', 'user_warned', 'user_banned', 'no_violation'])
                resolved_at = fake.date_time_between(start_date='-2m', end_date='now')
                resolved_by = random.choice(active_user_ids[:50])  
                moderator_comment = fake.text(max_nb_chars=100)
            else:
                resolution = None
                resolved_at = None
                resolved_by = None
                moderator_comment = None
            
            cur.execute("""
                INSERT INTO reports (
                    reporter_user_id, entity_type, entity_id, reported_user_id, reason,
                    description, evidence_url, status, resolution, moderator_comment,
                    created_at, resolved_at, resolved_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                reporter_id,
                entity_type,
                entity_id,
                reported_id,
                random.choice(['spam', 'offensive_language', 'inappropriate_content', 'spoiler', 'other']),
                fake.text(max_nb_chars=200),
                f'https://example.com/evidence/{random.randint(1, 1000)}.png' if random.random() > 0.5 else None,
                status,
                resolution,
                moderator_comment,
                fake.date_time_between(start_date='-6m', end_date='now'),
                resolved_at,
                resolved_by
            ))
        
        print("   Создано 300 жалоб")
        
        print("📊 Аудит-лог...")
        admin_ids = user_ids[:10]
        moderator_ids = user_ids[10:30]
        
        for i in range(500):
            if random.random() < 0.2:
                user_id = None
                user_role = 'system'
            else:
                if random.random() < 0.1: 
                    user_id = random.choice(admin_ids)
                    user_role = 'admin'
                elif random.random() < 0.3: 
                    user_id = random.choice(moderator_ids)
                    user_role = 'moderator'
                else:  
                    user_id = random.choice(user_ids[100:]) 
                    user_role = 'user'
            
            entity_type = random.choice(['title', 'review', 'user', 'studio', 'genre', 'author'])
            entity_id = random.randint(1, 1000)
            
            changes = {
                'old_value': fake.word(),
                'new_value': fake.word(),
                'changed_fields': random.sample(['title', 'status', 'description', 'rating'], 2),
                'timestamp': datetime.now().isoformat()
            }
            
            cur.execute("""
                INSERT INTO audit_log (
                    user_id, user_role, action_type, entity_type, entity_id, 
                    description, changes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                user_role,
                random.choice(['catalog_update', 'catalog_delete', 'review_create', 
                              'review_update', 'user_block', 'system_event']),
                entity_type,
                entity_id,
                fake.sentence(),
                json.dumps(changes, ensure_ascii=False)  
            ))
        
        print("   Создано 500 записей аудит-лога")
        
        
        conn.commit()
        print("✅ База успешно заполнена!")
        
        print("\n📊 Статистика:")
        tables = ['users', 'titles', 'user_library', 'reviews', 'reports', 'audit_log']
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table}: {cur.fetchone()[0]:,} записей")
        
        print("\n📈 Дополнительная статистика:")
        cur.execute("SELECT COUNT(*) FROM titles WHERE type = 'anime'")
        print(f"  Аниме: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM titles WHERE type = 'manga'")
        print(f"  Манга: {cur.fetchone()[0]}")
        
        cur.execute("SELECT AVG(average_rating) FROM titles WHERE vote_count > 0")
        avg_rating = cur.fetchone()[0]
        print(f"  Средний рейтинг всех тайтлов: {avg_rating if avg_rating else 'нет оценок'}")

        cur.execute("SELECT AVG(user_score) FROM user_library WHERE user_score IS NOT NULL")
        avg_user_score = cur.fetchone()[0]
        print(f"  Средняя оценка пользователей: {avg_user_score if avg_user_score else 'нет оценок'}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_seed()
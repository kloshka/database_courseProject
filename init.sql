-- =============================================
-- СИСТЕМА УПРАВЛЕНИЯ БИБЛИОТЕКОЙ АНИМЕ И МАНГИ
-- Всего: 15 таблиц
-- =============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto; 

-- =============================================
-- 1. ТАБЛИЦА: users
-- =============================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(255) DEFAULT '/default-avatar.png',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE users IS 'Учетные записи пользователей системы';

-- =============================================
-- 2. ТАБЛИЦА: user_profiles
-- =============================================
CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY,
    birth_date DATE,
    about_text TEXT,
    
    CONSTRAINT fk_user_profile_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE user_profiles IS 'Профили пользователей (расширенная информация)';

-- =============================================
-- 3. ТАБЛИЦА: titles
-- =============================================
CREATE TABLE titles (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL CHECK (type IN ('anime', 'manga')),
    canonical_title VARCHAR(255) NOT NULL,
    russian_title VARCHAR(255),
    synopsis TEXT,
    poster_url VARCHAR(255),
    
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('announced', 'ongoing', 'released', 'discontinued')),
    
    start_date DATE,
    end_date DATE,
    
    episodes_count INTEGER,
    volumes_count INTEGER,
    chapters_count INTEGER,
    
    total_score BIGINT DEFAULT 0,
    vote_count INTEGER DEFAULT 0,
    average_rating DECIMAL(4,2)
);

ALTER TABLE titles ADD CONSTRAINT unique_title_type UNIQUE (canonical_title, type);

ALTER TABLE titles ADD CONSTRAINT chk_title_type_consistency CHECK (
    (type = 'anime' AND volumes_count IS NULL AND chapters_count IS NULL) OR
    (type = 'manga' AND episodes_count IS NULL)
);

COMMENT ON TABLE titles IS 'Каталог аниме и манги (основная таблица системы)';

-- =============================================
-- 4. ТАБЛИЦА: studios
-- =============================================
CREATE TABLE studios (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL 
        CHECK (type IN ('studio', 'publisher')),
    country VARCHAR(50),
    founded_date DATE
);

COMMENT ON TABLE studios IS 'Студии анимации и издательства манги';

-- =============================================
-- 5. ТАБЛИЦА: genres
-- =============================================
CREATE TABLE genres (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

COMMENT ON TABLE genres IS 'Жанры для классификации аниме и манги';

-- =============================================
-- 6. ТАБЛИЦА: authors
-- =============================================
CREATE TABLE authors (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(50)
);

COMMENT ON TABLE authors IS 'Авторы, режиссеры и сценаристы';

-- =============================================
-- 7. ТАБЛИЦА: title_studios
-- =============================================
CREATE TABLE title_studios (
    title_id BIGINT NOT NULL,
    studio_id BIGINT NOT NULL,
    role VARCHAR(100),
    
    PRIMARY KEY (title_id, studio_id),
    CONSTRAINT fk_title_studios_title 
        FOREIGN KEY (title_id) 
        REFERENCES titles(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_title_studios_studio 
        FOREIGN KEY (studio_id) 
        REFERENCES studios(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE title_studios IS 'Связь многие-ко-многим между тайтлами и студиями';

-- =============================================
-- 8. ТАБЛИЦА: title_genres
-- =============================================
CREATE TABLE title_genres (
    title_id BIGINT NOT NULL,
    genre_id BIGINT NOT NULL,
    
    PRIMARY KEY (title_id, genre_id),
    CONSTRAINT fk_title_genres_title 
        FOREIGN KEY (title_id) 
        REFERENCES titles(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_title_genres_genre 
        FOREIGN KEY (genre_id) 
        REFERENCES genres(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE title_genres IS 'Связь многие-ко-многим между тайтлами и жанры';

-- =============================================
-- 9. ТАБЛИЦА: title_authors
-- =============================================
CREATE TABLE title_authors (
    title_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    role VARCHAR(100),
    
    PRIMARY KEY (title_id, author_id),
    CONSTRAINT fk_title_authors_title 
        FOREIGN KEY (title_id) 
        REFERENCES titles(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_title_authors_author 
        FOREIGN KEY (author_id) 
        REFERENCES authors(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE title_authors IS 'Связь многие-ко-многим между тайтлами и авторами';

-- =============================================
-- 10. ТАБЛИЦА: user_library
-- =============================================
CREATE TABLE user_library (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title_id BIGINT NOT NULL,
    
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('planned', 'watching', 'completed', 'dropped', 'on_hold')),
    
    progress INTEGER DEFAULT 0,
    CONSTRAINT progress_non_negative CHECK (progress >= 0),
    
    user_score INTEGER 
        CHECK (user_score BETWEEN 1 AND 10 OR user_score IS NULL),
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (user_id, title_id),
    CONSTRAINT fk_user_library_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_user_library_title 
        FOREIGN KEY (title_id) 
        REFERENCES titles(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE user_library IS 'Библиотека пользователей - основная таблица активности';

-- =============================================
-- 11. ТАБЛИЦА: reviews
-- =============================================
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (user_id, title_id),
    CONSTRAINT fk_reviews_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_reviews_title 
        FOREIGN KEY (title_id) 
        REFERENCES titles(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE reviews IS 'Рецензии пользователей на тайтлы';

-- =============================================
-- 12. ТАБЛИЦА: audit_log
-- =============================================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP DEFAULT clock_timestamp(),
    
    user_id BIGINT,
    user_role VARCHAR(20) NOT NULL 
        CHECK (user_role IN ('admin', 'moderator', 'user', 'system')),
    
    action_type VARCHAR(50) NOT NULL 
        CHECK (action_type IN (
            'catalog_create', 'catalog_update', 'catalog_delete',
            'review_create', 'review_update', 'review_delete',
            'library_add', 'library_update', 'library_delete',
            'user_create', 'user_update', 'user_delete', 
            'user_block', 'user_unblock',
            'system_event',
            'report_created', 'report_resolved'
        )),
    
    entity_type VARCHAR(20) NOT NULL 
        CHECK (entity_type IN ( 'title', 'review', 'user', 'studio', 
            'genre', 'author', 'user_library', 'report')),
    
    entity_id BIGINT NOT NULL,
    description VARCHAR(500) NOT NULL,
    changes JSONB,
    
    CONSTRAINT fk_audit_log_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL
);

COMMENT ON TABLE audit_log IS 'Журнал аудита для отслеживания важных изменений в системе';

-- =============================================
-- 13. ТАБЛИЦА: reports
-- =============================================
CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    reporter_user_id BIGINT NOT NULL,
    entity_type VARCHAR(20) NOT NULL 
        CHECK (entity_type IN ('review', 'user_avatar')),
    
    entity_id BIGINT NOT NULL,
    reported_user_id BIGINT NOT NULL,
    
    reason VARCHAR(30) NOT NULL 
        CHECK (reason IN (
            'spam', 'offensive_language', 'hate_speech',
            'inappropriate_content', 'spoiler', 
            'copyright_violation', 'other'
        )),
    
    description TEXT,
    evidence_url VARCHAR(255),
    
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('pending', 'investigating', 'resolved', 'rejected'))
        DEFAULT 'pending',
    
    resolution VARCHAR(20) 
        CHECK (resolution IN (
            'content_removed', 'user_warned', 'user_banned',
            'no_violation', 'duplicate'
        )),
    
    moderator_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by BIGINT,
    
    CONSTRAINT fk_reports_reporter 
        FOREIGN KEY (reporter_user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_reports_reported 
        FOREIGN KEY (reported_user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_reports_resolved_by 
        FOREIGN KEY (resolved_by) 
        REFERENCES users(id) 
        ON DELETE SET NULL
);

COMMENT ON TABLE reports IS 'Жалобы пользователей на контент (система модерации)';

-- =============================================
-- 14. ТАБЛИЦА: import_batches
-- =============================================
CREATE TABLE import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('title', 'user', 'review')),
    total_records INTEGER NOT NULL,
    successful_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    config JSONB NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    skipped_records INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    status VARCHAR(30) NOT NULL CHECK (status IN ('processing', 'completed', 'failed', 'partial_success', 'completed_with_skipped'))
);

COMMENT ON TABLE import_batches IS 'Метаинформация о партиях импорта';

-- =============================================
-- 15. ТАБЛИЦА: import_errors
-- =============================================
CREATE TABLE import_errors (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id UUID NOT NULL,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('title', 'user', 'review')),
    entity_data JSONB NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_import_errors_batch 
        FOREIGN KEY (import_batch_id) 
        REFERENCES import_batches(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE import_errors IS 'Логирование ошибок при батчевом импорте';

-- =============================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- =============================================

-- Индексы для таблицы titles
CREATE INDEX idx_titles_status ON titles(status);
CREATE INDEX idx_titles_rating ON titles(average_rating DESC);
CREATE INDEX idx_titles_start_date ON titles(start_date);
CREATE INDEX idx_titles_canonical_lower_btree ON titles (lower(canonical_title));
CREATE INDEX idx_titles_canonical_trgm_gin ON titles USING gin (canonical_title gin_trgm_ops);
CREATE INDEX idx_titles_russian_trgm_gin ON titles USING gin (russian_title gin_trgm_ops);

-- Индекс для audit_log
CREATE INDEX idx_audit_log_timestamp ON audit_log(event_timestamp DESC);

-- Индексы для импорта
CREATE INDEX idx_import_batches_created ON import_batches(started_at DESC);
CREATE INDEX idx_import_errors_batch ON import_errors(import_batch_id);
CREATE INDEX idx_import_errors_type ON import_errors(error_type);

-- =============================================
-- ФУНКЦИИ
-- =============================================

CREATE OR REPLACE FUNCTION fn_update_library_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = clock_timestamp();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_update_title_rating()
RETURNS TRIGGER AS $$
DECLARE
    v_title_id BIGINT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_title_id := OLD.title_id;
    ELSE
        v_title_id := NEW.title_id;
    END IF;
    
    IF TG_OP = 'INSERT' AND NEW.user_score IS NOT NULL THEN
        UPDATE titles 
        SET 
            total_score = total_score + NEW.user_score,
            vote_count = vote_count + 1
        WHERE id = NEW.title_id;
    
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.user_score IS NULL AND NEW.user_score IS NOT NULL THEN
            UPDATE titles 
            SET 
                total_score = total_score + NEW.user_score,
                vote_count = vote_count + 1
            WHERE id = NEW.title_id;
        
        ELSIF OLD.user_score IS NOT NULL AND NEW.user_score IS NOT NULL THEN
            UPDATE titles 
            SET total_score = total_score - OLD.user_score + NEW.user_score
            WHERE id = NEW.title_id;
        
        ELSIF OLD.user_score IS NOT NULL AND NEW.user_score IS NULL THEN
            UPDATE titles 
            SET 
                total_score = total_score - OLD.user_score,
                vote_count = vote_count - 1
            WHERE id = NEW.title_id;
        END IF;
    
    ELSIF TG_OP = 'DELETE' AND OLD.user_score IS NOT NULL THEN
        UPDATE titles 
        SET 
            total_score = total_score - OLD.user_score,
            vote_count = vote_count - 1
        WHERE id = OLD.title_id;
    END IF;
    
    IF v_title_id IS NOT NULL THEN
        UPDATE titles 
        SET average_rating = 
            CASE 
                WHEN vote_count > 0 THEN ROUND(total_score::DECIMAL / vote_count, 2)
                ELSE NULL
            END
        WHERE id = v_title_id;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION log_title_deletion()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id,
        user_role, 
        action_type, 
        entity_type, 
        entity_id, 
        description, 
        changes
    ) VALUES (
        NULL,
        'system',
        'catalog_delete',
        'title',
        OLD.id,
        'Удален тайтл: ' || OLD.canonical_title,
        jsonb_build_object(
            'old_data', row_to_json(OLD),
            'deleted_at', clock_timestamp(),
            'deleted_by', current_user
        )
    );
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION audit_review_update()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id, 
        user_role, 
        action_type, 
        entity_type, 
        entity_id, 
        description, 
        changes
    ) VALUES (
        NEW.user_id,
        'user',
        'review_update', 
        'review', 
        NEW.id, 
        'Отредактирована рецензия на тайтл #' || NEW.title_id,
        jsonb_build_object(
            'old_content', OLD.content,
            'new_content', NEW.content,
            'changed_at', NOW()
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION audit_library_add()
RETURNS TRIGGER AS $$
DECLARE
    v_title_name VARCHAR;
BEGIN
    SELECT canonical_title INTO v_title_name
    FROM titles WHERE id = NEW.title_id;
    
    INSERT INTO audit_log (
        user_id, 
        user_role, 
        action_type, 
        entity_type, 
        entity_id, 
        description, 
        changes
    ) VALUES (
        NEW.user_id,
        'user',
        'library_add',
        'user_library', 
        NEW.id,
        'Добавлен тайтл "' || COALESCE(v_title_name, 'Unknown') || '" в библиотеку',
        jsonb_build_object(
            'title_id', NEW.title_id,
            'status', NEW.status,
            'score', NEW.user_score,
            'added_at', NOW()
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_user_rank(p_user_id BIGINT)
RETURNS VARCHAR AS $$
DECLARE
    v_completed_count INTEGER;
    v_user_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM users WHERE id = p_user_id) INTO v_user_exists;
    IF NOT v_user_exists THEN
        RETURN 'Пользователь не найден';
    END IF;
    
    SELECT COUNT(*) INTO v_completed_count
    FROM user_library
    WHERE user_id = p_user_id AND status = 'completed';
    
    IF v_completed_count < 10 THEN
        RETURN 'Новичок';
    ELSIF v_completed_count < 50 THEN
        RETURN 'Любитель';
    ELSIF v_completed_count < 100 THEN
        RETURN 'Опытный';
    ELSE
        RETURN 'Отаку-сенсей';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- ТРИГГЕРЫ 
-- =============================================

CREATE OR REPLACE TRIGGER trg_update_library_timestamp
BEFORE UPDATE ON user_library
FOR EACH ROW
EXECUTE FUNCTION fn_update_library_timestamp();

CREATE OR REPLACE TRIGGER trg_update_review_timestamp
BEFORE INSERT OR UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION fn_update_timestamp();

CREATE OR REPLACE TRIGGER trg_calculate_rating
AFTER INSERT OR UPDATE OF user_score OR DELETE ON user_library
FOR EACH ROW
EXECUTE FUNCTION fn_update_title_rating();

CREATE OR REPLACE TRIGGER trg_audit_title_delete
BEFORE DELETE ON titles
FOR EACH ROW
EXECUTE FUNCTION log_title_deletion();

CREATE OR REPLACE TRIGGER trg_audit_review_update
AFTER UPDATE ON reviews
FOR EACH ROW
WHEN (OLD.content IS DISTINCT FROM NEW.content)
EXECUTE FUNCTION audit_review_update();

CREATE OR REPLACE TRIGGER trg_audit_library_add
AFTER INSERT ON user_library
FOR EACH ROW
EXECUTE FUNCTION audit_library_add();

-- =============================================
-- ПРЕДСТАВЛЕНИЯ (VIEW)
-- =============================================

CREATE OR REPLACE VIEW view_top_anime AS
SELECT 
    id,
    canonical_title AS title,
    average_rating,
    vote_count,
    poster_url
FROM titles
WHERE type = 'anime' AND status = 'released'
ORDER BY average_rating DESC NULLS LAST, vote_count DESC;

CREATE OR REPLACE VIEW view_user_stats AS
SELECT
    u.id,
    u.username,
    COUNT(ul.id) AS total_titles,
    COUNT(CASE WHEN ul.status = 'completed' THEN 1 END) AS completed_count,
    COALESCE(ROUND(AVG(ul.user_score), 2), 0) AS avg_score,
    MAX(ul.last_updated) AS last_active
FROM users u
LEFT JOIN user_library ul ON u.id = ul.user_id
GROUP BY u.id, u.username;

CREATE OR REPLACE VIEW view_genre_popularity AS
SELECT 
    g.name AS genre,
    COUNT(tg.title_id) AS titles_count,
    ROUND(AVG(t.average_rating), 2) AS genre_avg_rating
FROM genres g
JOIN title_genres tg ON g.id = tg.genre_id
JOIN titles t ON tg.title_id = t.id
GROUP BY g.id, g.name
ORDER BY titles_count DESC;
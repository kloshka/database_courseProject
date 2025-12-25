# Anime & Manga Library Management System — Курсовой проект по базам данных

## Требования

* Docker и Docker Compose (рекомендуется)
* Python 3.11 и pip (если планируете запускать приложение локально без контейнера)

## Настройка

### Склонируйте репозиторий

```bash
git clone https://github.com/kloshka/database_courseProject.git
cd database_courseProject
```

### Создайте в папке проекта файл .env.docker и заполните его данными вашего подключения, например:

```env
DB_NAME=animedb
DB_USER=admin
DB_PASSWORD=your_strong_password
DB_HOST=db
DB_PORT=5432
```

### Для запуска в docker, находясь в корневой папке проекта выполните команду:

```bash
docker compose up -d --build
```

После запуска контейнера проект будет доступен по адресу [http://localhost:8000/docs](http://localhost:8000/docs)

### Для локального запуска, находясь в корневой папке проекта выполните команду:

```bash
docker compose up -d db
```

После запуска базы данных установите необходимые зависимости приложения:

```bash
pip install -r requirements.txt
```

Наконец, выполните запуск сервера:

```bash
uvicorn app.main:app --reload
```

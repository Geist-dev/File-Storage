
# 📁 File Storage (FastAPI + SQLite + Vanilla JS)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?logo=fastapi)
![SQLite](https://img.shields.io/badge/SQLite-DB-003B57?logo=sqlite)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/status-active-success)

Маленький, но полноценный pet-project на Python/JS — **личное файловое хранилище** с аутентификацией, drag&drop загрузкой, тегами и корзиной.  

## ✨ Возможности
- 🔐 **Закрытый доступ** — без входа не видно ни одного файла  
- 📝 **Регистрация и вход** (JWT токены)  
- 🚫 **Валидация пароля** (и на фронте, и на бэке)  
- 📤 **Загрузка файлов**:
  - Drag & Drop
  - Поддержка подпапок (`work/reports`)
  - Ограничение по типам (`.jpg, .png, .pdf...`) и размеру (по умолчанию 50 MB)  
- 🏷️ **Теги-чипсы** для организации файлов  
- 🖼 **Предпросмотр** изображений + миниатюры (Pillow)  
- 🗑 **Корзина** и восстановление файлов  
- 📥 **Скачивание файлов**  
- 🚪 **Кнопка выхода** и сброс сессии  

## 🛠 Технологии
**Backend**:
- [FastAPI](https://fastapi.tiangolo.com/)  
- [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite  
- [Passlib](https://passlib.readthedocs.io/) (bcrypt)  
- [Pillow](https://pillow.readthedocs.io/) (миниатюры)  

**Frontend**:
- Чистый Vanilla JS + HTML + CSS  
- Простая SPA-логика без фреймворков  

## 🚀 Быстрый запуск (One-Click)
1. Клонируй репозиторий:
   ```bash
   git clone https://github.com/Geist-dev/File-Storage.git
   cd File-Storage
   ```
2. Запусти скрипт:
   ```bash
   python run_oneclick.py
   ```
3. Откроются два сервиса:
   - 🌐 Frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)  
   - ⚙️ Backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)  

*(На Windows можно запускать через PyCharm: правый клик по `run_oneclick.py` → Run)*

## ⚙️ Конфигурация
Все параметры в **backend/.env**:
```env
APP_NAME=FileStoragePython
APP_PORT=8000
JWT_SECRET=change_me
JWT_EXPIRES_MIN=10080
STORAGE_DIR=storage
DATABASE_URL=sqlite:///./data.db
MAX_UPLOAD_MB=50
ALLOWED_MIME=image/jpeg,image/png,image/webp,application/pdf,text/plain
```

## 📸 Скриншоты
> _Сюда можно вставить скрины интерфейса: форма входа, загрузка файлов, список, корзина._

![UI example](https://via.placeholder.com/900x450.png?text=FileStorage+UI+Example)

## 🤝 Идеи для улучшений
- ✅ Массовые операции (удаление/восстановление нескольких файлов)  
- ✅ Поддержка шаринга ссылкой (публичные файлы)  
- ✅ Тёмная/светлая тема  
- ✅ Docker-сборка  

## 📜 Лицензия
MIT — используй свободно.

---

⭐ Если проект понравился — ставь звезду и форкай!

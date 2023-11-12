# Используйте официальный образ Python 3.9 как базовый
FROM python:3.9

# Установите рабочую директорию в контейнере
WORKDIR /app

# Установка зависимостей для OpenCV и очистка кэша для уменьшения размера образа
RUN apt-get update && \
    apt-get install -y libgl1-mesa-dev && \
    rm -rf /var/lib/apt/lists/*

# Обновите pip
RUN pip install --upgrade pip

# Сначала скопируйте только файл requirements.txt
COPY requirements.txt ./

# Установите зависимости из файла requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Теперь скопируйте остальные файлы
COPY . .

# Сделайте порт доступным для мира снаружи контейнера
EXPOSE 5000

# Запустите приложение при старте контейнера
CMD ["python", "app.py"]

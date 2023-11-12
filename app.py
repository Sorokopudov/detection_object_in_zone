#app.py
import logging
from flask import Flask, request, send_from_directory, render_template, redirect, url_for
import os
import zipfile
from utils import process_images_zip  # Обновленная функция


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"Upload folder exists: {os.path.exists(UPLOAD_FOLDER)}")
    logging.info(f"Result folder exists: {os.path.exists(RESULT_FOLDER)}")
    return render_template('index.html')

def extract_zip(input_zip, path):
    with zipfile.ZipFile(input_zip, 'r') as zip_ref:
        zip_ref.extractall(path)
        extracted_paths = zip_ref.namelist()
    # Возвращаем первую папку из списка (предполагаем, что она одна)
    first_directory = next((item for item in extracted_paths if item.endswith('/')), None)
    return os.path.join(path, first_directory) if first_directory else None


@app.route('/upload', methods=['POST'])
def upload_files():
    zone_file = request.files['zone_file']
    image_file = request.files['image_file']

    if not zone_file or not image_file:
        logging.warning('One of the files was not provided.')
        return 'Необходимо загрузить оба файла.', 400

    # Сохранение и извлечение зон
    zone_path = os.path.join(UPLOAD_FOLDER, 'zones.zip')
    zone_file.save(zone_path)
    zones_folder_path = extract_zip(zone_path, UPLOAD_FOLDER)

    # Сохранение и извлечение изображений
    image_path = os.path.join(UPLOAD_FOLDER, 'images.zip')
    image_file.save(image_path)
    images_folder_path = extract_zip(image_path, UPLOAD_FOLDER)

    # Проверяем, были ли найдены пути к извлеченным директориям
    if zones_folder_path is None or images_folder_path is None:
        logging.error('Failed to find extracted folders for zones or images.')
        return 'Произошла ошибка при извлечении файлов.', 500

    # Обработка изображений и получение пути к ZIP-архиву с результатами
    logging.info('Starting image processing...')
    result_zip_path = process_images_zip(images_folder_path, zones_folder_path, RESULT_FOLDER)

    if not os.path.exists(result_zip_path):
        logging.error('The result.zip file does not exist.')
        return 'Произошла ошибка при обработке файлов.', 500

    logging.info('Image processing completed successfully.')
    # Переадресация на скачивание результатов
    return redirect(url_for('download_results'))


@app.route('/download_results')
def download_results():
    result_zip = os.path.join(RESULT_FOLDER, 'result.zip')
    logging.info(f'Sending file {result_zip} to user.')
    return send_from_directory(directory=RESULT_FOLDER, path='result.zip', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

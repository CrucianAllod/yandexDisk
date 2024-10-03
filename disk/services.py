import requests
import mimetypes
import urllib.parse
import zipfile
import io
from typing import List, Tuple, Optional

API_URL = 'https://cloud-api.yandex.net/v1/disk/public/resources'

def file_list(public_key: str) -> Optional[List[dict]]:
    """
    Получает список файлов из публичной папки Яндекс.Диска.

    :param public_key: Публичный ключ для доступа к папке
    :return: Список файлов в папке или None, если произошла ошибка
    """
    url = f'{API_URL}?public_key={public_key}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('_embedded', {}).get('items', [])
    return None

def filter_files_by_type(items: List[dict], file_type: str) -> List[dict]:
    """
    Фильтрует список файлов по указанному типу.

    :param items: Список файлов
    :param file_type: Тип файлов для фильтрации ('documents' или 'images')
    :return: Отфильтрованный список файлов
    """
    if file_type == 'documents':
        items = [item for item in items if item['type'] == 'file' and is_document(item['name'])]
    elif file_type == 'images':
        items = [item for item in items if item['type'] == 'file' and is_image(item['name'])]
    return items

def is_document(file_name: str) -> bool:
    """
    Проверяет, является ли файл документом.

    :param file_name: Имя файла
    :return: True, если файл является документом, иначе False
    """
    document_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type in document_types

def is_image(file_name: str) -> bool:
    """
    Проверяет, является ли файл изображением.

    :param file_name: Имя файла
    :return: True, если файл является изображением, иначе False
    """
    image_types = ['image/jpeg', 'image/png', 'image/gif']
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type in image_types

def download_file(public_key: str, path: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Скачивает файл с Яндекс.Диска.

    :param public_key: Публичный ключ для доступа к папке
    :param path: Путь к файлу
    :return: Кортеж, содержащий содержимое файла и его имя, или (None, None), если произошла ошибка
    """
    url = f'{API_URL}/download?public_key={public_key}&path={path}'
    response = requests.get(url)
    if response.status_code == 200:
        download_url = response.json().get('href')
        file_response = requests.get(download_url)
        if file_response.status_code == 200:
            return file_response.content, path.split('/')[-1]
    return None, None

def multiple_download_files(public_key: str, paths: List[str]) -> bytes:
    """
    Скачивает несколько файлов и создает ZIP-архив.

    :param public_key: Публичный ключ для доступа к папке
    :param paths: Список путей к файлам
    :return: Содержимое ZIP-архива
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for path in paths:
            encoded_path = urllib.parse.quote(path)
            file_content, file_name = download_file(public_key, encoded_path)
            if file_content:
                zip_file.writestr(file_name, file_content)
            else:
                print(f"Не удалось загрузить файл {path}.")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
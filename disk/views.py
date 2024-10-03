from django.core.cache import cache
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
import requests
import mimetypes
import urllib.parse
import zipfile
import io
import datetime
# Импортируем mime_types для регистрации MIME-типов
import disk.mime_types


class FileListView(View):
    def get(self, request):
       return  render(request, 'disk/index.html')

    def post(self, request):
        public_key = request.POST.get('public_key')
        file_type = request.POST.get('file_type', 'all')
        cache_key = f"file_list_{public_key}"
        items = cache.get(cache_key)
        if items is None:
            url = f'https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_key}'
            response = requests.get(url)
            if response.status_code == 200:
                items = response.json().get('_embedded', {}).get('items', [])
                cache.set(cache_key, items, 300)
            else:
                return HttpResponseBadRequest('Ошибка при получении списка файлов')
            # Фильтрация файлов по типу
        if file_type == 'documents':
            items = [item for item in items if item['type'] == 'file' and self.is_document(item['name'])]
        elif file_type == 'images':
            items = [item for item in items if item['type'] == 'file' and self.is_image(item['name'])]

        return render(request, 'disk/index.html', {'items': items, 'public_key': public_key})


    def is_document(self, file_name):
        # Проверка, является ли файл документом
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

    def is_image(self, file_name):
        # Проверка, является ли файл изображением
        image_types = ['image/jpeg', 'image/png', 'image/gif']
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type in image_types

class FileDownloadView(View):
    def get(self, request):
        public_key = request.GET.get('public_key')
        path = request.GET.get('path')
        url = f'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}&path={path}'
        response = requests.get(url)
        if response.status_code == 200:
            download_url = response.json().get('href')
            file_response = requests.get(download_url)
            if file_response.status_code == 200:
                # Определяем MIME-тип файла
                file_name = path.split('/')[-1]
                mime_type, _ = mimetypes.guess_type(file_name)
                encoded_file_name = urllib.parse.quote(file_name, safe='')

                # Устанавливаем заголовки ответа
                response = HttpResponse(file_response.content, content_type=mime_type or 'application/octet-stream')
                response['Content-Disposition'] = f"attachment; filename={file_name}; filename*=UTF-8''{encoded_file_name}"
                return response
        return HttpResponseBadRequest('Ошибка при загрузке файла', status=500)


class FileMultipleDownloadView(View):
    def post(self, request):
        public_key = request.POST.get('public_key')
        paths = request.POST.getlist('files')

        if not paths:
            return HttpResponseBadRequest('Не выбрано ни одного файла.')

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for path in paths:
                encoded_path = urllib.parse.quote(path)
                url = f'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}&path={encoded_path}'
                response = requests.get(url)

                if response.status_code == 200:
                    download_url = response.json().get('href')
                    file_response = requests.get(download_url)

                    if file_response.status_code == 200:
                        file_name = path.split('/')[-1]
                        file_content = file_response.content

                        if file_content:
                            zip_file.writestr(file_name, file_content)
                        else:
                            print(f"Файл {file_name} пустой или не удалось загрузить содержимое.")
                    else:
                        print(f"Не удалось загрузить файл {path}. Статус: {file_response.status_code}")
                else:
                    print(f"Не удалось получить ссылку для скачивания для {path}. Статус: {response.status_code}")

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f"attachment; filename={datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return response
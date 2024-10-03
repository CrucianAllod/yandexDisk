from django.core.cache import cache
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
import mimetypes
import urllib.parse
import datetime
# Импортируем mime_types для регистрации MIME-типов
import disk.mime_types
from disk.services import file_list, filter_files_by_type, download_file, multiple_download_files
from typing import Optional, List


class FileListView(View):
    def get(self, request) -> HttpResponse:
        """
        Обрабатывает GET-запрос для отображения начальной страницы.

        :param request: HTTP-запрос
        :return: HTTP-ответ с рендерингом начальной страницы
        """
        return render(request, 'disk/index.html')

    def post(self, request) -> HttpResponse:
        """
        Обрабатывает POST-запрос для получения и отображения списка файлов.

        :param request: HTTP-запрос
        :return: HTTP-ответ с рендерингом страницы и списком файлов
        """
        public_key: str = request.POST.get('public_key')
        file_type: str = request.POST.get('file_type', 'all')
        cache_key: str = f"file_list_{public_key}"

        # Получаем список файлов из кэша, если доступен
        items: Optional[List[dict]] = cache.get(cache_key)
        if items is None:
            # Получаем список файлов с Яндекс.Диска
            items = file_list(public_key)
            if items is not None:
                # Сохраняем список файлов в кэш
                cache.set(cache_key, items, 3600)
            else:
                return HttpResponseBadRequest('Ошибка при получении списка файлов')

        # Фильтруем файлы по типу
        items = filter_files_by_type(items, file_type)

        return render(request, 'disk/index.html', {'items': items, 'public_key': public_key})


class FileDownloadView(View):
    def get(self, request) -> HttpResponse:
        """
        Обрабатывает GET-запрос для скачивания одного файла.

        :param request: HTTP-запрос
        :return: HTTP-ответ с содержимым файла для скачивания
        """
        public_key: str = request.GET.get('public_key')
        path: str = request.GET.get('path')
        file_content: Optional[bytes]
        file_name: Optional[str]

        file_content, file_name = download_file(public_key, path)

        if file_content:
            mime_type, _ = mimetypes.guess_type(file_name)
            encoded_file_name = urllib.parse.quote(file_name, safe='')

            response = HttpResponse(file_content, content_type=mime_type or 'application/octet-stream')
            response['Content-Disposition'] = f"attachment; filename={file_name}; filename*=UTF-8''{encoded_file_name}"
            return response

        return HttpResponseBadRequest('Ошибка при загрузке файла', status=500)


class FileMultipleDownloadView(View):
    def post(self, request) -> HttpResponse:
        """
        Обрабатывает POST-запрос для скачивания нескольких файлов в виде ZIP-архива.

        :param request: HTTP-запрос
        :return: HTTP-ответ с ZIP-архивом для скачивания
        """
        public_key: str = request.POST.get('public_key')
        paths: List[str] = request.POST.getlist('files')

        if not paths:
            return HttpResponseBadRequest('Не выбрано ни одного файла.')

        # Получаем содержимое ZIP-архива
        zip_content: bytes = multiple_download_files(public_key, paths)

        response = HttpResponse(zip_content, content_type='application/zip')
        response[
            'Content-Disposition'] = f"attachment; filename={datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        return response
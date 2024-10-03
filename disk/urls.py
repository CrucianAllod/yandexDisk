from django.urls import path
from .views import FileListView, FileDownloadView, FileMultipleDownloadView

urlpatterns = [
    path('', FileListView.as_view(), name='file_list'),
    path('download/', FileDownloadView.as_view(), name='file_download'),
    path('download_multiple/', FileMultipleDownloadView.as_view(), name='download_multiple'),
]
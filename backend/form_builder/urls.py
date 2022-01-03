from django.urls import path
from .views import FormListAPI, FormRUDAPI, ResponseOfAFormAPIView, DownloadAPIView

app_name = 'form_builder'

urlpatterns = [
    path('forms/', FormListAPI.as_view(), name="forms"),
    path('forms/<slug:slug>/', FormRUDAPI.as_view(), name="form-RUD"),
    path('responses/<slug:slug>/', ResponseOfAFormAPIView.as_view(), name='response'),
    path('export-responses/<slug:slug>/', DownloadAPIView.as_view(), name='export')
]

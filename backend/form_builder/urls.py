from django.urls import path
from .views import FormListAPI, FormRUDAPI

app_name = 'form_builder'

urlpatterns = [
    path('forms/', FormListAPI.as_view(), name='forms'),
    path('forms/<slug:slug>/', FormRUDAPI.as_view(), name='form-RUD'),
]

from django.urls import path
from .views import FormListAPI, FormRUDAPI, ResponseListAPI, ResponseAPIView

app_name = 'form_builder'

urlpatterns = [
    path('forms/', FormListAPI.as_view(), name='forms'),
    path('forms/<slug:slug>/', FormRUDAPI.as_view(), name='form-RUD'),
    path('responses/', ResponseListAPI.as_view(), name="responses"),
    path('responses/<slug:slug>/', ResponseAPIView.as_view(), name="form-responses"),
]

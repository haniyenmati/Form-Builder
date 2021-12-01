from django.urls import path
from .views import RegisterAPIView, LogoutAPIView
from rest_framework.authtoken import views


app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', views.obtain_auth_token, name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
]

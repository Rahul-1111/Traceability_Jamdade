from django.urls import path
from . import views

urlpatterns = [
    path('', views.combined_page, name='combined_page'),
    path('generate_qr_codes/', views.generate_qr_codes, name='generate_qr_codes'),
    path('fetch_torque_data/', views.fetch_torque_data, name='fetch_torque_data'),
]

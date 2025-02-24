from django.urls import path
from .views import plc_status, generate_qr_code_view, fetch_torque_data, combined_page

urlpatterns = [
    path('', combined_page, name='combined_page'),
    path('plc_statuses/', plc_status, name='plc_statuses'),  # ✅ Ensure this matches JS
    path('generate_qr_code/', generate_qr_code_view, name='generate_qr_codes'),  # ✅ Ensure this matches JS
    path('fetch_torque_data/', fetch_torque_data, name='fetch_torque_data'),  # ✅ Ensure this matches JS
]

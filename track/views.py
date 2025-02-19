from django.shortcuts import render
from django.http import JsonResponse
from .models import TraceabilityData
import logging
from .qr_utils import generate_qr_code  # ✅ Using latest QR code function
import random
import datetime

logger = logging.getLogger(__name__)

# ✅ Render the main page
def combined_page(request):
    return render(request, 'track/combined_page.html')

# View to handle QR code generation# View to handle QR code generation
def generate_qr_code_view(request):
    if request.method == "POST":
        prefix = request.POST.get("prefix")  # ✅ Get selected prefix
        serial_number = random.randint(10000, 99999)  # ✅ Generate unique 5-digit serial

        if not prefix:
            return JsonResponse({"error": "Prefix is required"}, status=400)

        try:
            response_message = generate_qr_code(prefix, serial_number)
            return JsonResponse({"message": response_message, "generated_code": f"{prefix}-{datetime.datetime.now().strftime('%d%m%y')}-{serial_number}"})

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)

# ✅ Fetch torque data as JSON
def fetch_torque_data(request):
    if request.method == "GET":
        data = list(TraceabilityData.objects.values())  # ✅ Fetch as list of dicts
        return JsonResponse({"data": data})  # ✅ Removed extra `,`

from django.shortcuts import render
from django.http import JsonResponse
from .models import TraceabilityData
import logging
from .qr_utils import generate_qr_code  # ✅ Using latest QR code function

logger = logging.getLogger(__name__)

# View for rendering the combined page
def combined_page(request):
    return render(request, 'track/combined_page.html')

# View to handle QR code generation
def generate_qr_code_view(request):
    if request.method == "POST":
        serial_number = request.POST.get("serial_number")

        if not serial_number:
            return JsonResponse({"error": "Serial number is required"}, status=400)

        try:
            serial_number = int(serial_number)
            if serial_number <= 0:
                return JsonResponse({"error": "Serial number must be a positive integer"}, status=400)

            # ✅ Generate and print a single QR code
            response_message = generate_qr_code(serial_number)

            return JsonResponse({"message": response_message})

        except ValueError:
            return JsonResponse({"error": "Invalid serial number. Please enter a valid number."}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)

# API endpoint to fetch torque data as JSON
def fetch_torque_data(request):
    if request.method == "GET":
        data = list(TraceabilityData.objects.values())  # Fetch all data as a list of dictionaries
        return JsonResponse({"data": data})

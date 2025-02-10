from django.shortcuts import render
from django.http import JsonResponse
from .models import TraceabilityData
import logging
from .qr_utils import generate_qr_codes_batch

logger = logging.getLogger(__name__)

# View for rendering the combined page
def combined_page(request):
    return render(request, 'track/combined_page.html')

# View to handle QR code generation
lot_serial_tracker = {}

def generate_qr_codes(request):
    if request.method == "POST":
        lot_number = request.POST.get("lot_number")

        if not lot_number:
            return JsonResponse({"error": "Lot number is required"}, status=400)

        try:
            lot_number = int(lot_number)
            if lot_number <= 0:
                return JsonResponse({"error": "Lot number must be a positive integer"}, status=400)

            # Generate and print **only one** QR code
            response_message = generate_qr_codes_batch(lot_number)

            return JsonResponse({"message": response_message})

        except ValueError:
            return JsonResponse({"error": "Invalid lot number. Please enter a number."}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)

# API endpoint to fetch torque data as JSON
def fetch_torque_data(request):
    if request.method == "GET":
        data = list(TraceabilityData.objects.values())  # Fetch all data as a list of dictionaries
        return JsonResponse({"data": data})

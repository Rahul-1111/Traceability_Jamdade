from django.contrib import admin
from .models import TraceabilityData

class TraceabilityDataAdmin(admin.ModelAdmin):
    list_display = (
        'sr_no', 'part_number', 'date', 'time', 'shift',
        'st1_result', 'st2_result', 'st3_result', 'st4_result', 'st5_result',
        'st6_result', 'st7_result', 'st8_result'
    )
    list_filter = ('date', 'shift', 'st1_result', 'st2_result', 'st3_result', 'st4_result', 
                   'st5_result', 'st6_result', 'st7_result', 'st8_result')
    search_fields = ('part_number', 'date')
    ordering = ('date',)
    list_per_page = 25

admin.site.site_header = "Traceability Management System"
admin.site.site_title = "Traceability Admin Panel"
admin.site.index_title = "Welcome to the Traceability Dashboard"

admin.site.register(TraceabilityData, TraceabilityDataAdmin)

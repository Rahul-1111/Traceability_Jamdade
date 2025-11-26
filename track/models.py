from django.db import models

class TraceabilityData(models.Model):
    sr_no = models.AutoField(primary_key=True)  # Serial Number (Primary Key)
    part_number = models.CharField(max_length=100, unique=True)  # QR Code remove -    , unique=True
    date = models.DateField()  # Date of entry
    time = models.TimeField()  # Time of entry
    shift = models.CharField(max_length=10, null=True, blank=True)  # Shift (e.g., A, B, C)
    st1_time = models.TimeField(null=True, blank=True)
    st1_result = models.CharField(max_length=10, null=True, blank=True)  # Station 1 Result
    st2_time = models.TimeField(null=True, blank=True)
    st2_result = models.CharField(max_length=10, null=True, blank=True)  # Station 2 Result
    st3_time = models.TimeField(null=True, blank=True)
    st3_result = models.CharField(max_length=10, null=True, blank=True)  # Station 3 Result
    st4_time = models.TimeField(null=True, blank=True)
    st4_result = models.CharField(max_length=10, null=True, blank=True)  # Station 4 Result
    st5_time = models.TimeField(null=True, blank=True)
    st5_result = models.CharField(max_length=10, null=True, blank=True)  # Station 5 Result
    st6_time = models.TimeField(null=True, blank=True)
    st6_result = models.CharField(max_length=10, null=True, blank=True)  # Station 6 Result
    st7_time = models.TimeField(null=True, blank=True)
    st7_result = models.CharField(max_length=10, null=True, blank=True)  # Station 7 Result
    st8_time = models.TimeField(null=True, blank=True)
    st8_result = models.CharField(max_length=10, null=True, blank=True)  # Station 8 Result
    st9_time = models.TimeField(null=True, blank=True)
    st9_result = models.CharField(max_length=10, null=True, blank=True)  # Station 7 Result
    st10_time = models.TimeField(null=True, blank=True)
    st10_result = models.CharField(max_length=10, null=True, blank=True)  # Station 8 Result

    def __str__(self):
        return f"{self.sr_no} - {self.part_number}"

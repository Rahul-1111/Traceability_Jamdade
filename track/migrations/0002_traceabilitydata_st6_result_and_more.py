# Generated by Django 4.2.18 on 2025-02-20 10:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("track", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="traceabilitydata",
            name="st6_result",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="traceabilitydata",
            name="st7_result",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="traceabilitydata",
            name="st8_result",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

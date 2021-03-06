# Generated by Django 3.1.8 on 2021-04-11 18:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("turtle_shell", "0002_auto_20210411_1045"),
    ]

    operations = [
        migrations.AddField(
            model_name="executionresult",
            name="user",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name="executionresult",
            name="error_json",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="executionresult",
            name="output_json",
            field=models.JSONField(default=dict),
        ),
    ]

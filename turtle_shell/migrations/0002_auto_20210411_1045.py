# Generated by Django 3.1.8 on 2021-04-11 17:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("turtle_shell", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="executionresult",
            name="error_json",
            field=models.JSONField(default=None),
        ),
        migrations.AlterField(
            model_name="executionresult",
            name="func_name",
            field=models.CharField(editable=False, max_length=512),
        ),
        migrations.AlterField(
            model_name="executionresult",
            name="output_json",
            field=models.JSONField(default=None),
        ),
        migrations.AlterField(
            model_name="executionresult",
            name="status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("RUNNING", "Running"),
                    ("DONE", "Done"),
                    ("ERRORED", "Errored"),
                    ("JSON_ERROR", "Result could not be coerced to JSON"),
                ],
                default="CREATED",
                max_length=10,
            ),
        ),
    ]

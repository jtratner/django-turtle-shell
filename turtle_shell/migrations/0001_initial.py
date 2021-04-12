# Generated by Django 3.1.8 on 2021-04-11 16:41

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutionResult',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('func_name', models.CharField(max_length=512)),
                ('input_json', models.JSONField()),
                ('output_json', models.JSONField()),
                ('status', models.CharField(choices=[('CREATED', 'Created'), ('RUNNING', 'Running'), ('DONE', 'Done'), ('ERRORED', 'Errored')], default='CREATED', max_length=10)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
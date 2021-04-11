from django.db import models
import uuid



class ExecutionResult(models.Model):
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    func_name = models.CharField(max_length=512)
    input_json = models.JSONField()
    output_json = models.JSONField()

    class ExecutionStatus(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        RUNNING = 'RUNNING', 'Running'
        DONE = 'DONE', 'Done'
        ERRORED = 'ERRORED', 'Errored'

    status = models.CharField(max_length=10, choices=ExecutionStatus.choices,
            default=ExecutionStatus.CREATED)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


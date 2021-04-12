from django.db import models, transaction
from django.urls import reverse
from django.conf import settings
from turtle_shell import utils
import uuid
import cattr
import json

class CaughtException(Exception):
    """An exception that was caught and saved. Generally don't need to rollback transaction with
    this one :)"""
    def __init__(self, exc, message):
        self.exc = exc
        super().__init__(message)


class ResultJSONEncodeException(CaughtException):
    """Exceptions for when we cannot save result as actual JSON field :("""



class ExecutionResult(models.Model):
    FIELDS_TO_SHOW_IN_LIST = [("func_name", "Function"),  ("created", "Created"), ("user", "User"),
            ("status", "Status")]
    uuid = models.UUIDField(primary_key=True, unique=True, editable=False, default=uuid.uuid4)
    func_name = models.CharField(max_length=512, editable=False)
    input_json = models.JSONField(encoder=utils.EnumAwareEncoder, decoder=utils.EnumAwareDecoder)
    output_json = models.JSONField(default=dict, null=True, encoder=utils.EnumAwareEncoder,
            decoder=utils.EnumAwareDecoder)
    error_json = models.JSONField(default=dict, null=True, encoder=utils.EnumAwareEncoder,
            decoder=utils.EnumAwareDecoder)

    class ExecutionStatus(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        RUNNING = 'RUNNING', 'Running'
        DONE = 'DONE', 'Done'
        ERRORED = 'ERRORED', 'Errored'
        JSON_ERROR = 'JSON_ERROR', 'Result could not be coerced to JSON'

    status = models.CharField(max_length=10, choices=ExecutionStatus.choices,
            default=ExecutionStatus.CREATED)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)

    def execute(self):
        """Execute with given input, returning caught exceptions as necessary"""
        from turtle_shell import pydantic_adapter

        if self.status not in (self.ExecutionStatus.CREATED, self.ExecutionStatus.RUNNING):
            raise ValueError("Cannot run - execution state isn't complete")
        func = self.get_function()
        original_result = None
        try:
            # TODO: redo conversion another time!
            result = original_result = func(**self.input_json)
        except Exception as e:
            # TODO: catch integrity error separately
            self.error_json = {"type": type(e).__name__, "message": str(e)}
            self.status = self.ExecutionStatus.ERRORED
            self.save()
            raise CaughtException(f"Failed on {self.func_name} ({type(e).__name__})", e) from e
        try:
            if hasattr(result, "json"):
                result = json.loads(result.json())
            if not isinstance(result, (dict, str, tuple)):
                result = cattr.unstructure(result)
            self.output_json = result
            self.status = self.ExecutionStatus.DONE
            # allow ourselves to save again externally
            with transaction.atomic():
                self.save()
        except TypeError as e:
            self.error_json = {"type": type(e).__name__, "message": str(e)}
            msg = f"Failed on {self.func_name} ({type(e).__name__})"
            if 'JSON serializable' in str(e):
                self.status = self.ExecutionStatus.JSON_ERROR
                # save it as a str so we can at least have something to show
                self.output_json = str(result)
                self.save()
                raise ResultJSONEncodeException(msg, e) from e
            else:
                raise e
        return original_result

    def get_function(self):
        # TODO: figure this out
        from . import get_registry

        func_obj = get_registry().get(self.func_name)
        if not func_obj:
            raise ValueError(f"No registered function defined for {self.func_name}")
        return func_obj.func

    def get_absolute_url(self):
        # TODO: prob better way to do this so that it all redirects right :(
        return reverse(f'turtle_shell:detail-{self.func_name}', kwargs={"pk": self.pk})

    def __repr__(self):
        return (f'<{type(self).__name__}({self})')

    @property
    def pydantic_object(self):
        from turtle_shell import pydantic_adapter

        return pydantic_adapter.get_pydantic_object(self)

    @property
    def list_entry(self) -> list:
        return [getattr(self, obj_name) for obj_name, _ in self.FIELDS_TO_SHOW_IN_LIST]

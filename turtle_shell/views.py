from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic.edit import CreateView
from .models import ExecutionResult


class ExecutionViewMixin:
    """Wrapper that auto-filters queryset to include function name"""
    func_name: str = None
    model = ExecutionResult

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if not self.func_name:
            raise ValueError("Must specify function name for ExecutionClasses classes (class was {type(self).__name__})")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(func_name=self.func_name)


class ExecutionDetailView(DetailView, ExecutionViewMixin):
    pass

class ExecutionListView(ListView, ExecutionViewMixin):
    pass

class ExecutionCreateView(CreateView, ExecutionViewMixin):
    pass

from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from graphene_django.views import GraphQLView
from .models import ExecutionResult
from dataclasses import dataclass
from django.urls import path
from django.contrib import messages
from typing import Optional


class ExecutionViewMixin:
    """Wrapper that auto-filters queryset to include function name"""

    func_name: str = None
    model = ExecutionResult

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if not self.func_name:
            raise ValueError(
                "Must specify function name for ExecutionClasses classes (class was {type(self).__name__})"
            )

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(func_name=self.func_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["func_name"] = self.func_name
        return context


class ExecutionDetailView(ExecutionViewMixin, DetailView):
    pass


class ExecutionListView(ExecutionViewMixin, ListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("-created")


class ExecutionCreateView(ExecutionViewMixin, CreateView):
    def get_form_kwargs(self, *a, **k):
        kwargs = super().get_form_kwargs(*a, **k)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        from .models import CaughtException

        sup = super().form_valid(form)
        try:
            self.object.create_execution()
            #self.object.execute()
        except CaughtException as e:
            messages.warning(
                self.request, f"Error in Execution {self.object.pk} ({self.object.func_name}): {e}"
            )
        else:
            messages.info(
                self.request, f"Completed execution for {self.object.pk} ({self.object.func_name})"
            )
        return sup

    def get_context_data(self, *a, **k):
        ctx = super().get_context_data(*a, **k)
        ctx["doc"] = self.form_class.__doc__
        return ctx


class LoginRequiredGraphQLView(LoginRequiredMixin, GraphQLView):
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("No permission to access this resource.")
        resp = HttpResponse(json.dumps({"error": "Invalid token"}), status=401)
        resp["WWW-Authenticate"] = "Bearer"
        return resp


@dataclass
class Views:
    detail_view: object
    list_view: object
    create_view: object
    graphql_view: Optional[object]
    func_name: str

    @classmethod
    def from_function(
        cls, func: "turtle_shell._Function", *, require_login: bool = True, schema=None
    ):
        bases = (LoginRequiredMixin,) if require_login else tuple()
        detail_view = type(
            f"{func.name}DetailView", bases + (ExecutionDetailView,), ({"func_name": func.name})
        )
        list_view = type(
            f"{func.name}ListView", bases + (ExecutionListView,), ({"func_name": func.name})
        )
        create_view = type(
            f"{func.name}CreateView",
            bases + (ExecutionCreateView,),
            ({"func_name": func.name, "form_class": func.form_class}),
        )
        return cls(
            detail_view=detail_view,
            list_view=list_view,
            create_view=create_view,
            func_name=func.name,
            graphql_view=(
                LoginRequiredGraphQLView.as_view(graphiql=True, schema=schema) if schema else None
            ),
        )

    def urls(self, *, list_template, detail_template, create_template):
        # TODO: namespace this again!
        ret = [
            path(
                f"{self.func_name}/",
                self.list_view.as_view(template_name=list_template),
                name=f"list-{self.func_name}",
            ),
            path(
                f"{self.func_name}/create/",
                self.create_view.as_view(template_name=create_template),
                name=f"create-{self.func_name}",
            ),
            path(
                f"{self.func_name}/<uuid:pk>/",
                self.detail_view.as_view(template_name=detail_template),
                name=f"detail-{self.func_name}",
            ),
        ]
        ret.append(path("graphql", self.graphql_view))
        return ret

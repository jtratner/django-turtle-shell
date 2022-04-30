from dataclasses import dataclass

from django.views.generic import TemplateView


@dataclass
class _Router:
    urls: list


class _Registry:
    func_name2func: dict
    _schema = None

    def __init__(self):
        self.func_name2func = {}

    @classmethod
    def get_registry(self):
        return _RegistrySingleton

    def add(self, func, name=None, config=None):
        from .function_to_form import _Function

        # TODO: maybe _Function object should have overridden __new__ to keep it immutable?? :-/
        name = name or func.__name__
        func_obj = self.get(name)
        if not func_obj:
            func_obj = _Function.from_function(func, name=name, config=config)
            self.func_name2func[func_obj.name] = func_obj
        else:
            if func_obj.func is not func:
                raise ValueError(f"Func {name} already registered. (existing is {func_obj})")
        return self.get(name)

    def get(self, name):
        return self.func_name2func.get(name, None)

    def summary_view(self, template_name: str = "turtle_shell/overview.html"):
        """Create a summary view.

        This uses a class-based view version of Template View just to make
        """
        registry = self

        # TODO: Something is super goofy here, not sure how to wrap this up more nicely.

        class SummaryView(TemplateView):
            def get_context_data(self, **kwargs):
                ctx = super().get_context_data()
                ctx["registry"] = registry
                ctx["functions"] = registry.func_name2func.values()
                return ctx

        return SummaryView.as_view(template_name=template_name)

    def get_router(
        self,
        *,
        list_template="turtle_shell/executionresult_list.html",
        detail_template="turtle_shell/executionresult_detail.html",
        create_template="turtle_shell/executionresult_create.html",
        overview_template="turtle_shell/overview.html",
    ):
        from django.urls import path
        from . import views

        urls = [path("", self.summary_view(template_name=overview_template), name="overview")]
        for func in self.func_name2func.values():
            urls.extend(
                views.Views.from_function(func, schema=get_registry().schema).urls(
                    list_template=list_template,
                    detail_template=detail_template,
                    create_template=create_template,
                )
            )
        return _Router(urls=(urls, "turtle_shell"))

    def clear(self):
        self.func_name2func.clear()
        self._schema = None
        assert not self.func_name2func

    @property
    def schema(self):
        from .graphene_adapter import schema_for_registry

        if not self._schema:
            self._schema = schema_for_registry(self)

        return self._schema


_RegistrySingleton = _Registry()
get_registry = _Registry.get_registry

from .function_to_form import Text

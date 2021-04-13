from django import template
from django.utils.safestring import mark_safe, SafeString
from django.utils import html
from django.template.defaultfilters import urlizetrunc
import textwrap
import json

register = template.Library()


@register.filter(is_safe=True)
def pydantic_model_to_table(obj):
    if not hasattr(obj, "dict"):
        raise ValueError("Invalid object - must be pydantic type! (got {type(obj).__name__})")
    if hasattr(obj, "front_end_dict"):
        print("FRONT END DICT")
        raw = obj.front_end_dict()
    else:
        raw = json.loads(obj.json())
    return mark_safe(dict_to_table(raw))


def _urlize(value):
    if isinstance(value, SafeString):
        return value
    return urlizetrunc(value, 40)


def dict_to_table(dct):
    rows = []
    for k, v in dct.items():
        if isinstance(v, dict):
            v = dict_to_table(v)
        elif isinstance(v, (list, tuple)):
            if v:
                v_parts = [
                    html.format_html(
                        "<details><summary>{num_elements} elements</summary>", num_elements=len(v)
                    ),
                    '<table><thead><tr><th scope="col">#</th><th scope="col">Elem</th></tr></thead>',
                ]
                v_parts.append("<tbody>")
                for i, elem in enumerate(v, 1):
                    if isinstance(elem, dict):
                        elem = dict_to_table(elem)
                    v_parts.append(
                        html.format_html(
                            "<tr><td>{idx}</td><td>{value}</td></tr>", idx=i, value=_urlize(elem)
                        )
                    )
                v_parts.append("</tbody></table></details>")
                v = mark_safe("\n".join(v_parts))
        rows.append(
            html.format_html(
                '<tr><th scope="row">{key}</th><td>{value}</td>', key=k, value=_urlize(v)
            )
        )
    row_data = "\n        ".join(rows)
    return mark_safe(
        textwrap.dedent(
            f"""\
        <table class="table table-striped table-responsive">
            <thead>
                <th scope="col">Key</th>
                <th scope="col">Value</th>
            <tbody>
                {row_data}
            </tbody>
        </table>"""
        )
    )

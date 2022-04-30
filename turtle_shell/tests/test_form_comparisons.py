"""
Confirm that our form comparison tool actually works!
"""
import enum
import pytest
from django import forms
from typing import Type
from .utils import compare_form_field, compare_forms


class FormA(forms.Form):
    myfield = forms.CharField()


class DifferentFieldNames(forms.Form):
    otherfield = forms.CharField()


class DifferentFieldTypes(forms.Form):
    myfield = forms.IntegerField()


class DifferentFieldRequired(forms.Form):
    myfield = forms.CharField(required=False)


class DifferentInitial(forms.Form):
    myfield = forms.CharField(initial="something")


class DocForm(forms.Form):
    """
    My Doc

    Some new line
    """

    some = forms.CharField()


class DocFormExtraWhitespace(forms.Form):
    """
    My Doc

    Some new line
    """

    some = forms.CharField()


class DifferentDoc(forms.Form):
    """
    Another doc

    Some new line
    """

    some = forms.CharField()


def test_comparison():

    compare_forms(FormA, FormA)
    with pytest.raises(AssertionError, match="Found unexpected form fields"):
        test_different_fields(raiseit=True)

    with pytest.raises(AssertionError, match=r"Field mismatch \(myfield\)"):
        test_field_required(raiseit=True)

    with pytest.raises(AssertionError, match=r"Field mismatch \(myfield\)"):
        test_field_initial(raiseit=True)

    with pytest.raises(AssertionError, match=r"Field type mismatch \(myfield\)"):
        test_different_field_types(raiseit=True)

    with pytest.raises(AssertionError, match=r"Forms have different docstrings"):
        test_doc_diff(raiseit=True)

    test_different_whitespace()


def _wrap_knownfail(f):
    def wrapper(*args, raiseit=False, **kwargs):
        try:
            f(*args, **kwargs)
        except AssertionError as exc:
            if raiseit:
                raise
            else:
                print("Known fail: {type(exc)}: {exc}")

    return wrapper


@_wrap_knownfail
def test_different_fields():
    compare_forms(FormA, DifferentFieldNames)


@_wrap_knownfail
def test_different_field_types():
    compare_forms(FormA, DifferentFieldTypes)


@_wrap_knownfail
def test_field_required():
    compare_forms(FormA, DifferentFieldRequired)


@_wrap_knownfail
def test_field_initial():
    compare_forms(FormA, DifferentInitial)


@_wrap_knownfail
def test_convert_form():
    pass


@_wrap_knownfail
def test_doc_diff():
    actual_fields = DocForm.declared_fields
    expected_fields = DifferentDoc.declared_fields
    assert actual_fields.keys() == expected_fields.keys(), "Different fields"
    compare_forms(DocForm, DifferentDoc)


def test_different_whitespace():
    compare_forms(DocForm, DocFormExtraWhitespace)


def test_equivalent_forms():
    class Form1(forms.Form):
        myfield = forms.CharField(initial="whatever")

    class Form2(forms.Form):
        myfield = forms.CharField(initial="whatever")

    compare_forms(Form1, Form2)


def test_differ_on_doc():
    class BasicForm(forms.Form):
        myfield = forms.CharField(initial="whatever", help_text="what")

    class BasicFormDifferentDoc(forms.Form):
        myfield = forms.CharField(initial="whatever", help_text="different")

    with pytest.raises(AssertionError, match="myfield.*"):
        compare_forms(BasicForm, BasicFormDifferentDoc)

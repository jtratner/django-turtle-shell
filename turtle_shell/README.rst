Function to Form View
=====================

Motivation
----------

1. You have a bunch of shell scripts lying around to do things.
2. You don't want to force everyone to install your dependencies or use docker or whatnot.
3. Your permission model isn't SOOO complicated that it's necessary to have everyone use their own tokens OR you're just doing read-only things.
4. You want people to have website goodness (deep-linking, record of actions, easy on-boarding, etc)
5. Composing and/or ability to long-poll endpoints seems cool to you.

How does it work?
-----------------


This lil' old library converts _your_ function with annotations into a ✨Django Form✨ (that calls the function on ``form_valid``!)

It leverages some neat features of defopt under the hood so that a function like this:

.. code-block:: python

    def some_action(
        username: str,
        url: str,
        optional_comment: str=None,
        hits: int = 5,
        _special_hidden_field: bool=False,
    ):
    """Perform action on URL for username.

    Args:
        username: the user to associate the URL with
        url: which url to hit
        optional_comment: why this happened
        hits: how many hits you saw
    """
    pass


Becomes this awesome form!

    <screenshot of form with fields, help text, etc>


Overall gist
------------

You register your functions with the library::

    MyFuncWrapper = wrapit.wrap(myfunc)

Then in urls.py::


    path("/myfunc", MyFuncWrapper.as_view())
    path("/api/myfunc", MyFuncWrapper.as_view(graphql=True))

And finally run migrations::

    ...


Now you can get list view / form to create / graphql API to create.

Example Implementation
----------------------

executions.py::

    from easy_execute import ExecutionWrapper
    from my_util_scripts import find_root_cause, summarize_issue, error_summary

    Registry = ExecutionWrapper()


    FindRootCause = Registry.wrap(find_root_cause)
    SummarizeIssue = Registry.wrap(summarize_issue)
    ErrorSummary = Registry.wrap(error_summary)




You can just stop there if ya like! Woo :)

For convenience, easy_execute provides a router that set ups default list/detail/edit by function.

urls.py::

    from executions import Registry
    from graphene_django import GraphQLView

    router = Registry.get_router(list_template="list.html", detail_template="detail.html")

    urlpatterns = [
        path('/api', GraphQLView(schema=Registry.schema, include_graphiql=False)),
        path('/graphql', GraphQLView(schema=Registry.schema, include_graphiql=True)),
        # get default list and view together
        path('/execute', include(router.urls),
    ]

    # /execute/overview
    # /execute/find-root-cause
    # /execute/find-root-cause/create
    # /execute/find-root-cause/<UUID>
    # /execute/summarize-issue
    # /execute/summarize-issue/create
    # /execute/summarize-issue/<UUID>

Of course you can also customize further::

views::

    from . import executions

    class FindRootCauseList(executions.FindRootCause.list_view()):
        template_name = "list-root-cause.html"

    class FindRootCauseDetail(executions.FindRootCause.detail_view()):
        template_name = "detail-root-cause.html"

These use the generic django views under the hood.

What's missing from this idea
-----------------------------

- granular permissions (gotta think about nice API for this)
- separate tables for different objects.

Using the library
-----------------


ExecutionResult:
    DB attributes:
    - pk (UUID)
    - input_json
    - output_json
    - func_name  # defaults to module.function_name but can be customized

    Properties:
    get_formatted_response() -> JSON serializable object


ExecutionForm(func)

ExecutionGraphQLView(func)


Every function gets a generic output::

    mutation { dxFindRootCause(input: {job_id: ..., project: ...}) {
        uuid: str
        execution {
            status: String?
            exitCode: Int
            successful: Bool
        }
        rawOutput {
            stderr: String?
            stdout: String  # often JSON serializable
            }
        }
        errors: Optional {
            type
            message
        }
    }


But can also have structured output::

    mutation { dxFindRootCause(input: {job_id: ..., project: ...}) {
        output {
            rootCause: ...
            rootCauseMessage: ...
            rootCauseLog: ...
            }
        }
    }

Other potential examples::

    mutation { summarizeAnalysis(input: {analysisId: ...}) {
        output {
            fastqSizes {
                name
                size
            }
            undeterminedReads {
                name
                size
            }
            humanSummary
        }
    }


Which would look like (JSON as YAML)::

    output:
        fastqSizes:
            - name: "s_1.fastq.gz"
              size: "125MB"
            - name: "s_2.fastq.gz"
              size: "125GB"
        undeterminedReads:
        humanSummary: "Distribution heavily skewed. 10 barcodes missing. 5 barcodes much higher than rest."




Why is this useful?
-------------------

I had a bunch of defopt-based CLI tools that I wanted to expose as webapps for folks
who were not as command line savvy.

1. Python type signatures are quite succinct - reduces form boilerplate
2. Expose utility functions as forms for users


Customizing the forms
---------------------

First - you can pass a config dictionary to ``function_to_form`` to tell it to
use particular widgets for fields or how to construct a form field for your custom type (
as a callable that takes standard field keyword arguments).

You can also subclass the generated form object to add your own ``clean_*`` methods or more complex validation - yay!

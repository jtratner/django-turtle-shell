Django Turtle-Shell Usage Guide
===============================

Building App Using Turtle-shell
-------------------------------

Django turtle-shell supports asynchronous and synchronous execution of tasks. Using async with turtle-shell is easy when you want to allow long-running background tasks or update results once external systems complete.

There's an easy migration path from sync to async tasks.

first write your main method like this: XYZ.


Adding Functions To Registry
----------------------------

You can create executable functions for the app. For example:

.. code-block::

   def deidentify(sample_ids_list: Optional[str] = None,
                  flowcell_barcodes_list: Optional[str] = None,
                  deidentification_suffix: str = None,
                  flowcell_type: FlowcellType = FlowcellType.IPS):
       ...

This can be a function that needs to be executed asynchronously.

.. code-block::

   def reidentify(research_sample_ids: str,
                  send_email_to_third_party: Optional[bool] = False,
                  to_email_ids_list: Optional[str] = None,
                  flowcell_type: FlowcellType = FlowcellType.IPS):
       ...

This can be another function that needs to be executed in a synchronous fashion.

The ``_Registry`` class in turtle-shell provides the following template functionality to add such executable functions to the apps that derive from it.

In the apps that extend ``turtle_shell`` asyncronous or synchronous functions can be added as follows:

.. code-block::

    Registry = turtle_shell.get_registry()

    # Add function for new asynchronous executions
    Registry.add(deidentify)

    # Add function for new synchronous executions
    Registry.addSync(reidentify)

This will add functions ``deidentify`` and ``reidentify`` to the django app that can now be used to process requests with async or sync execution, respectively.
By adding them to the ``turtle-shell`` registry, this library converts these functions with annotations into a Django Form and optionally a graphql view. It leverages the features of defopt under the hood so that functions like this can become forms, generated from type annotations! Refer README for more details.

The ``turtle_shell`` model functions can be overridden to define app-specific implementations.

.. code-block::

    class AppExecution(turtle_shell.models.Execution):
        def get_current_state(inputs, state):
            # App specific behavior to calculate internal state of inputs (based on output from previous task), the status (state)
            # and return the new internal state of inputs (or output at this stage) and new status (state)
            return current_inputs, current_state

        def _validate_inputs(inputs, func_name, state):
            # Define input validation for function
            if inputs.valid():
                return get_current_state(inputs, state)

        def create(**kwargs):
            # App specific behavior to start an execution
            try:
                self.inputs = self.cleaned_data(**kwargs['input'])
                self.func = self.get_function()
                cur_inp, cur_state = get_current_state(self.inputs, self.state)
                # Here the execution instance is created, so the
                self.state = cur_state # will be ExecutionStatus.CREATED
                self.save()
            except CreationError as ce:
                self.handle_error_response(ce)
            return cur_inp, cur_state

        def start(**kwargs):
            # App specific behavior for running the function
            self.inputs = kwargs['input']
            cur_inp, cur_state = get_current_state(self.inputs, self.state)
            self.state = cur_state # will be ExecutionStatus.STARTED
            try:
                val_inp, val_state = _validate_inputs(cur_inp, self.func, cur_state)
                self.state = val_state # will be ExecutionStatus.VALIDATED
                self.save()
            except ValidationError as ve:
                self.handle_error_response(ve)
            return val_inp, val_state


The ``create_execution`` method is expected to validate arguments and prep data for downstream work. This should set the state to ``created``. For asynchronous functions, this can trigger queueing the executions with this state for async execution.

For any functions added, the first time the function is called as an execution, an ``ExecutionResult`` object is created. The input are stored as ``self.inputs`` on the object, and the previous return value is stored as ``self.state``.
You can also write a default function like ``get_current_state`` that simply takes inputs and state as arguments and returns a new state.

The ``execute`` function can define the app-specific behavior for running a function. This can be triggered by the task (celery or other type) handler for asynchronous function executions.

.. code-block::

    def execute(**kwargs):
            # App specific behavior for running the function
            self.inputs = kwargs['input']
            func = self.func
            try:
                result = func(**self.inputs)
                self.save()
                result_out, result_state = get_current_state(result, self.state)
            except ExecutionError as ee:
                self.handle_error_response(ee)
            return result_out, result_state

Then an optional ``update`` method like this:

.. code-block::

    def update():
         # App specific update functionality

The update method will take in current state and be expected to transition to next allowed state based on the status of the execution. In case of async function executions, this could update the status and intermediate outputs at each stage, if any.

You can optionally add a cancel method that would do cancel/ stop an execution that is in created or running states.

.. code-block::

    def cancel():
        # App specific implementation

Error handling and responses can be defined by overriding the ``handle_error_response`` function:

.. code-block::

    def handle_error_response():
        # App specific error response handling

You signal that still work to do via the ``update()`` function (dual return value?) and use ``handle_error_response()`` to signal that an error happened via exception.
If an execution fails with error due to external factors like network issues etc., then you can extend the functionality of ``execute()`` to define the behavior to ``rerun`` from the last checkpoint.


Details like input, execution states, creation/ update/ completion times, final response, intermediate stage updates or error response, if any for various functions in the app, through the ``ExecutionDetailView`` and ``ExecutionListView`` views.

Extending Turtle-shell Functionality
------------------------------------

Redefine `turtle-shell`` implementation to add executable functions with asyncronous or synchronous execution to ``_Registry`` class in turtle-shell template functionality.

.. code-block::

    def add(self, func, name=None, config=None):
        func_obj = self.get(name)
        if not func_obj:
           func_obj = _Function.from_function(func, name=name, config=config)

This adds an executable function that can be run asynchronously, which is the default mode of execution.

Functions that execute synchronously are a special case and can be added to the ``turtle-shell`` Registry using the following.

.. code-block::

    def addSync(self, func, name=None, config=None):
        func_obj = self.get(name)
        if not func_obj:
           func_obj = _Function.from_function(func, name=name, config=config)

Define these new classes:

``ExecutionValidator`` : To define input validation for function executions

``ExecutionState``: To define execution states, transition filter annotator and to implement state transitions

``Execution``: To implement functionality to create, run, update or cancel executions to specific state transitions

``SyncExecutionState``  and ``SyncExecution`` can be special case implementations for synchronous function executions.

.. code-block::

    class ExecutionValidator:
        def validate_execution_input(self, uuid, func_name, input_json):
            # define validation here

    class ExecutionState:
        states = []
        def state_transition_filter(self, from_states, to_states):
            # Default implementation is async
            # return allowed state transitions

        def transition_state(self, uuid, from_state, to_state):
            #Change from_state to to_state for the object and save

    class SyncExecutionState(ExecutionState):
        def state_transition_filter(self, from_states, to_states):
           # Implementation specific to sync execution as needed

    class Execution(ExecutionValidator, ExecutionResult):
        #all fields in the model are available here
        execution_state = ExecutionState()
        def get_function(self):
            #return function object

        def create_execution(self):
            func = self.get_function()
            self.validate_execution_input()
            self.state = "CREATED"

        @ExecutionState.state_transition_filter()
        def run_execution(self):
            json_result = self.func(**self.input_json)
            self.transition_state(uuid='', from_state=self.state, to_state='next state in flow')

        @ExecutionState.state_transition_filter()
        def update_execution(self):
            json_result = self.func(**self.input_json)
            self.transition_state(uuid='', from_state=self.state, to_state='next state in flow')

        @ExecutionState.state_transition_filter()
        def cancel_execution(self):
            self.func.cancel()
            self.transition_state(uuid='', from_state=self.state, to_state='next state in flow')

    class SyncExecution(Execution):
        execution_state = SyncExecutionState()
        def execute(self):
            self.create_execution()
            self.run_execution()

        def update(self):
            self.update_execution()

Extending Views To Support Async/ Sync Function Views
-----------------------------------------------------

Redefine Views for asynchronous and synchronous function executions.

.. code-block::

    class ExecutionDetailView(ExecutionViewMixin, DetailView):
       # Implement the DetailView to show the progress of the execution

    class ExecutionListView(ExecutionViewMixin, ListView):
        def get_queryset()
            # List executions with status (Created, Running, Done, Errored, Updating etc.)
            #order executions by("-created")

    class ExecutionCreateView(ExecutionViewMixin, CreateView):
        def get_form_kwargs()
            ...
        def get_context_data()
            ...

        def form_valid():
            self.object.create_execution()
            ....

This provides views for asynchronous functions, which is the default execution mode. This can be overridden to define special case functionality for synchronous functions.

.. code-block::

    class SyncExecutionDetailView(ExecutionViewMixin, DetailView):
        pass
        #no op

    class SyncExecutionListView(ExecutionViewMixin, ListView):
        def get_queryset():
            #order executions by("-created")

    class SyncExecutionCreateView(ExecutionViewMixin, CreateView):
        def get_form_kwargs():
            ...
        def get_context_data():
            ...
        def form_valid():
            self.object.create_execution()
            self.object.execute()
            ...

Extend the functionality of the `ExecutionResult` model to define ways to create, run, update and cancel executions.

.. code-block::

    class ExecutionResult(models.Model):
        def create_execution():
            create_response = {}
            try:
                self.status = self.ExecutionStatus.CREATED
                with transaction.atomic():
                    self.save()
                create_response['uuid'] = self.uuid
                create_response['status'] = self.status
                create_response['output_json'] = json.dumps({
 "message": "The execution is in progress and will update upon completion"})
                 ...
            except:
                error_details = {'error_type': error_type,
                                 'error_traceback': traceback,}
                error_response = self.handle_error_response(error_details)
                return error_response
            return create_response

        def handle_error_response(self, error_details):
            error_response = {}
            self.status = self.ExecutionStatus.ERRORED
            with transaction.atomic():
                self.save()

            error_response['uuid'] = self.uuid
            error_response['error_details'] = error_details
            ...
           return error_response

        def execute():
            ...
            try:
                result = original_result = func(**self.input_json)
                result = json.loads(result.json())
                self.output_json = result
                self.status = self.ExecutionStatus.DONE
                   with transaction.atomic():
                        self.save()
            except:
                error_details = {'error_type': error_type,
                                 'error_traceback': traceback}
                error_response = self.handle_error_response(error_details)
                return error_response
            ...
            return original_result

        def cancel():
            cancel_response = {}
            ...
            self.status = self.ExecutionStatus.CANCELLED
            with transaction.atomic():
                self.save()
            cancel_response['uuid'] = self.uuid
            cancel_response['status'] = self.status
            ....
            return cancel_response
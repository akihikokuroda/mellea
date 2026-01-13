Requirements API
================

Requirements are a special type of Component used for validation in Instruct/Validate/Repair patterns.

Overview
--------

Requirements in Mellea allow you to specify constraints that generated text must satisfy. They can be:

1. **Simple strings** - Validated using LLM-as-a-Judge
2. **Requirement objects** - With custom validation functions
3. **Check-only requirements** - Validated but not included in prompts

Creating Requirements
---------------------

Simple String Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest way to use requirements is with strings:

.. code-block:: python

   import mellea
   m = mellea.start_session(backend="openai/gpt-4")
   
   result = m.instruct(
       "Write an email",
       requirements=[
           "be formal",
           "Use 'Dear interns' as greeting",
           "Include a date and time"
       ]
   )

Requirement Class
~~~~~~~~~~~~~~~~~

.. class:: mellea.stdlib.requirement.Requirement

   A Requirement component for validation.

   .. method:: __init__(description: str | None = None, validation_fn: Callable[[Context], ValidationResult] | None = None, *, output_to_bool: Callable[[CBlock | str], bool] | None = default_output_to_bool, check_only: bool = False)

      Create a new Requirement.

      :param description: Natural-language description of the requirement
      :type description: str | None
      :param validation_fn: Custom validation function (if provided, LLM-as-a-Judge is not used)
      :type validation_fn: Callable[[Context], ValidationResult] | None
      :param output_to_bool: Function to convert LLM output to boolean (default looks for "yes")
      :type output_to_bool: Callable[[CBlock | str], bool] | None
      :param check_only: If True, requirement is validated but not included in instruction prompt
      :type check_only: bool

      **Example - Basic Requirement:**

      .. code-block:: python

         from mellea.stdlib.requirement import Requirement
         
         req = Requirement("Output must be valid JSON")
         result = m.instruct("Generate user data", requirements=[req])

      **Example - Custom Validation Function:**

      .. code-block:: python

         from mellea.stdlib.requirement import Requirement, ValidationResult
         
         def validate_length(ctx):
             output = str(ctx.last_output())
             is_valid = len(output) < 100
             return ValidationResult(
                 result=is_valid,
                 reason=f"Length is {len(output)}, must be < 100"
             )
         
         req = Requirement(
             description="Keep it short",
             validation_fn=validate_length
         )
         
         result = m.instruct("Write a summary", requirements=[req])

      **Example - Check-Only Requirement:**

      .. code-block:: python

         # This requirement is validated but NOT included in the prompt
         # Useful to avoid "purple elephant" effects
         req = Requirement(
             "Do not mention elephants",
             check_only=True
         )

   .. method:: validate(backend: Backend, ctx: Context, *, format: type[BaseModelSubclass] | None = None, model_options: dict | None = None) -> ValidationResult

      Validate the requirement against a context.

      :param backend: The backend to use for LLM-as-a-Judge validation
      :type backend: Backend
      :param ctx: The context to validate
      :type ctx: Context
      :param format: Optional structured output format
      :type format: type[BaseModelSubclass] | None
      :param model_options: Optional model options
      :type model_options: dict | None
      :return: Validation result
      :rtype: ValidationResult

ValidationResult Class
~~~~~~~~~~~~~~~~~~~~~~

.. class:: mellea.stdlib.requirement.ValidationResult

   The result of a requirement's validation.

   .. method:: __init__(result: bool, *, reason: str | None = None, score: float | None = None, thunk: ModelOutputThunk | None = None, context: Context | None = None)

      Create a validation result.

      :param result: True if the requirement passed, False otherwise
      :type result: bool
      :param reason: Optional reason for the result
      :type reason: str | None
      :param score: Optional numeric score
      :type score: float | None
      :param thunk: Optional ModelOutputThunk if LLM was used
      :type thunk: ModelOutputThunk | None
      :param context: Optional context if backend was used
      :type context: Context | None

      **Example:**

      .. code-block:: python

         from mellea.stdlib.requirement import ValidationResult
         
         def my_validator(ctx):
             output = str(ctx.last_output())
             word_count = len(output.split())
             
             return ValidationResult(
                 result=word_count >= 50,
                 reason=f"Word count: {word_count}/50",
                 score=word_count / 50.0
             )

   .. attribute:: reason
      :type: str | None

      Reason for the validation result.

   .. attribute:: score
      :type: float | None

      Optional numeric score for the validation.

   .. attribute:: thunk
      :type: ModelOutputThunk | None

      The ModelOutputThunk if an LLM was used for validation.

   .. attribute:: context
      :type: Context | None

      The context if a backend was used for validation.

   .. method:: as_bool() -> bool

      Return the validation result as a boolean.

   .. method:: __bool__() -> bool

      Allow using ValidationResult in boolean contexts.

Helper Functions
----------------

req
~~~

.. code-block:: python

   from mellea.stdlib.requirement import req
   
   # Shorthand for creating requirements
   requirements = [
       req("be formal"),
       req("include date")
   ]

check
~~~~~

.. code-block:: python

   from mellea.stdlib.requirement import check
   
   # Create a check-only requirement
   requirements = [
       check("do not mention competitors")
   ]

Requirement Libraries
---------------------

Mellea provides pre-built requirement libraries for common validation tasks:

Markdown Requirements
~~~~~~~~~~~~~~~~~~~~~

See :doc:`stdlib` → Requirement Libraries → Markdown

.. code-block:: python

   from mellea.stdlib.reqlib.md import (
       has_section,
       has_bullet_list,
       has_code_block
   )
   
   result = m.instruct(
       "Write a README",
       requirements=[
           has_section("Installation"),
           has_bullet_list(),
           has_code_block()
       ]
   )

Python Requirements
~~~~~~~~~~~~~~~~~~~

See :doc:`stdlib` → Requirement Libraries → Python

.. code-block:: python

   from mellea.stdlib.reqlib.python import (
       is_valid_python,
       has_function,
       has_docstring
   )
   
   result = m.instruct(
       "Write a Python function",
       requirements=[
           is_valid_python(),
           has_function("calculate_total"),
           has_docstring()
       ]
   )

Tools Requirements
~~~~~~~~~~~~~~~~~~

See :doc:`stdlib` → Requirement Libraries → Tools

Best Practices
--------------

1. **Use Custom Validators for Deterministic Checks**
   
   When possible, write validation functions instead of relying on LLM-as-a-Judge:

   .. code-block:: python

      # Good - deterministic
      def validate_json(ctx):
          try:
              json.loads(str(ctx.last_output()))
              return ValidationResult(True)
          except:
              return ValidationResult(False, reason="Invalid JSON")
      
      # Less reliable - uses LLM
      req = Requirement("Output must be valid JSON")

2. **Use check_only to Avoid Purple Elephants**
   
   If mentioning a constraint in the prompt might cause the model to violate it, use ``check_only=True``:

   .. code-block:: python

      # Don't mention "elephants" in the prompt, but check for them
      req = Requirement("Do not mention elephants", check_only=True)

3. **Provide Helpful Reasons in ValidationResult**
   
   Include specific feedback that can help with repair:

   .. code-block:: python

      return ValidationResult(
          result=False,
          reason=f"Expected 5 paragraphs, found {paragraph_count}"
      )

See Also
--------

* :doc:`session_api` - Using requirements with ``m.instruct()``
* :doc:`quickref` - Quick examples
* :doc:`stdlib` - Requirement libraries (markdown, python, tools)
* Source: ``mellea/stdlib/requirement.py``

.. Made with Bob

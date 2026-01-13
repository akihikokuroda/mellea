Session API
===========

The ``MelleaSession`` class provides the main interface for interacting with Mellea.

.. note::
   This page provides manual documentation for the Session API. Due to circular import issues,
   some methods cannot be auto-documented. See the source code for complete details.

Creating a Session
------------------

.. code-block:: python

   import mellea
   
   # Create a session with a specific backend
   m = mellea.start_session(backend="openai/gpt-4")
   
   # Or with a local model
   m = mellea.start_session(backend="ollama/llama2")

MelleaSession Class
-------------------

.. class:: mellea.stdlib.session.MelleaSession

   The main session object for Mellea operations.

   .. method:: instruct(description: str, *, requirements: list[str | Requirement] | None = None, strategy: SamplingStrategy | None = None, format: type[BaseModelSubclass] | None = None, model_options: dict | None = None, tool_calls: bool = False) -> str

      Generate text based on instructions with optional requirements and sampling strategies.

      :param description: The instruction or task description
      :type description: str
      :param requirements: Optional list of requirements (strings or Requirement objects)
      :type requirements: list[str | Requirement] | None
      :param strategy: Sampling strategy for generation (default: RejectionSamplingStrategy)
      :type strategy: SamplingStrategy | None
      :param format: Pydantic model for structured output
      :type format: type[BaseModelSubclass] | None
      :param model_options: Additional model-specific options
      :type model_options: dict | None
      :param tool_calls: Whether to enable tool calling
      :type tool_calls: bool
      :return: Generated text
      :rtype: str

      **Example:**

      .. code-block:: python

         from mellea.stdlib.sampling import RejectionSamplingStrategy
         
         email = m.instruct(
             "Write an email to invite all interns to the office party.",
             requirements=["be formal", "Use 'Dear interns' as greeting."],
             strategy=RejectionSamplingStrategy(loop_budget=3),
         )

      **With structured output:**

      .. code-block:: python

         from pydantic import BaseModel
         
         class Person(BaseModel):
             name: str
             age: int
         
         person = m.instruct(
             "Generate a person profile",
             format=Person
         )

   .. method:: chat(message: str, *, images: list[PILImage.Image] | None = None, model_options: dict | None = None, tool_calls: bool = False) -> str

      Send a chat message and get a response.

      :param message: The chat message
      :type message: str
      :param images: Optional list of images for multimodal models
      :type images: list[PILImage.Image] | None
      :param model_options: Additional model-specific options
      :type model_options: dict | None
      :param tool_calls: Whether to enable tool calling
      :type tool_calls: bool
      :return: Model response
      :rtype: str

      **Example:**

      .. code-block:: python

         response = m.chat("What is the capital of France?")
         print(response)  # "The capital of France is Paris."

   .. method:: generate(component: Component, *, requirements: list[Requirement] | None = None, strategy: SamplingStrategy | None = None, format: type[BaseModelSubclass] | None = None, model_options: dict | None = None, tool_calls: bool = False) -> ModelOutputThunk

      Low-level generation method with full control over components.

      :param component: The component to generate from
      :type component: Component
      :param requirements: Optional requirements
      :type requirements: list[Requirement] | None
      :param strategy: Sampling strategy
      :type strategy: SamplingStrategy | None
      :param format: Structured output format
      :type format: type[BaseModelSubclass] | None
      :param model_options: Model options
      :type model_options: dict | None
      :param tool_calls: Enable tool calling
      :type tool_calls: bool
      :return: Model output thunk
      :rtype: ModelOutputThunk

   .. attribute:: ctx
      :type: Context

      The current context (conversation history).

   .. attribute:: backend
      :type: Backend

      The backend being used for generation.

   .. attribute:: model_options
      :type: dict

      Default model options for this session.

Functional API
--------------

For advanced use cases, Mellea provides a functional API:

.. code-block:: python

   from mellea.stdlib.functional import instruct
   from mellea.stdlib.session import start_session
   
   m = start_session(backend="openai/gpt-4")
   
   result = instruct(
       "Write a haiku",
       context=m.ctx,
       backend=m.backend
   )

See Also
--------

* :doc:`quickref` - Quick reference with examples
* :doc:`stdlib` - Other standard library modules
* Source: ``mellea/stdlib/session.py``
* Source: ``mellea/stdlib/functional.py``

.. Made with Bob

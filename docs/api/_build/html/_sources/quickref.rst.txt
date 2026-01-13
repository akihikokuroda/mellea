Quick Reference
===============

This page provides quick links to commonly used Mellea functions and methods.

Core Session Methods
--------------------

The ``MelleaSession`` object (typically named ``m``) provides the main interface for Mellea operations.

Creating a Session
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import mellea
   m = mellea.start_session(backend="openai/gpt-4")

Key Methods
~~~~~~~~~~~

instruct
^^^^^^^^

Generate text based on instructions with optional requirements and sampling strategies.

.. automethod:: mellea.stdlib.session.MelleaSession.instruct
   :noindex:

**Example:**

.. code-block:: python

   from mellea.stdlib.sampling import RejectionSamplingStrategy
   
   email = m.instruct(
       "Write an email to invite all interns to the office party.",
       requirements=["be formal", "Use 'Dear interns' as greeting."],
       strategy=RejectionSamplingStrategy(loop_budget=3),
   )

chat
^^^^

Interactive chat with the model.

.. automethod:: mellea.stdlib.session.MelleaSession.chat
   :noindex:

**Example:**

.. code-block:: python

   response = m.chat("What is the capital of France?")

generate
^^^^^^^^

Low-level generation with full control.

.. automethod:: mellea.stdlib.session.MelleaSession.generate
   :noindex:

Functional API
--------------

Mellea also provides a functional API for more advanced use cases.

instruct (functional)
~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: mellea.stdlib.functional.instruct
   :noindex:

**Example:**

.. code-block:: python

   from mellea.stdlib.functional import instruct
   from mellea.stdlib.session import start_session
   
   m = start_session(backend="openai/gpt-4")
   result = instruct(
       "Write a haiku about programming",
       context=m.ctx,
       backend=m.backend
   )

Sampling Strategies
-------------------

RejectionSamplingStrategy
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: mellea.stdlib.sampling.RejectionSamplingStrategy
   :noindex:
   :members:

**Example:**

.. code-block:: python

   from mellea.stdlib.sampling import RejectionSamplingStrategy
   
   strategy = RejectionSamplingStrategy(loop_budget=5)
   result = m.instruct("Generate a valid email", strategy=strategy)

BestOfNSamplingStrategy
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: mellea.stdlib.sampling.best_of_n.BestOfNSamplingStrategy
   :noindex:
   :members:

MajorityVotingSamplingStrategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: mellea.stdlib.sampling.majority_voting.MajorityVotingSamplingStrategy
   :noindex:
   :members:

Requirements
------------

Creating Requirements
~~~~~~~~~~~~~~~~~~~~~

Requirements can be specified as strings or ``Requirement`` objects:

.. code-block:: python

   # Simple string requirements
   m.instruct("Write code", requirements=["use Python", "include comments"])
   
   # Using Requirement objects
   from mellea.stdlib.requirement import Requirement
   
   req = Requirement("Output must be valid JSON")
   m.instruct("Generate user data", requirements=[req])

See Also
--------

* :doc:`stdlib` - Complete standard library reference
* :doc:`backends` - Backend implementations
* :doc:`index` - Main documentation index

.. Made with Bob

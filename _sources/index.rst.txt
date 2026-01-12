Biohit Pipettor Plus Documentation
====================================

Welcome to the Biohit Pipettor Plus documentation. This is a modern GUI application
for controlling electronic pipettors with advanced workflow capabilities.

Quick Links
-----------

* `Download Latest Release (v1.0.2) <https://github.com/smartlab-network/open-biohit-plus/releases/latest>`_
* `GitHub Repository <https://github.com/smartlab-network/open-biohit-plus>`_

Overview
--------

Biohit Pipettor Plus is a comprehensive solution for automated pipetting operations.
While currently in use with Biohit electronic pipettors, it can be adapted for use
with other pipettor brands as well.

Key Features
^^^^^^^^^^^^

* **Interactive GUI** - Custom deck, slot, and labware definition with easy visualization
* **Flexible Operation** - Works with both single and multi-channel pipettors
* **Labware-Based Operations** - Direct implementation of common operations:

  * ``pick_tips()`` - Automated tip picking
  * ``return_tips()`` - Tip disposal and return
  * ``add_medium()`` - Liquid addition
  * ``remove_medium()`` - Liquid removal

* **Workflow Builder** - Build, save, and run complex operation sequences
* **Operation Logging** - Complete tracking of all pipetting operations
* **Save & Load** - Persistent storage of workflows and deck configurations

User Guide
----------

.. toctree::
   :maxdepth: 2
   :caption: Contents

   deck_slot_labware
   pipettor
   operation
   workflow
   troubleshooting

API Reference
-------------

Complete API documentation for all modules and classes.

.. automodule:: biohit_pipettor_plus
   :members:
   :undoc-members:
   :show-inheritance:

Support
-------

If you encounter any issues or have questions:

* Check the :doc:`troubleshooting` guide
* Open an issue on `GitHub <https://github.com/smartlab-network/open-biohit-plus/issues>`_

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
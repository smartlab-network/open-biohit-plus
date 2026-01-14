Configuring the Pipettor
========================
After creating a deck, you must connect to the pipettor before any operations can be performed.

Brief introduction to the ``open-biohit`` package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
By default, the software connects to a Sartorius Biohit pipettor using the
``open-biohit`` Python package.

Documentation:
`open-biohit (biohit-pipettor-python) <https://umg-pharma-lab-automation.pages.gwdg.de/biohit-pipettor-python/>`_

The ``open-biohit`` package communicates with the pipettor via a **32-bit vendor DLL**. It provides access to
basic pipetting commands such as move_x, move_y, pick_tip, aspirate:

Notes from the package documentation:

* The pipettor may be **single-channel** or **multi-channel**.
* It supports tips of **200 µL** and **1000 µL**.
* The connection is handled through a **context manager** to prevent errors affecting future workflows.
* The pipettor can be **initialized on connect**, resetting it to its default state.
* A **mock pipettor** connection is available:

  * A plot of pipettor calls is generated using ``matplotlib`` when mock connection ends.

How to connect
^^^^^^^^^^^^^^
Pipettor configuration is managed from the **Pipettor Configuration** section inside the
**Low-Level Parameters** tab.

Available configuration options include:

* Tip volume
* Tip length
* Single-channel or multi-channel mode
* Initialize pipettor on connect
* Connect to mock pipettor

After configuring these values, click **Connect to Pipettor** to verify the connection.

Once connected, additional parameters can be tuned:

* Movement speed
* Aspirate force
* Dispense force

Tip lengths
-----------
``TIP_LENGTHS`` provides default tip lengths:

* **200 µL:** 38 mm
* **1000 µL:** 88 mm

Reference document:
`rLINE dispensing module (PDF) <https://shop.sartorius.com/medias/rLINE-dispensing-module.pdf?context=bWFzdGVyfGRvY3VtZW50c3wxMDQ1NjEzfGFwcGxpY2F0aW9uL3BkZnxhRGhoTDJoaE1pODVPVEEyT0RReE9UYzJPRFl5fGFkZmZmYzFjM2UzYjAwNjI2ODA3MmVmZmYxMWU4NDExZTVlOWMyNTFjNmYzYjZmY2M3Y2ZkODgxMDEzN2U1MDg>`_


Troubleshooting connection issues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Check the following:

* Ensure the pipettor USB driver is installed.
* Confirm the pipettor is powered on and responsive.
* Clear any pending error/backlog state.
  For Biohit pipettors, a **blue light** may indicate a backlog error.
* Restart the program and try connecting again.
* Try connecting without the GUI using the base package.

If the error cannot be cleared using the steps above, a technician may be required.

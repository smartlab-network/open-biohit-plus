Troubleshooting
===============

Workflow/Operation validation failing
----------------------------------------

Sometimes, the Workflow will not be validated and an error message will show up on the screen. The operation that causes
workflow failure will be shown and the reason behind error as well. These are the common errors that can be expected
when interacting with follwoing labware type

- **Plate (Well)** - Overflow when dispensing /Not enough Volume when aspirating
- **ReservoirHolder (Reservoir)** - Overflow when dispensing /Not enough Volume when aspirating
- **PipetteHolder ( IndividualPipeeteHolder)** - Pipettor fail to pick tip from selected holder during pick_tip/ replace_tip.

If the operation is physically possible, then changing children value by clicking on edit children Lw in deck_Editor.


.. _pipettor-connection-issues:

Pipettor connection issues
---------------------------
Check the following:

* Ensure the pipettor USB driver is installed.
* Confirm the pipettor is powered on and responsive.
* Clear any pending error/backlog state.
  For Biohit pipettors, a **blue light** may indicate a backlog error.
* Restart the program and try connecting again.
* Try connecting without the GUI using the base package.

If the error cannot be cleared using the steps above, a technician may be required.


Installing a new pipettor
---------------------------

A package similar to open-biohit must be created with similar pipettor functions. Mock pipettor should also be
consdiered to allow virtual testing. Clone the open-biohit-plus package and change import in pipettor_plus.py file in
biohit_pipettor_plus.pipettor_plus folder. Change pyproject.toml and spec file accordingly Make sure python in use
matches the bit version of dll file

Go through the documentation of `open-biohit (biohit-pipettor-python) <https://umg-pharma-lab-automation.pages.gwdg.de/biohit-pipettor-python/>`_

Welcome to the biohit-pipettor documentation!
=============================================

.. toctree::
   :maxdepth: 2

This module is an unofficial Python interface for our Biohit Roboline devices.

Installation
------------

First, download the repository as zip file `here <https://gitlab.gwdg.de/umg-pharma-lab-automation/biohit-pipettor-python/-/archive/master/biohit-pipettor-python-master.zip>`_.
Then, execute ``pip install biohit-pipettor-python-master.zip``.

Usage
-----

To control the pipetting robot, use the :py:class:`~biohit_pipettor.Pipettor` class.

Details about encountered errors are currently not provided.
If you encounter errors and would like to receive more details, please let the maintainer know.

All distance values are given or expected in millimeters, volumes are in microliters.

It is strongly recommended to use the Pipettor class as a `context manager <https://book.pythontips.com/en/latest/context_managers.html#context-managers>`_:
Otherwise, background threads might not be properly stopped when errors occur, preventing the program from terminating.

.. code-block::

    from biohit_pipettor import Pipettor

    with Pipettor(tip_volume=200, multichannel=False, initialize=True) as p:
        p.move_xy(10, 10)
        p.pick_tip(70)
        p.move_xy(25, 160)
        p.aspirate(50)
        p.move_xy(100, 60)
        p.dispense_all()
        ...

Simulation
----------

You can use the class :py:class:`~biohit_pipettor.pipettor_simulator._PipettorSimulator` instead of :py:class:`~biohit_pipettor.Pipettor`
to check your pipetting routine for common errors, perform static type checks, and generate a plot representing your routine.

Detected problems
^^^^^^^^^^^^^^^^^

It raises a :py:class:`RuntimeError` in the following situations:

- if used without context manager (works on real device, but should not be done)
- if ``tip_volume`` was not ``200`` or ``1000``
- if ``multichannel`` was ``True`` and ``tip_volume`` was ``200``
- if ``initialize`` was ``False`` (works on the real device, but simulation must start with no tip at position (0, 0, 0))
- if ``initialize()`` is executed while the pipettor has a tip
- if ``move_to_surface()`` is executed with a multi-channel pipette
- if ``move_to_surface()`` is executed while the pipettor has no tip
- if ``aspirate()`` is executed while the pipettor has no tip
- if ``aspirate()`` is executed with too much volume
- if ``dispense()`` is executed while the pipettor has no tip
- if ``dispense()`` is executed with more volume than currently is in the tip
- if ``dispense_all()`` is executed whiel the pipettor has no tip
- if ``pick_tip()`` is executed while the pipettor has a tip
- if ``eject_tip()`` is executed while the pipettor has no tip

It emits a :py:class:`UserWarning` in the following situations:

- if the pipettor has a tip at the end of the context manager
- if ``eject_tip()`` is executed and the tip is not empty
- if ``move_to_surface()`` is executed (only works if the device has a working tip sensor)
- if ``sensor_value`` is accessed (only works if the device has a working tip sensor)

Examples:

.. code-block:: python

    from biohit_pipettor import PipettorSimulator

    # error: no context manager
    p = PipettorSimulator(tip_volume=200, multichannel=False, initialize=True)
    p.move_xy(10, 20)

    # error: initialize must be True
    with PipettorSimulator(tip_volume=200, multichannel=False, initialize=False) as p:
        ...

    # error: aspirate requires a tip
    with PipettorSimulator(tip_volume=200, multichannel=False, initialize=True) as p:
        p.aspirate(100)

Static type checking
^^^^^^^^^^^^^^^^^^^^

You can use `mypy <https://github.com/python/mypy>`_ to check your code for type errors:

- Installation: ``pip install mypy``
- Check: ``mypy path/to/your/pipetting-script.py``

Plotting
^^^^^^^^

The :py:class:`PipettorSimulator <biohit_pipettor.pipettor_simulator._PipettorSimulator>` internally writes every action to a `matplotlib <https://matplotlib.org>`_ plot
(:py:attr:`~biohit_pipettor.pipettor_simulator._PipettorSimulator.fig`, :py:attr:`~biohit_pipettor.pipettor_simulator._PipettorSimulator.ax`).
You can interact with these attributes directly, or use the methods :py:func:`~biohit_pipettor.pipettor_simulator._PipettorSimulator.save_plot`
or :py:func:`~biohit_pipettor.pipettor_simulator._PipettorSimulator.show_plot` to save/show the plot.

Example:

.. code-block:: python

    from biohit_pipettor import PipettorSimulator

    with PipettorSimulator(tip_volume=200, multichannel=False) as p:
        p.move_xy(100, 50)
        p.pick_tip(100)

        p.move_xy(150, 100)
        p.aspirate(200)

        for column in range(12):  # 11 to 0
            tip_x = column * 9 + 6
            for row in range(8):  # 0 to 7
                tip_y = row * 9 + 125

                p.move_xy(tip_x, tip_y)
                p.move_z(60)
                p.dispense(2)

        p.move_z(0)
        p.move_xy(150, 150)
        p.dispense_all()

        p.move_xy(50, 50)
        p.eject_tip()

        p.show_plot()

This generates this plot:

.. image:: bla.svg


The Pipettor classes
--------------------

.. autoclass:: biohit_pipettor.Pipettor
    :show-inheritance:

.. autoclass:: biohit_pipettor.pipettor_simulator._PipettorSimulator
    :show-inheritance:

.. autoclass:: biohit_pipettor.AbstractPipettor

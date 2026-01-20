Deck, Slot, and Labware
========================

This section explains the core components for defining and managing the physical layout
of your automated pipetting system through the GUI interface.

Overview
--------

The deck-slot-labware system creates a hierarchical structure that you interact with through the GUI:

* :class:`~biohit_pipettor_plus.Deck`
  - The main working surface that contains all slots

* :class:`~biohit_pipettor_plus.Slot`
  - Individual positions on the deck that hold labware

* :class:`~biohit_pipettor_plus.Labware`
  - Physical items like tip racks, well plates, and reservoirs

This hierarchical organization allows for precise positioning and tracking of all components
during automated pipetting operations. Each item has a unique id.

Labware Types
-------------

Low level labware (LLL)
^^^^^^^^^^^^^^^^^^^^^^^^^^

* :class:`~biohit_pipettor_plus.Well`
* :class:`~biohit_pipettor_plus.IndividualPipetteHolder`
* :class:`~biohit_pipettor_plus.Reservoirs`

LLL Parameters
^^^^^^^^^^^^^^^^

All three Low level labware require size x,y,z dimensions alongside offset x and offset y values.

- Offset is distance from the center of the object at which the pipettor should access the labware.
- Well and Reservoir has **content** attribute, a dictionary mapping content types to volumes.
- IndividualPipetteHolder has **has_tip** attribute that signify if tips are present or not.

High level labware (HLL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* :class:`~biohit_pipettor_plus.Plate`  – contain wells (e.g. 48-well plate)
* :class:`~biohit_pipettor_plus.PipetteHolder` -  contain IndividualPipetteHolders (individual tips)
* :class:`~biohit_pipettor_plus.ReservoirHolder` – contain Reservoirs (30ml reservoir,100ml reservoirs, 2ml tubes)
* :class:`~biohit_pipettor_plus.Stack` -  a minimal labware intended to let other labware stack on top of it
* :class:`~biohit_pipettor_plus.TipDropzone` - An open box where tips can be discarded

HLL parameters
^^^^^^^^^^^^^^^

All HLL share a few common attributes. This includes dimensions(size_x,y,z), offset(x & y), and stackable(True or False)
- offset values is the distance (mm) of the first object in the labware from slot corner (top left)
- stackable property allow other labware to be placed on top of them.

TipDropzone includes a drop height parameter, which specifies the distance above the labware bottom
where the pipettor should release (discard) tips.
Unique parameters for PipetteHolder, ReservoirHolder, and Plate include:

- Rows
- Columns
- Add height: height from the specific LLL bottom at which ``eject_tip`` / ``dispense`` is performed
- Remove height: height from the specific LLL bottom at which ``pick_tip`` / ``aspirate`` is performed
- X spacing: distance between adjacent LLLs along the X dimension
- Y spacing: distance between adjacent LLLs along the Y dimension
- LLL template: create or select the LLL


Since reservoir can be big enough to accommodate all tips of multipipettor or just one, ReservoirHolder has another
parameter called as ``one reservoir per tip``. When ticked, the pipettor will expect unique reservoir for all the tips


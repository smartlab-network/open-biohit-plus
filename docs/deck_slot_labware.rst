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
  - Link to API

* :class:`~biohit_pipettor_plus.Labware`
  - Physical items like tip racks, well plates, and reservoirs
  - Link to API

This hierarchical organization allows for precise positioning and tracking of all components
during automated pipetting operations. Each item has a unique id.

Labware Types
-------------

Low level labware (lll)
^^^^^^^^^^^^^^^^^^^^^^^^^^

* :class:`~biohit_pipettor_plus.Well`
* :class:`~biohit_pipettor_plus.IndividualPipetteHolder`
* :class:`~biohit_pipettor_plus.Reservoirs`

Well and Reservoir has **content** attrbiute , dictonary mapping content types to volumes
IndividualPipetteHolder has has_tip attribute that signify where

High level labware (hll)
^^^^^^^^^^^^^^^^^^^^^^^^^^^


* :class:`~biohit_pipettor_plus.Plate`  – contain wells (e.g. 48-well plate)
* :class:`~biohit_pipettor_plus.PipetteHolder` -  contain IndividualPipetteHolders (individual tips)
* :class:`~biohit_pipettor_plus.ReservoirHolder` – contain Reservoirs (30ml reservoir,100ml reservoirs, 2ml tubes)
* :class:`~biohit_pipettor_plus.Stack` -  a minimal labware intended to let other labware stack on top of it
* :class:`~biohit_pipettor_plus.TipDropzone` - An open box where tips can be discarded


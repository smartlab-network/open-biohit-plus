Direct Operation
==================

Operations on the pipettor can be executed directly or thorugh a wrokflow. Both are availiable once the pipettor is connected.

Before running an operation/workflwo, they are validated to ensure they can be run. For eg,
if user select inidivualpipietteholders with no tips for pick tip operation, then the validation will fail. Similarly,
aspirating more volume than available or filling more than capacity will lead to failure.

The most basic list of operation are available under system heading. This include
Home , move_xy , move_z , pick_tips,
eject_tips, aspirate, dispense

Tip Operations
^^^^^^^^^^^^^^^^
These operations include interaction of the pipettor with the PipetteHolder(IndividualPipetteHolder) or TipDropzone labware.
The four operations are

**Discard Tips** - goes to TipDropzone at drop_height and eject the tip.

**Pick Tips** - goes to the selected/auto-selected IndividualPipetteHolder and pick tip.
Value error is raised if pipettor already has tips or if pipettor fail to pick tips from all IndividualPipetteHolder

**Return Tips** - goes to the selected/auto-selected IndividualPipetteHolder and eject tip
Value error is raised if pipettor has no tips to begin with or if pipettor fail to eject tips to all IndividualPipetteHolder

**Replace Tips** - Return tips + Pick tips.

Since IndividualPipetteHolder contains pick_tip attribute, a simple autoselect feature is activated if user make operation
without selecting any individualHolder. For Pick_tips operation, holder with has_tip = TRUE are selected and opposite
for Return_tips. To assist the user, non-usable holders for the operation are automatically disabled.

.. _liquid_handling_operation:

Liquid handling operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^
These operations include interaction of the pipettor with the Plate(wells) and ReservoirHolder(reservoirs) labware. It
is essential for the pipettor to have tips to commence these operations.

The four operations are -:

**Add medium** - Transfer medium from Reservoir to Wells. One to many.
**Remove medium** - Transfer medium from Wells to Resrevoir. Many to One.
**Transfer Plate** to Plate - Transfer medium from Wells to Wells. One to One.
**Remove and Add** - runs Remove medium and Add medium in batches of well. This is ideal for long operation if well must
not be without liquid for a long time

Key feature of the operations -:

**Batch_mode_transfer** - This ensure efficiency in one to many operation or many to one operation. For example, if 190ul is to be
added to 10 well and tip_volume is 1000ul, the pipettor will aspirate 950ul and dispense 190ul to 5 wells and do same
for remaining 5. Not applicable for one to one operation. Batch size is capped by Maximum_Batch_Size.

**Multi_trip_transfer** - If working volume exceeds max tip_volume, then each labware item gets accessed the
required number of times to fulfil the volume.

**Mixing** - Limit batch size to 1. Runs after dispensing to wells in add_medium, transfer_Plate_to_Plate, remove_and_Add.
Simple aspiration and dispensing of said volume.

**Change tips** - Limit batch size to 1. Runs discard_tip and pick_tip after every operation. If TipDropzone is not present
then return_tip and pick_tip is run.

Start_measurement
^^^^^^^^^^^^^^^^^^^^^^^^^^

This runs the chosen bat script after a period of incubation. Example use - to measure force of measurement of beating EHMs.


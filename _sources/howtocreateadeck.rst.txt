How to create a deck
========================

"Deck_Editor" and "Low Level Parameter" tab of GUI are involved in creating and setting up deck for pipetting operations.

Defining a new Deck
--------------------

1. Open the **File** menu in the top menu bar.
2. Select **New Deck** and enter desired parameters.
3. A new, empty deck will be created and displayed in the **Deck_Editor** tab.

At this stage, the deck contains no slots or labware. The current deck info can be seen in the **Deck_Editor** tab.

Working with Slot
------------------

To create a slot:

1. Navigate to the **Deck_Editor** tab.
2. Click **Create Slot** and enter desired parameters.
3. The slot now exists in **unplaced state** and should be seen in the selection box.
4. Unplaced slot can be placed, edited, or deleted. **Double click** on the slot also places the slot on deck
5. To unplace a slot --- **Triple click** the slot or click on **Unplace slot** button

Working with Labware
----------------------

Creating a labware is slightly more complex because of various types of labware.

1. Low level labware can be created by clicking on **Create LLL** in the **Low level parameter** tab.
    List of available LLL can also be seen there.

2. High level labware can be created by clicking on **Create labware** in the **Deck_Editor** tab.
    If LLL for the HLL does not exist, the required LLL can also be created when creating a HLL.

Labware placement and editing:

* After creation, HLL can be placed on slot by clicking on **Place on Slot on Deck**. Double clicking does the same job
* Triple click removes placed labware from deck
* Physical attributes (such as size, offset, stackable) are editable for a HLL
* Physical attribute of the LLL used in HLL creation is not editable
* Some properties of the LLL (like has_tips/ content) is however editable
* Note - For ReservoirHolder, LLL can be removed and custom reservoir spanning (more than one row/column) can be used

After Labware is placed
------------------------------
It is important to validate a labware parameters at least once. This can be done once the labware is placed.

Click on **Edit children lw** button in Deck editor tab and test out position, add, and remove height for the labware.
These values are passed on to the pipettor during operations and hence it is important to confirm them. Adjustment to
the parameters have to be made to get desired positions and z values.

Saving and Loading Decks
------------------------
Deck configurations can be saved and reused.

To save a deck:

1. Open the **File** menu.
2. Select **Save Deck**.

To load an existing deck:

1. Open the **File** menu.
2. Select **Load Deck**.
3. Choose a previously saved deck configuration.

Important Notes
^^^^^^^^^^^^^^^^

.. important::

   If a deck is created or modified during an active session, the pipettor must
   be reconnected. The pipettor connection requires a valid deck reference, which
   changes whenever the deck is updated.

Always ensure that the virtual deck layout matches the physical setup of the
instrument to avoid incorrect pipetting behavior or hardware collisions.


Next Steps
^^^^^^^^^^^^

Once the deck has been created and validated, you can proceed to:

* Configure pipettor
* Build workflows
* Execute pipetting operations

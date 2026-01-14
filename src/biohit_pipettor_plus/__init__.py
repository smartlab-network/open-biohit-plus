"""
Biohit Pipettor Plus
====================

A comprehensive solution for automated pipetting operations with GUI workflow builder.
"""

__version__ = "1.0.2"
__author__ = "Advait Lath"


from biohit_pipettor_plus.deck_structure import *
from biohit_pipettor_plus.pipettor_plus.pipettor_plus import PipettorPlus

__all__ = [
    "PipettorPlus",
] + deck_structure.__all__
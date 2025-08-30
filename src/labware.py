import json
import os
import os.path
from envs import env
from pathlib import Path
from biohit_pipettor.baseclass import Baseclass

class Labware(Baseclass):
    """
    Loads the Labware Libraries
    :param initialize: 
    """
    _labware_folder = Path(r"C:\Labhub\Import\Labware")
    _labware_env: str = 'LABWARE_DIR'
    _JSON_SUFFIXES = [".json"]
    
    def __init__(self):    
        self._loadLibrary()       


        
    @property
    def tipPosition(self) -> str:
        """True if the device is connected, False otherwise"""
        return self._tipPosition

    @tipPosition.setter
    def tipPosition(self, sPosition):
        self.self_tipPosition=sPosition

    def _tipCoordinates(self) ->str:
        return self.deckPosition[self.tipPosition]
    
    def _loadLibrary(self) ->bool:
        #
        filelist = []
        #
        if env(self._labware_env) is not None:
            self._labware_folder = Path(env(self._labware_env))        
        
        if self._labware_folder.is_dir():           
            for f in self._labware_folder.iterdir():
                if f.suffix in self._JSON_SUFFIXES:
                    filelist.append(f)            
        
        print("filelist contains %d .json files", filelist.count() )
        #
        for f in filelist:                
            data = json.load(f)
            
            

        return bOk

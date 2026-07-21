import os
from options.options_manager import OptionsManager
from pyresample.geometry import AreaDefinition

class GeoInfo:

    def __init__(self):
        file_opt = os.path.join(os.path.dirname(__file__), 'options/geoinfo.ini')
        self.manager = OptionsManager(file_opt, None)
        self.VALID = True
        if not self.manager.is_valid():
            print(f'[ERROR] Problem retrieving options from {file_opt}')
            self.VALID = False

    def get_area_definition(self,area_id):
        if not self.VALID:
            return None
        poptions, required_list = self.manager.get_retrieve_options('AREA_DEF_OPTIONS')
        area_info = self.manager.get_options_as_dict(area_id, poptions, required_list)
        for key in area_info:
            if area_info[key] is None:
                print(f'[ERROR] Option {key} not found in configuration file geoinfo.ini for area {area_id}')
                return None
        if area_info['width']<=0 or area_info['height']<=0:
            print(f'[ERROR] Options width and height must be greater than 0')
            return None
        extent = tuple(area_info['extent'])
        area_def = AreaDefinition(area_id, area_info['description'], area_info['proj_id'], area_info['projection'],
                                  area_info['width'], area_info['height'], extent)
        return area_def


from pyresample.geometry import GridDefinition,SwathDefinition,AreaDefinition
from pyresample.kd_tree import get_sample_from_neighbour_info, get_neighbour_info
import numpy as np
import math
from geoinfo import GeoInfo

class Resampler:
    def __init__(self):
        self.base_area_definition = None
        self.data_area_definition = None
        self.info_nn = {'valid_input_index':None,'valid_output_index':None,'index_array':None,'distance_array':None,'output_shape':None}


    def set_area_definitions_from_lat_lon_arrays(self,lat_base,lon_base,lat_data,lon_data,resolution=10000.0,n_neighbours=1):
        self.base_area_definition  = get_area_definition_from_lat_lon_arrays(lat_base,lon_base)
        self.data_area_definition  = get_area_definition_from_lat_lon_arrays(lat_data,lon_data)
        self.set_info_nn(resolution,n_neighbours,ny=len(lat_base),nx=len(lon_base))

    def set_area_definitions_from_area_ids(self,area_id_base,area_id_data,resolution=10000.0,n_neighbours=1):
        geo_info = GeoInfo()
        area_base = geo_info.get_area_definition(area_id_base)
        area_data = geo_info.get_area_definition(area_id_data)
        self.set_area_definitions(area_base,area_data,resolution,n_neighbours)

    def set_area_definitions(self,area_base,area_data,resolution=10000.0,n_neighbours=1):
        self.base_area_definition = area_base
        self.data_area_definition = area_data
        self.set_info_nn(resolution, n_neighbours)

    def set_info_nn(self,resolution,n_neighbours,ny=-1,nx=-1):

        if ny==-1 and nx==-1:
            ny = self.base_area_definition.height
            nx = self.base_area_definition.width
        info_nn_t = get_neighbour_info(self.data_area_definition, self.base_area_definition, resolution,neighbours=n_neighbours)
        self.info_nn['valid_input_index'] = info_nn_t[0]
        self.info_nn['valid_output_index'] = info_nn_t[1]
        self.info_nn['index_array'] = info_nn_t[2]
        self.info_nn['distance_array'] = info_nn_t[3]
        self.info_nn['output_shape'] = (ny,nx)

    def compute_nn_resampled_array(self,input_data):
        for key in self.info_nn:
            if self.info_nn[key] is None:
                return None


        output_data = get_sample_from_neighbour_info('nn',self.info_nn['output_shape'],input_data,self.info_nn['valid_input_index'],self.info_nn['valid_output_index'],self.info_nn['index_array'],self.info_nn['distance_array'],fill_value=None)

        return output_data

    def print_area_def_info(self,area_def):
        print('GRID SIZE:')
        print('Width: ', area_def.width)
        print('Height: ', area_def.height)

        print('RESOLUTION')
        print('Pixel Size X: ', area_def.pixel_size_x)
        print('Pixel Size Y: ', area_def.pixel_size_y)

        print('OUTER BOUNDARY CORNERS:')
        ob = area_def.outer_boundary_corners
        print('Upper Left: ', np.degrees(ob[0].lat), np.degrees(ob[0].lon))
        print('Upper Rigth: ', np.degrees(ob[1].lat), np.degrees(ob[1].lon))
        print('Lower Right: ', np.degrees(ob[2].lat), np.degrees(ob[2].lon))
        print('Lower Left ', np.degrees(ob[3].lat), np.degrees(ob[3].lon))

        print('MIDDLE POINTS: ')
        xmid = math.floor(area_def.width / 2)
        ymid = math.floor(area_def.height / 2)
        xend = area_def.width - 1
        yend = area_def.height - 1
        lon1, lat = area_def.get_lonlat_from_array_coordinates(xmid, 0)
        print('Upper Middle: ', lat, lon1)
        lon2, lat = area_def.get_lonlat_from_array_coordinates(xend, ymid)
        print('Right Middle: ', lat, lon2)
        lon3, lat = area_def.get_lonlat_from_array_coordinates(xmid, yend)
        print('Lower Middle: ', lat, lon3)
        lon4, lat = area_def.get_lonlat_from_array_coordinates(0, ymid)
        print('Left Middle: ', lat, lon4)
        lon5, lat5 = area_def.get_lonlat_from_array_coordinates(xmid, ymid)
        print('Middle: ', lat5, lon5)

        print('SPHERIC LIMITS:')
        lons = [np.degrees(ob[0].lon), np.degrees(ob[1].lon), np.degrees(ob[2].lon), np.degrees(ob[3].lon), lon1, lon2,
                lon3, lon4]
        lonmin = round(np.min(lons))
        lonmax = round(np.max(lons))
        if lonmin == -180 or lonmax == 180:
            lonmin = -180
            lonmax = 180
        latmin = lat
        lon, latmax = area_def.get_lonlat_from_array_coordinates(xmid, ymid)
        print('Lat min: ', latmin)
        print('Lat max: ', latmax)
        print('Lon min: ', lonmin)
        print('Lon max: ', lonmax)

def get_area_definition_from_lat_lon_arrays(lat_array,lon_array):
    projection = {'proj': 'eqc', 'lat_ts': 0, 'lat_0': 0, 'lon_0': 0, 'x_0': 0, 'y_0': 0, 'units': 'm', 'type': 'crs'}
    ny = len(lat_array)
    nx = len(lon_array)
    yspace = np.mean(np.diff(lat_array)) / 2
    xspace = np.mean(np.diff(lon_array)) / 2

    gd = AreaDefinition.from_extent('base', projection, [ny, nx],
                                    [np.min(lon_array) - xspace, np.min(lat_array) - yspace, np.max(lon_array) + xspace,
                                     np.max(lat_array) + yspace], units='degrees')
    return gd
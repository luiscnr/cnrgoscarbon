from pyresample.geometry import GridDefinition,SwathDefinition,AreaDefinition
from pyresample.kd_tree import get_sample_from_neighbour_info, get_neighbour_info
import numpy as np

class Resampler:
    def __init__(self):
        self.base_area_definition = None
        self.data_area_definition = None
        self.info_nn = {'valid_input_index':None,'valid_output_index':None,'index_array':None,'distance_array':None,'output_shape':None}


    def set_area_definitions_from_lat_lon_arrays(self,lat_base,lon_base,lat_data,lon_data,resolution=10000.0,n_neighbours=1):
        self.base_area_definition  = get_area_definition_from_lat_lon_arrays(lat_base,lon_base)
        self.data_area_definition  = get_area_definition_from_lat_lon_arrays(lat_data,lon_data)
        info_nn_t = get_neighbour_info(self.data_area_definition, self.base_area_definition,resolution, neighbours=n_neighbours)
        self.info_nn['valid_input_index'] = info_nn_t[0]
        self.info_nn['valid_output_index'] = info_nn_t[1]
        self.info_nn['index_array'] = info_nn_t[2]
        self.info_nn['distance_array'] = info_nn_t[3]
        self.info_nn['output_shape'] = (len(lat_base),len(lon_base))

    def compute_nn_resampled_array(self,input_data):
        for key in self.info_nn:
            if self.info_nn[key] is None:
                return None


        output_data = get_sample_from_neighbour_info('nn',self.info_nn['output_shape'],input_data,self.info_nn['valid_input_index'],self.info_nn['valid_output_index'],self.info_nn['index_array'],self.info_nn['distance_array'],fill_value=None)

        return output_data


def get_area_definition_from_lat_lon_arrays(lat_array,lon_array):
    projection = {'proj': 'eqc', 'lat_ts': 0, 'lat_0': 0, 'lon_0': 0, 'x_0': 0, 'y_0': 0, 'units': 'm', 'type': 'crs'}
    ny = len(lat_array)
    nx = len(lon_array)
    yspace = np.mean(np.diff(lat_array)) / 2
    xspace = np.mean(np.diff(lon_array)) / 2

    gd = AreaDefinition.from_extent('base', projection, [ny, nx],
                                    [np.min(lon_array) - xspace, np.min(lat_array) - yspace, np.max(lon_array) + xspace,
                                     np.max(lat_array) + yspace], units='degrees')

    # lat_points = np.zeros(ny)
    # yb = ny - 1
    # for y in range(ny):
    #     lat_points[yb] = gd.get_lonlat(y, 0)[1]
    #     yb = yb - 1
    # diff_lat = lat_array - lat_points
    # print(np.min(diff_lat), np.max(diff_lat))
    #
    # lon_points = np.zeros(nx)
    # for x in range(nx):
    #     lon_points[x] = gd.get_lonlat(0, x)[0]
    #
    # diff_lon = lon_array - lon_points
    # print(np.min(diff_lon), np.max(diff_lon))
    return gd
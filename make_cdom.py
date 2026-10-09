import argparse,os,time

import numpy as np
from netCDF4 import Dataset

import common_functions as cf
from cdom import CdomModel
from options.options_manager import OptionsManager
from datetime import timedelta
try:
    import xarray as xr
except ModuleNotFoundError:
    print(f'[ERROR] xarray is not installed. Please install the xarray module')

class OptionsCDOM:
    def __init__(self,config_file):
        file_opt = os.path.join(os.path.dirname(__file__),'options/cdom_options.ini')
        self.cmanager = OptionsManager(file_opt,None)
        self.omanager = OptionsManager(config_file,None)
        self.VALID = True
        if not self.cmanager.is_valid():
            print(f'[ERROR] Problem retrieving options from {file_opt}')
            self.VALID = False
        if not self.omanager.is_valid():
            print(f'[ERROR] Problem retrieving options from the configuration file {config_file}')
            self.VALID = False

    def get_options_as_dict(self,section):
        if not self.VALID:
            return None
        poptions,required_list = self.cmanager.get_retrieve_options(section)
        options_dict = self.omanager.get_options_as_dict(section,poptions,required_list)
        return options_dict


    def get_cdom_options(self):
        return self.get_options_as_dict('CDOM_DAILY')

class CDOMRun:
    def __init__(self,options_cdom):
        self.options_cdom = options_cdom

    def run_date(self,date_run):
        print(f'[INFO] Running CDOM for date {date_run}')
        file_out = cf.get_input_file(self.options_cdom['output_path'], self.options_cdom['output_file'], '%Y%j',
                                     date_run, create_sub_dirs=True, none_if_not_exists=False)
        if os.path.isfile(file_out) and not self.options_cdom['overwrite']:
            print(f'[WARNING] {file_out} already exists and overwrite is set to False. Skipping date {date_run.strftime("%Y-%m-%d")}')
            return


        list_files_format = self.options_cdom['list_files_format']
        list_files = self.options_cdom['list_files']
        list_var = self.options_cdom['list_var']
        n_var = len(list_var)
        array_out, valid_array, y_array, x_array, lat_array, lon_array= [None] * 6
        info_dims = None

        for ivar, var_name in enumerate(list_var):
            input_file_format = list_files_format[ivar] if len(list_files_format) == len(list_var) else list_files_format[0]
            input_file = list_files[ivar] if len(list_files) == len(list_var) else list_files[0]
            input_path_date = os.path.join(self.options_cdom['input_path'],date_run.strftime(self.options_cdom['input_path_organization']))
            input_path = os.path.join(input_path_date,input_file.replace('$DATE$',date_run.strftime(input_file_format)))
            if os.path.exists(input_path):

                dset = Dataset(input_path)
                if info_dims is None:
                    info_dims = cf.get_spatial_dims_arrays(None,dset)
                array_here = np.squeeze(dset.variables[var_name][:])
                if y_array is None and x_array is None and info_dims is not None:
                    y_array = dset.variables[info_dims['y_name']][:]
                    x_array = dset.variables[info_dims['x_name']][:]
                    if info_dims['lat_name'] is not None and info_dims['y_name']!=info_dims['lat_name']:
                        lat_array = dset.variables[info_dims['lat_name']][:]
                    if info_dims['lon_name'] is not None and info_dims['x_name']!=info_dims['lon_name']:
                        lon_array = dset.variables[info_dims['lon_name']][:]

                dset.close()
                if array_out is None:
                    array_out = np.ma.masked_all((n_var,) + array_here.shape)
                array_out[ivar, :] = array_here[:]
                if valid_array is None:
                    valid_array = np.where(array_here.mask == False, 1, 0)
                else:
                    valid_array = np.logical_and(valid_array, np.where(array_here.mask == False, 1, 0))
            else:
                print(f'[ERROR] File {input_path} is required but it is not available for running the daily CDOM')
                return
        if array_out is None:
            return

        indices_valid = np.where(valid_array == 1) if valid_array is not None else None
        n_valid = len(indices_valid[0])
        if indices_valid is not None:
            print(f'[INFO] Number of valid pixels common for all the bands: {n_valid}')
        cdom_array_2d = np.ma.masked_all(array_out.shape[1:], dtype=np.float64)
        if n_valid>0:
            indices_valid_by_band = [(np.array([x]).astype(np.int32),) + indices_valid for x in range(6)]
            cdomModel = CdomModel()
            nowstr = cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]], array_out[indices_valid_by_band[1]],
                                        array_out[indices_valid_by_band[2]], array_out[indices_valid_by_band[3]],
                                        array_out[indices_valid_by_band[4]], array_out[indices_valid_by_band[5]],date_here= date_run)
            cdom_array = cdomModel.run_model(nowstr=nowstr)
            if cdom_array is None:
                retries = 5
                index_retry = 1
                while index_retry<=retries:
                    print(f'[INFO] Waiting for 1 minute and retrying to run the CDOM model: {index_retry}....')
                    time.sleep(60)
                    cdom_array = cdomModel.run_model(nowstr=nowstr)
                    if cdom_array is not None:
                        break
                    index_retry = index_retry + 1
            if cdom_array is None:
                return
            cdom_array_2d[indices_valid] = cdom_array[:]

        acdom = xr.DataArray(
            cdom_array_2d,
            name="Acdom_sat",  # Name the variable in the xarray
            dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
            coords={info_dims['y_name']: y_array, info_dims['x_name']: x_array}  # Use the existing coordinates from the input data
        )

        acdom_dataset = None
        if lat_array is not None and lon_array is not None:
            ny = cdom_array_2d.shape[0]
            nx = cdom_array_2d.shape[1]
            if len(lat_array.shape)==2 and len(lon_array.shape)==2 and lat_array.shape==lon_array.shape and lat_array.shape==(ny,nx):
                xr_lat_array = xr.DataArray(lat_array,name='lat',dims=[info_dims['y_name'], info_dims['x_name']],
                                         coords={info_dims['y_name']: y_array, info_dims['x_name']: x_array})
                xr_lon_array = xr.DataArray(lon_array, name='lon', dims=[info_dims['y_name'], info_dims['x_name']],
                                            coords={info_dims['y_name']: y_array, info_dims['x_name']: x_array})

                acdom_dataset =xr.Dataset({
                    'Acdom-sat': acdom,
                    'lat': xr_lat_array,
                    'lon': xr_lon_array,
                })
            else:
                print(f'[ERROR] Dimensions of latitude ({lat_array.shape}) and longitude ({lon_array.shape}) arrays are inconsistent with the expected y,x dimensions {ny,nx}')
        else:
            acdom_dataset = xr.Dataset({'Acdom-sat': acdom})

        if acdom_dataset is not None:
            acdom_dataset.to_netcdf(file_out)
            print(f'[INFO] CDOM daily product for date {date_run.strftime("%Y-%m-%d")} was saved to {file_out}')
        else:
            print(f'[ERROR] CDOM daily product for date {date_run.strftime("%Y-%m-%d")} could not be saved to {file_out}')


def main(args_d):
    start_date = cf.get_date_arg(args_d['start_date'])
    end_date = cf.get_date_arg(args_d['end_date'])
    if start_date is None:
        return
    if end_date is None:
        end_date = start_date

    options = OptionsCDOM(args_d['config_file'])

    if not options.VALID:
        return

    cdom_options = options.get_cdom_options()
    if cdom_options is None:
        return

    work_date  = start_date
    while work_date <= end_date:
        print('[INFO] --------------------------------------------------------')
        cdom_run = CDOMRun(cdom_options)
        cdom_run.run_date(work_date)
        print('[INFO] --------------------------------------------------------')
        work_date = work_date + timedelta(days=1)


if __name__ == "__main__":
    print(f'[INFO] Started CNR-GOS Carbon tool!')
    print(f'[INFO] This is the script to generate CDOM products.')
    parser = argparse.ArgumentParser(description="CNR-GOS Carbon Tool: CDOM products")
    parser.add_argument("-v", "--verbose", help="Verbose mode.", action="store_true")
    parser.add_argument('-c', "--config_file", help="Config File.")
    #parser.add_argument('-only_datasets',"--only_get_datasets",help="Mode to retrieve the datasets without launching the DOD",action="store_true")
    parser.add_argument('-sd', "--start_date",help="Start date: YYYY-mm-dd")
    parser.add_argument('-ed', "--end_date", help="End date: YYYY-mm-dd")
    args = parser.parse_args()
    args_dict = vars(args)
    main(args_dict)
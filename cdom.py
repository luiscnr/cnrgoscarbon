import os
import subprocess
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
from composite import Composite
import common_functions as cf

def loisel2014_443(diffkd):
    slope,intercept,slopex,interceptx = [0.906040175463018, -0.5259306235301482, 0.9901899987526812, -0.05217938868943062]
    dp = np.power(10,(np.ma.log10(diffkd)*slope + intercept))
    x=diffkd-dp
    pacdom443 = np.power(10,(np.ma.log10(x)*slopex + interceptx))

    return pacdom443,x,dp,diffkd,slopex,interceptx

def check_input_data_arrays(array_412, array_443, array_490, array_510, array_560, array_670):
    check = True
    check = check & check_input_data_array(array_412,412)
    check = check & check_input_data_array(array_443,443)
    check = check & check_input_data_array(array_490,490)
    check = check & check_input_data_array(array_510,510)
    check = check & check_input_data_array(array_560,560)
    check = check & check_input_data_array(array_670,670)
    if not check:
        return False
    shape_ref = array_412.shape
    check = check & check_shape(array_443, shape_ref,443)
    check = check & check_shape(array_490, shape_ref,490)
    check = check & check_shape(array_510, shape_ref,510)
    check = check & check_shape(array_560, shape_ref,560)
    check = check & check_shape(array_670, shape_ref,670)

    return check


def check_input_data_array(array,wl_ref):
    if array is None:
        print(f'[ERROR] Input array at {wl_ref} nm is not available ')
        return False
    if not isinstance(array, np.ndarray):
        print(f'[ERROR] Input array at {wl_ref} nm is not a valid numpy array')
        return False
    return True

def check_shape(array,shape_ref,wl_ref):
    if array.shape != shape_ref:
        print(f'[ERROR] Array at {wl_ref} nm ({array.shape}) has a different shape than reference (wl=412 nm): ({shape_ref})')
        return False
    return True

def launch_multiple_cdom_files(input_date,info):
    if info['file_cdom'] is None:
        print(f'[ERROR] Option file_cdom with the format of the CDOM files including DATA key work is required')
        return None
    if info['input_path_cdom'] is None:
        info['input_path_cdom'] = info['input_path']
    if info['input_path_cdom_organization'] is None:
        info['input_path_cdom_organization'] = info['input_path_organization']
    info_cdom = info.copy()
    info_cdom['input_path'] = info['input_path_cdom']
    info_cdom['input_path_organization'] = info['input_path_cdom_organization']
    info_cdom['list_files'] = [info['file_cdom']]
    info_cdom['list_files_format'] = [info['file_cdom_format']]
    info_cdom['list_var'] = [info['var_cdom']]

    week = 0
    if 'week' in info and info['week'] is not None:
        week = int(info['week'])
    dates_key = f'dates_{int(week * (-1))}w'


    composite = Composite(input_date)
    composite.set_info_var_and_files(info_cdom)
    #print(composite.list_var,info_cdom['list_var'])
    check_files, file_ref, unavailable_files = composite.check_input_files()
    if len(unavailable_files)==0:
        info_dims = cf.get_spatial_dims_arrays(file_ref, None)

    if len(unavailable_files) > 0:
        for unavailable_date in unavailable_files:
            print(f'[INFO] Check CDOM for date: {unavailable_date}')
            input_date_here = dt.strptime(unavailable_date,'%Y-%m-%d')
            composite_day = Composite(input_date_here)
            info_day = info.copy()
            info_day['week'] = 0
            info_day['dates_0w'] = [0, 0]
            composite_day.set_info_var_and_files(info_day)
            check_files, file_ref, unavailable_files = composite_day.check_input_files()
            info_dims = cf.get_spatial_dims_arrays(file_ref, None)
            if check_files==2: ##there is availability
                array_out, indices_valid = composite_day.compute_composite()
                indices_valid_by_band = [(np.array([x]).astype(np.int32),) + indices_valid for x in range(6)]
                cdomModel = CdomModel()
                nowstr = cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]],
                                                      array_out[indices_valid_by_band[1]],
                                                      array_out[indices_valid_by_band[2]],
                                                      array_out[indices_valid_by_band[3]],
                                                      array_out[indices_valid_by_band[4]],
                                                      array_out[indices_valid_by_band[5]],
                                                      date_here=input_date)
                cdom_array = cdomModel.run_model(nowstr=nowstr)
                if cdom_array is None:
                    retries = 5
                    index_retry = 1
                    while index_retry <= retries:
                        print(f'[INFO] Waiting for 1 minute and retrying to run the CDOM model: {index_retry}....')
                        time.sleep(60)
                        cdom_array = cdomModel.run_model(nowstr=nowstr)
                        if cdom_array is not None:
                            break
                        index_retry = index_retry + 1
                if cdom_array is None:
                    return None

                cdom_array_2d = np.ma.masked_all(array_out.shape[1:], dtype=cdom_array.dtype)
                cdom_array_2d[indices_valid] = cdom_array[:]

                acdom = xr.DataArray(
                    cdom_array_2d,
                    name=info['var_cdom'],  # Name the variable in the xarray
                    dims=[info_dims['y_name'], info_dims['x_name']],
                    # Dimensions are assumed to be latitude and longitude
                    coords={info_dims['y_name']: info_dims['y_array'], info_dims['x_name']: info_dims['x_array']}
                    # Use the existing coordinates from the input data
                )
                if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
                    acdom['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
                    acdom['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

                file_out = cf.get_input_file(info['input_path_cdom'], info['file_cdom'], info['file_cdom_format'], input_date_here,
                                          create_sub_dirs=True, none_if_not_exists=False)
                acdom.to_netcdf(file_out)
                print(f'[INFO] CDOM composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

        check_files, file_ref, unavailable_files = composite.check_input_files()
    if check_files==0:
        print(f'[ERROR] No daily CDOM files are available and could not be created.')
        return None
    if check_files==1:
        print(f'[WARNING] Some of the daily files are not available for the composite.')

    array_out, indices_valid = composite.compute_composite()



    acdom = xr.DataArray(
        np.squeeze(array_out),
        name="Acdom_sat",  # Name the variable in the xarray
        dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
        coords={info_dims['y_name']: info_dims['y_array'], info_dims['x_name']: info_dims['x_array']}
        # Use the existing coordinates from the input data
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        acdom['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        acdom['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

    input_date_week = input_date
    if week == -1:
        input_date_week = input_date - timedelta(days=8)
    elif week == -2:
        input_date_week = input_date - timedelta(days=16)
    file_out = cf.get_input_file(info['output_path'], info['output_file'], '%Y%j', input_date_week, create_sub_dirs=True,
                              none_if_not_exists=False)
    acdom.to_netcdf(file_out)
    print(f'[INFO] CDOM composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out

    return False


class CdomModel:
    def __init__(self):


        self.input_df = None ##input data frame, including NaN
        self.input_file = None ##input file used in the script, should be input_df without NaN
        self.output_file = None ##output file in the script

        path_base = os.path.dirname(os.path.abspath(__file__))
        self.path_model = os.path.join(path_base,'mCDOM_mDOC')

        self.path_data = os.path.join(os.path.dirname(path_base),'aCDOM_results') ##path to save self.input_file and self.output_file if they are not given



    def set_df_from_arrays(self,array_412,array_443,array_490,array_510,array_560,array_670,date_here = None):
        if not check_input_data_arrays(array_412,array_443,array_490,array_510,array_560,array_670):
            return None
        os.makedirs(self.path_data,exist_ok=True)
        if not os.path.isdir(self.path_data):
            print(f'[ERROR] Path data {self.path_data} does not exist and could not be created. Review writing permissions.')
            return None

        # make sure arrays are flatten
        if len(array_412.shape) > 2:
            array_412 = array_412.flatten()
            array_443 = array_443.flatten()
            array_490 = array_490.flatten()
            array_510 = array_510.flatten()
            array_560 = array_560.flatten()
            array_670 = array_670.flatten()

        self.input_df = pd.DataFrame(
            {'id': np.arange(np.size(array_412)),
             '412': array_412,
             '443': array_443,
             '490': array_490,
             '510': array_510,
             '560': array_560,
             '670': array_670,
             'theta': [1] * len(array_412)
             }
        )

        # drop rows with NaN
        df1 = self.input_df.dropna()
        print(f'[INFO] Number of data in arrays: {len(self.input_df.index)}. After dropping NaN values: {len(df1.index)}')

        # Save the clean DataFrame to CSV
        nowstr = str(dt.now().timestamp()).replace('.', '')
        date_here_str = date_here.strftime('%Y%m%d') if date_here is not None else ''
        nowstr = f'{date_here_str}_{nowstr}'

        self.input_file = os.path.join(self.path_data, f'input_data_acdom_{nowstr}.csv')
        print(f'[INFO] Saving data to {self.input_file}')
        df1.to_csv(self.input_file, sep=' ', header=None, index=None)

        return nowstr



    def check_run_model(self):

        if not os.path.isdir(self.path_model):
            print(f'[ERROR] Path model {self.path_model} is not available')
            return False

        if not os.path.isfile(self.input_file):
            print(f'[ERROR] Input file {self.input_file} does not exist.')
            return False

        return True

    def run_model(self,output_file=None,date_here = None,nowstr=None):

        if nowstr is None:
            date_here_str = date_here.strftime('%Y%m%d') if date_here is not None else ''
            nowstr = str(dt.now().timestamp()).replace('.','')
            nowstr = f'{date_here_str}_{nowstr}'

        if output_file is None:
            self.output_file = os.path.join(self.path_data,f'output_data_acdom_{nowstr}.csv')
        else:
            self.output_file = output_file

        if self.input_file is None:
            self.input_file = os.path.join(self.path_data,f'input_data_acdom_{nowstr}.csv')

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        if not os.path.isdir(os.path.dirname(self.output_file)):
            print(f'[ERROR] Path data {os.path.dirname(self.output_file)} does not exist and could not be created. Review writing permissions.')
            return None
        if not self.check_run_model():
            return None



        print(f'[INFO] aCDOM Model: Started')
        path = os.path.join(self.path_model,'acdom_codeCo/SRC')
        subprocess.call(["gcc", "-c", "function_acdom.c", "-Wall", "-g"], cwd=path)
        subprocess.call(["gcc", "-c", "neuron_difKd_443.c", "-Wall", "-g"], cwd=path)
        subprocess.call(["gcc", path + "/Test_calc_Dif443.c", "-o", "Test_calc_Dif443", "function_acdom.o", "neuron_difKd_443.o", "-lm", "-Wall", "-g","-fcommon"], cwd=path)
        print(f'[INFO] Compilation done. Running using the input file: {self.input_file}')
        os.chdir(path)
        try:
            subprocess.check_call(['./Test_calc_Dif443',self.input_file,self.output_file])
            print(f'[INFO] aCDOM Model: Finished. Output saved to: {self.output_file}')
        except Exception as e:
            print(f'[ERROR] aCDOM Model: Failed computing dkd443. Error raised: {e}')
            print(f'[ERROR] Removed input file: {self.input_file}')
            os.remove(self.input_file)
            return None
        print(f'[INFO] Computing acdom 443 using Loisel algorithm...')
        df_kd = pd.read_csv(self.output_file, na_values=-999, sep=' ')
        dkd443 = np.ma.array(df_kd.DiffKd443)
        acdom443_sat, _, _, _, _, _ = loisel2014_443(dkd443)
        print(f'[INFO] ACDOM 443 computed')



        if len(self.input_df.index)==len(acdom443_sat):
            pass
        else:
            print(f'[INFO] Getting array with the original shape')
            df1 = pd.read_csv(self.input_file, na_values=-999, sep=' ')
            acdom_df = pd.DataFrame({
                'id': df1['id'].values,  # Use the original 'id' from the clean DataFrame
                'acdom_sat': acdom443_sat
            })
            self.input_df = self.input_df.merge(acdom_df, on='id', how='left')
            acdom443_sat = np.array(self.input_df['acdom_sat'])

        print(f'[INFO] Removing temporary csv files')
        os.remove(self.input_file)
        os.remove(self.output_file)

        return acdom443_sat


        
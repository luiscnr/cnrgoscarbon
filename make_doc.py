import argparse
import os.path

from netCDF4 import Dataset
from pandas.core.groupby import generic

import common_functions as cf
from datetime import timezone,timedelta
from datetime import datetime as dt
import numpy as np
import xarray as xr
from cdom import CdomModel
from options.options_manager import OptionsManager


from composite import Composite
from Run_CLA.Run_classification import classification
from Run_DOC import Run_DOC_model
from resampler import Resampler

class OptionsDOC:
    def __init__(self,config_file):
        file_opt = os.path.join(os.path.dirname(__file__),'options/doc_options.ini')
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

    def get_general_model_options(self):
        return self.get_options_as_dict('DOC_MODEL')


def get_datasets(general_model_options,input_date):
    date_minus_1w = input_date - timedelta(days=8)
    date_minus_2w = input_date - timedelta(days=16)
    datasets = {
        "CHL-1w": [get_input_file(general_model_options['path_chl'],general_model_options['file_chl'],general_model_options['format_file_chl'],date_minus_1w,ref='CHL-1w')],  # Chlorophyll data for one week before the target date.
        "SST-1w": [get_input_file(general_model_options['path_sst'],general_model_options['file_sst'],general_model_options['format_file_sst'],date_minus_1w,ref='SST-1w')],  # Sea Surface Temperature data for one week before the target date.
        "MLD-1w": [get_input_file(general_model_options['path_mld'],general_model_options['file_mld'],general_model_options['format_file_mld'],date_minus_1w,ref='MLD-1w')],  # Mixed Layer Depth data for one week before the target date.
        "CDOM-2w": [get_input_file(general_model_options['path_cdom'],general_model_options['file_cdom'],general_model_options['format_file_cdom'],date_minus_2w,ref='CDOM-2w')],  # CDOM data for two weeks before the target date.
        "CDOM": [get_input_file(general_model_options['path_cdom'],general_model_options['file_cdom'],general_model_options['format_file_cdom'],input_date,ref='CDOM')],  # CDOM data for the target date.
        "CandP": [get_input_file(general_model_options['path_class'],general_model_options['file_class'],general_model_options['format_file_class'],input_date,ref='CandP')]  # 'Class_and_Prob' dataset for the target date.
    }


    return datasets

def get_input_file(input_path,name_file,name_file_date_format,date_here,ref='',none_if_not_exists=True):
    name_file = name_file.replace('$DATE$',date_here.strftime(name_file_date_format))
    folder_format = '%Y/%j'
    input_file = os.path.join(input_path,date_here.strftime(folder_format),name_file)
    if os.path.isfile(input_file):
        return input_file
    else:
        if none_if_not_exists:
            print(f'[WARNING] Input file {input_file} for dataset {ref} is not available')
            return None
        else:
            return input_file

def run_dataset(dataset_type,input_date,options):
    date_minus_1w = input_date - timedelta(days=8)
    date_minus_2w = input_date - timedelta(days=16)
    if dataset_type == 'CandP':
        print(f'[INFO] Starting production of Classification and Probability Dataset for date: {input_date.strftime("%Y-%m-%d")}')
        return run_classification(options,input_date)

    if dataset_type == 'SST-1w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of SST composite for date: {date_minus_1w.strftime("%Y-%m-%d")}')
        return run_sst(options, date_minus_1w)

    if dataset_type == 'CDOM-2w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of CDOM composite for date: {date_minus_2w.strftime("%Y-%m-%d")}')
        return run_cdom(options, date_minus_2w)

    if dataset_type == 'CDOM':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of CDOM composite for date: {input_date.strftime("%Y-%m-%d")}')
        return run_cdom(options, date_minus_2w)

    return None

def run_cdom(options,input_date):
    info = options.get_options_as_dict('CDOM_COMPOSITE')
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)
    lat_base, lon_base = [None]*2
    file_ref = composite.get_file_ref()
    if file_ref is not None:
        if 'resampler' in info:
            lat_base, lon_base, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
            composite.resampler = resampler
        else:
            lat_base, lon_base = get_lat_long_arrays(file_ref)
    cdomModel = CdomModel()
    cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]], array_out[indices_valid_by_band[1]], array_out[indices_valid_by_band[2]],array_out[indices_valid_by_band[3]], array_out[indices_valid_by_band[4]], array_out[indices_valid_by_band[5]])
    cdom_array = cdomModel.run_model()
    cdom_array_2d = np.ma.masked_all(array_out.shape[1:],dtype=cdom_array.dtype)
    cdom_array_2d[indices_valid] = cdom_array[:]

    acdom = xr.DataArray(
        cdom_array_2d,
        name="Acdom_sat",  # Name the variable in the xarray
        dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
        coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    )

    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', input_date, none_if_not_exists=False)
    acdom.to_netcdf(file_out)
    print(f'[INFO] CDOM composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out

def run_sst(options,input_date):
    info = options.get_options_as_dict('SST_COMPOSITE')
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)
    check_files,unavailable_files = composite.check_input_files()
    if check_files==0 and options['download'] is None:
        print(f'[ERROR] Files to compute the SST composite are not available.')
        return None
    file_ref = composite.get_file_ref()
    if file_ref is not None:
        if 'resampler' in info:
            lat_base,lon_base,resampler = get_resampler_from_info_and_file_ref(info,file_ref,input_date)
            composite.resampler = resampler
        else:
            lat_base,lon_base = get_lat_long_arrays(file_ref)


    array_out, indices_valid = composite.compute_composite()
    sst = xr.DataArray(
        np.squeeze(array_out),
        name="SST",  # Name the variable in the xarray
        dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
        coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    )
    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', input_date, none_if_not_exists=False)
    sst.to_netcdf(file_out)
    print(f'[INFO] SST composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out

def get_resampler_from_info_and_file_ref(info,file_ref,input_date):
    resampler = info['resampler']
    date_format = resampler[2] if len(resampler) == 3 else '%Y%j'
    file_base = get_input_file(resampler[0], resampler[1], date_format, input_date)
    lat_base,lon_base = get_lat_long_arrays(file_base)
    lat_data,lon_data = get_lat_long_arrays(file_ref)
    resampler = Resampler()
    resampler.set_area_definitions_from_lat_lon_arrays(lat_base, lon_base, lat_data, lon_data)

    return lat_base,lon_base,resampler

def get_lat_long_arrays(file_nc):
    dset = Dataset(file_nc)
    lat_array = dset.variables['lat'][:]
    lon_array = dset.variables['lon'][:]
    dset.close()
    return lat_array,lon_array

def run_classification(options,input_date):

    info = options.get_options_as_dict('CLASS_COMPOSITE')
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)
    array_out,indices_valid = composite.compute_composite()
    shape_out = array_out.shape[1:]
    shape_out_prob = shape_out + (17,)
    valid_array = np.zeros(shape_out).astype(np.bool)

    valid_array[indices_valid] = True
    valid_array_prob = np.tile(valid_array.flatten(),17).reshape((17,shape_out[0],shape_out[1]))
    valid_array_prob = np.moveaxis(valid_array_prob,0,2)

    print(f'[INFO] Running classification...')
    C, P, flag1, flag2, flag3, flag4 = classification(array_out[0,:].flatten(),array_out[1,:].flatten(),array_out[2,:].flatten(),array_out[3,:].flatten(),array_out[4,:].flatten(),array_out[5,:].flatten())


    class_array = np.ma.array(np.reshape(C,shape_out))
    class_array[valid_array==False] = np.ma.masked
    P = np.moveaxis(P,0,1)
    prob_array =  np.ma.array(np.reshape(P,shape_out_prob))
    prob_array[valid_array_prob==False] = np.ma.masked
    flag1_array = np.ma.array(np.reshape(flag1,shape_out))
    flag1_array[valid_array==False] = np.ma.masked
    flag2_array = np.ma.array(np.reshape(flag2,shape_out))
    flag2_array[valid_array==False] = np.ma.masked
    flag3_array = np.ma.array(np.reshape(flag3,shape_out))
    flag3_array[valid_array==False] = np.ma.masked
    flag4_array = np.ma.array(np.reshape(flag4,shape_out))
    flag4_array[valid_array==False] = np.ma.masked
    class_array = np.ma.masked_invalid(class_array)
    prob_array = np.ma.masked_invalid(prob_array)
    flag1_array = np.ma.masked_invalid(flag1_array)
    flag2_array = np.ma.masked_invalid(flag2_array)
    flag3_array = np.ma.masked_invalid(flag3_array)
    flag4_array = np.ma.masked_invalid(flag4_array)
    pclass = np.arange(17).astype(np.int8)

    print(f'[INFO] Running classification: Completed')

    file_ref = composite.get_file_ref()
    dset = Dataset(file_ref)
    lat = dset.variables['lat'][:]
    lon = dset.variables['lon'][:]
    dset.close()
    dataset_out = xr.Dataset(
        {
            "Class": (["lat", "lon"], class_array),
            "Probability": (["pclass", "lat", "lon"], np.moveaxis(prob_array,2,0)),
            "Flag1": (["lat", "lon"], flag1_array),
            "Flag2": (["lat", "lon"], flag2_array),
            "Flag3": (["lat", "lon"], flag3_array),
            "Flag4": (["lat", "lon"], flag4_array),
        },
        coords={
            "lat": lat,
            "lon": lon,
            "pclass": pclass
        }
    )

    file_out = get_input_file(info['output_path'],info['output_file'],'%Y%j',input_date,none_if_not_exists=False)
    dataset_out.to_netcdf(file_out)
    print(f'[INFO] Dataset Classification and Probability saved to {file_out}')

    return file_out

def main(args_d):
    input_date = cf.get_date_arg(args_d['date'])
    if input_date is None:
        input_date = dt.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc) - timedelta(days=1)

    options = OptionsDOC(args_d['config_file'])
    general_model_options = options.get_general_model_options()

    ##Getting output file
    output_file = get_input_file(general_model_options['output_path'], general_model_options['output_file'], '%Y%j', input_date,none_if_not_exists=False)
    output_path_date = os.path.dirname(output_file)
    try:
        os.makedirs(output_path_date, exist_ok=True)
    except OSError as e:
        print(f'[ERROR] Output path {output_path_date} does not exist and could not be created. Exception: {e}. Please review permissions')
        return

    dataset_dict = get_datasets(general_model_options,input_date)
    for dataset in dataset_dict:
        if dataset_dict[dataset] is None:
            file_out = run_dataset(dataset,input_date,options)
            if os.path.isfile(file_out) and file_out is not None:
                dataset_dict[dataset] = [file_out]
                print(f'[INFO] Dataset {dataset}->{file_out}')
            else:
                print(f'[ERROR] Dataset {dataset} is not available and could not be created. DOC will not be created.')
                return
        else:
            print(f'[INFO] Dataset {dataset}->{dataset_dict[dataset][0]}')

    print(f'[INFO] All the required datasets are available for date: {input_date.strftime("%Y-%m-%d")}')

    if args_d['only_get_datasets']:
        return

    ## Call the Run_DOC_model function, passing the datasets and the current date as arguments to compute the DOC values
    print(f'[INFO] Running the DOC model...')
    DOC = Run_DOC_model(dataset_dict, input_date)

    # Save the DOC and DOC_abc datasets as netCDF files in the folder path.
    DOC.to_netcdf(output_file)  # Save the DOC dataset to a netCDF file
    print(f'[INFO] DOC model saved to {output_file}')

    # from composite import Composite
    # date_minus_2w = input_date - timedelta(days=16)
    # info = {
    #     'input_path': '/mnt/c/DATA/INPUT_MULTI_MED',
    #     'list_files': ['X$DATE$-rrs412-med-hr.nc','X$DATE$-rrs443-med-hr.nc','X$DATE$-rrs490-med-hr.nc','X$DATE$-rrs510-med-hr.nc',
    #                    'X$DATE$-rrs555-med-hr.nc','X$DATE$-rrs670-med-hr.nc'],
    #     'list_var': ['RRS412','RRS443','RRS490','RRS510','RRS555','RRS670']
    # }
    # composite = Composite(date_minus_2w)
    # composite.set_info_var_and_files(info)
    # check,unavailable_dates = composite.check_input_files()
    # print(check, unavailable_dates)
    # input_file_ref = os.path.join(info['input_path'],date_minus_2w.strftime('%Y'),date_minus_2w.strftime('%j'),info['list_files'][0])
    #
    # input_file_ref = input_file_ref.replace('$DATE$',date_minus_2w.strftime('%Y%j'))
    # dataset = Dataset(input_file_ref)
    # lat_base = dataset.variables['lat'][:]
    # lon_base = dataset.variables['lon'][:]
    # dataset.close()

    ##cdom base on composite date_minus_2w
    # composite = Composite(date_minus_2w)
    # composite.set_info_var_and_files(info)
    # array_out,indices_valid = composite.compute_composite()
    # indices_valid_by_band = [(np.array([x]).astype(np.int32),)+indices_valid for x in range(6)]
    # cdomModel = CdomModel()
    # cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]], array_out[indices_valid_by_band[1]], array_out[indices_valid_by_band[2]],
    #                              array_out[indices_valid_by_band[3]], array_out[indices_valid_by_band[4]], array_out[indices_valid_by_band[5]])
    # cdom_array = cdomModel.run_model()
    # cdom_array_2d = np.ma.masked_all(array_out.shape[1:],dtype=cdom_array.dtype)
    # cdom_array_2d[indices_valid] = cdom_array[:]
    #
    # acdom = xr.DataArray(
    #     cdom_array_2d,
    #     name="Acdom_sat",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    # file_acdom = os.path.join(info['input_path'],date_minus_2w.strftime('%Y'),date_minus_2w.strftime('%j'),f'acdom_{date_minus_2w.strftime("%Y%j")}_-8D.nc')
    # acdom.to_netcdf(file_acdom)

    ##cdom composite 8D input date
    # composite = Composite(input_date)
    # composite.set_info_var_and_files(info)
    # array_out,indices_valid = composite.compute_composite()
    # if array_out is None:
    #     return
    # indices_valid_by_band = [(np.array([x]).astype(np.int32),)+indices_valid for x in range(6)]
    # cdomModel = CdomModel()
    # cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]], array_out[indices_valid_by_band[1]], array_out[indices_valid_by_band[2]],
    #                              array_out[indices_valid_by_band[3]], array_out[indices_valid_by_band[4]], array_out[indices_valid_by_band[5]])
    # cdom_array = cdomModel.run_model()
    # cdom_array_2d = np.ma.masked_all(array_out.shape[1:],dtype=cdom_array.dtype)
    # cdom_array_2d[indices_valid] = cdom_array[:]
    #
    # acdom = xr.DataArray(
    #     cdom_array_2d,
    #     name="Acdom_sat",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    # file_acdom = os.path.join(info['input_path'],input_date.strftime('%Y'),input_date.strftime('%j'),f'acdom_{input_date.strftime("%Y%j")}_-8D.nc')
    # acdom.to_netcdf(file_acdom)

    ##chl-8days composite for dates_minus-1w
    # info_chl = {
    #     'input_path': '/mnt/c/DATA/INPUT_MULTI_MED',
    #     'list_files': ['X$DATE$-chl-med-hr.nc'],
    #     'list_files_format': ['%Y%j'],
    #     'list_var': ['CHL']
    # }
    # composite = Composite(date_minus_1w)
    # composite.set_info_var_and_files(info_chl)
    # array_out, indices_valid = composite.compute_composite()
    # chl = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="CHL",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    # file_chl_out = os.path.join(info_chl['input_path'],date_minus_1w.strftime('%Y'),date_minus_1w.strftime('%j'),f'chl_{date_minus_1w.strftime("%Y%j")}_-8D.nc')
    # chl.to_netcdf(file_chl_out)

    ##sst 8-days composite for date_minus-1w
    # file_sst = '/mnt/c/DATA/SST/2026/143/temp_model_20260523_med.nc'
    # dset = Dataset(file_sst)
    # lat_sst = dset.variables['lat'][:]
    # lon_sst = dset.variables['lon'][:]
    # dset.close()
    # resampler = Resampler()
    # resampler.set_area_definitions_from_lat_lon_arrays(lat_base, lon_base, lat_sst, lon_sst)
    # info_sst = {
    #     'input_path': '/mnt/c/DATA/SST',
    #     'list_files': ['temp_model_$DATE$_med.nc'],
    #     'list_files_format': ['%Y%m%d'],
    #     'list_var': ['thetao'],
    #     'resampler': resampler
    # }
    # composite = Composite(date_minus_1w)
    # composite.set_info_var_and_files(info_sst)
    # array_out, indices_valid = composite.compute_composite()
    # sst = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="sst",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    # file_sst_out = os.path.join(info_sst['input_path'],date_minus_1w.strftime('%Y'),date_minus_1w.strftime('%j'),f'sst_{date_minus_1w.strftime("%Y%j")}_-8D.nc')
    # sst.to_netcdf(file_sst_out)

    ##mld -8 days for date_minus_-1w
    # file_mld = '/mnt/c/DATA/SST/2026/143/20260523_d-CMCC--AMXL-MFSeas10-MEDATL.nc'
    # dset = Dataset(file_mld)
    # lat_mld = dset.variables['lat'][:]
    # lon_mld = dset.variables['lon'][:]
    # dset.close()
    # resampler_mld = Resampler()
    # resampler_mld.set_area_definitions_from_lat_lon_arrays(lat_base, lon_base, lat_mld, lon_mld)
    # info_mld = {
    #     'input_path': '/mnt/c/DATA/SST',
    #     'list_files': ['$DATE$_d-CMCC--AMXL-MFSeas10-MEDATL.nc'],
    #     'list_files_format': ['%Y%m%d'],
    #     'list_var': ['mlotst'],
    #     'resampler': resampler_mld
    # }
    # composite = Composite(date_minus_1w)
    # composite.set_info_var_and_files(info_mld)
    # array_out, indices_valid = composite.compute_composite()
    # mld = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="mld",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat": lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    # file_mld_out = os.path.join(info_mld['input_path'], date_minus_1w.strftime('%Y'), date_minus_1w.strftime('%j'),
    #                             f'mld_{date_minus_1w.strftime("%Y%j")}_-8D.nc')
    # mld.to_netcdf(file_mld_out)



if __name__ == "__main__":
    print(f'[INFO] Started CNR-GOS Carbon tool!')
    parser = argparse.ArgumentParser(description="CNR-GOS Carbon Tool")
    parser.add_argument("-v", "--verbose", help="Verbose mode.", action="store_true")
    parser.add_argument('-c', "--config_file", help="Config File.")
    parser.add_argument('-only_datasets',"--only_get_datasets",help="Mode to retrieve the datasets without launching the DOD",action="store_true")
    parser.add_argument('-d', "--date",help="Input Date: YYYY-mm-dd")
    args = parser.parse_args()
    args_dict = vars(args)
    main(args_dict)


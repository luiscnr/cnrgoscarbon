import argparse
import os
from netCDF4 import Dataset
import common_functions as cf
from datetime import timedelta,timezone
from datetime import datetime as dt
import numpy as np
try:
    import xarray as xr
except ModuleNotFoundError:
    print(f'[ERROR] xarray is not installed. Please install the xarray module')
from cdom import CdomModel
import cdom as cdom_main
from options.options_manager import OptionsManager
from composite import Composite
from Run_CLA.Run_classification import classification
from Run_DOC import Run_DOC_model
from resampler import Resampler
from download import  LaunchDownload
from geoinfo import  GeoInfo

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

    def get_download_options(self,section):
        if not self.VALID:
            return None
        poptions,required_list = self.cmanager.get_retrieve_options('DOWNLOAD')
        options_dict = self.omanager.get_options_as_dict(section,poptions,required_list)

        return options_dict


class DOCWritter:
    def __init__(self,file_out,file_ref,date_product):
        self.file_out = file_out
        self.ncout = None
        dir_name = os.path.dirname(file_out)
        try:
            os.makedirs(dir_name,exist_ok=True)
        except OSError as ex:
            print(f'[ERROR] {dir_name} is not a valid directory and could not be created. Please review permissions. Error: {ex}')


        if os.path.isdir(dir_name):
            try:
                self.ncout = Dataset(file_out,'w')
            except Exception as ex:
                print(f'[ERROR][DOCWritter] Output dataset with file name {file_out} could not be started. Exception: {ex}')
                self.ncout = None

        self.file_ref = file_ref
        if file_ref is not None and os.path.isfile(file_ref):
            try:
                dset = Dataset(file_ref)
                self.global_attrs = dset.__dict__
                self.time_attrs = dset.variables['time'].__dict__
                self.lat_attrs = dset.variables['lat'].__dict__
                self.lon_attrs = dset.variables['lon'].__dict__
                dset.close()
            except Exception as ex:
                print(f'[ERROR][DOCWritter] Exception checking the reference file: {file_ref}. Exception: {ex}')
                self.ncout = None

        self.ny, self.nx, self.ntimes = -1,-1,1
        self.date_product = date_product

    def set_dimensions(self,doc_array):
        if len(doc_array.shape)==3 and doc_array.shape[0]==1:
            self.ny = doc_array.shape[1]
            self.nx = doc_array.shape[2]
        elif len(doc_array.shape)==2:
            self.ny = doc_array.shape[0]
            self.nx = doc_array.shape[1]

    def create_dimensions(self):
        if self.ncout is None:
            return False
        if self.ny==-1 or self.nx==-1:
            print(f'[ERROR][DOCWritter] Dimensions ny (for latitude) and nx (for longitude) are not valid. Please use first set_dimensions(doc_array) in your code')
            return False
        self.ncout.createDimension('time',self.ntimes)
        self.ncout.createDimension('lat', self.ny)
        self.ncout.createDimension('lon', self.nx)

        return True
    def create_time_variable(self):
        if self.ncout is None:
            return False
        time_var = self.ncout.createVariable('time','i4',('time',),zlib=True,complevel=6)
        time_var.setncatts(self.time_attrs)
        time_var[0] = int((self.date_product.replace(hour=0,minute=0,second=0,microsecond=0)-dt(1981,1,1,0,0,0,0)).total_seconds())
        return True

    def create_lat_variable(self,lat_array):
        if self.ncout is None:
            return False
        if lat_array.shape[0]!=self.ny:
            print(f'[ERROR][DOCWriter] Inconsistency between the size of the latitude array {lat_array.shape[0]} and the expected lat dimension {self.ny}')
            return False
        lat_var = self.ncout.createVariable('lat', 'f4', ('lat',), zlib=True, complevel=6)
        lat_var.setncatts(self.lat_attrs)
        lat_var[:] = lat_array[:]
        return True

    def create_lon_variable(self,lon_array):
        if self.ncout is None:
            return False
        if lon_array.shape[0]!=self.nx:
            print(f'[ERROR][DOCWriter] Inconsistency between the size of the longitude array {lon_array.shape[0]} and the expected lon dimension {self.nx}')
            return False
        lon_var = self.ncout.createVariable('lon', 'f4', ('lon',), zlib=True, complevel=6)
        lon_var.setncatts(self.lon_attrs)
        lon_var[:] = lon_array[:]
        return True

    def create_doc_variable(self,doc_array):
        doc_var = self.ncout.createVariable('DOC','f4',('time','lat','lon'),complevel=6,zlib=True,fill_value=-999.0)
        doc_var.standard_name = 'mole_concentration_of_dissolved_organic_carbon_in_sea_water'
        doc_var.long_name = 'Dissolved Organic Carbon concentration'
        doc_var.type = 'surface'
        doc_var.units = 'µmol L-1'
        doc_var.missing_value = -999.0
        if doc_array is None:
            shape_out = (1, self.ny, self.nx)
            doc_array = np.ma.masked_all(shape_out, np.float32)

        if doc_array is not None:
            if len(doc_array.shape)==2 and doc_array.shape[0]==self.ny and doc_array.shape[1]==self.nx:
                doc_array = np.ma.expand_dims(doc_array,0)
                doc_var[:] = doc_array[:]
            if len(doc_array.shape) == 3 and doc_array.shape==(1,self.ny,self.nx):
                doc_var[:] = doc_array[:]
            else:
                print(f'[ERROR] Dimensions of DOC array {doc_array.shape} are inconsistent with the expected in the variable {doc_var.shape}')
                return False

        return True

    def add_global_variables(self,source_files=''):
        self.ncout.setncatts(self.global_attrs)
        self.ncout.source_files = source_files
        now = dt.now().astimezone(timezone.utc)
        self.ncout.creation_date = now.strftime('%a %b %d %Y')
        self.ncout.creation_time = now.strftime('%H:%M:%S')

    def close_and_remove(self):
        if self.ncout is not None:
            try:
                self.close_file()
            except Exception as ex:
                print(f'[ERROR][DOCWritter] Error while closing the output file {self.file_out}. Exception: {ex}')
        try:
            os.remove(self.file_out)
        except Exception as ex:
            print(f'[ERROR][DOCWritter] Error while trying to remove the output file {self.file_out}. Exception: {ex}')
            return


    def close_file(self):
        if self.ncout is None:
            return
        self.ncout.close()


def get_datasets(general_model_options,options,input_date):
    ##fechas para buscar datasets, siempre 0, -8, -16
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

def get_date_week(input_date,week):
    if week == -1:
        output_date = input_date - timedelta(days=8)
    elif week==-2:
        output_date = input_date - timedelta(days=16)
    else:
        output_date = input_date
    return output_date


# def get_date_for_dataset_and_week(input_date,dataset,week,options):
#
#     options_dataset = options.get_options_as_dict(f'{dataset}_COMPOSITE')
#     key_dates = f'dates_{int(week)}w'
#     dates_values = options_dataset[key_dates]
#     if len(dates_values) == 2:  ##start and end dates are already defined
#
#         date_real = input_date + timedelta(days=dates_values[1])
#     else:
#         date_real = input_date + timedelta(days=dates_values[0])
#     return date_real


##Prepare the mask
def get_mask_from_input_datasets(input_datasets):
    name_variable_by_dataset = ['CHL','SST','MLD','Acdom_sat','Acdom_sat','Class']
    output_mask = None
    for index_dataset,input_dataset in enumerate(input_datasets):
        input_file = input_datasets[input_dataset][0]
        dset = Dataset(input_file)
        name_var = name_variable_by_dataset[index_dataset]
        array = dset.variables[name_var][:]
        if output_mask is None:
            output_mask = array.mask
        else:
            output_mask = output_mask | array.mask

        dset.close()
    print(f'[INFO] Number of masked pixels: {np.sum(output_mask)}. Valid: {np.sum(output_mask==False)} ({(np.sum(output_mask==False)/output_mask.size)*100:.2f}%)')

    return output_mask


def get_input_file(input_path,name_file,name_file_date_format,date_here,ref='',none_if_not_exists=True,create_sub_dirs=False):
    name_file = name_file.replace('$DATE$',date_here.strftime(name_file_date_format))
    folder_format = '%Y/%j'
    input_path_date = os.path.join(input_path,date_here.strftime(folder_format))
    if not os.path.isdir(input_path_date) and create_sub_dirs:##try to create subdirs
        try:
            os.makedirs(input_path_date)
        except Exception as ex:
            print(f'[ERROR] {input_path_date} could not be created. Exception: {ex}')
            return None

    input_file = os.path.join(input_path_date,name_file)

    if os.path.isfile(input_file):
        return input_file
    else:
        if none_if_not_exists:
            print(f'[WARNING] Input file {input_file} for dataset {ref} is not available')
            return None
        else:
            return input_file

def get_resampler_from_area_defs(info,input_date):
    resampler_l = info['resampler']
    if len(resampler_l) <2 or len(resampler_l)>5:
        print(f'Option resampler with resampler_type = projections should be a list of 3, 4 or 5 elements indicating: 0: area id for base, 1: area id for data, 2: file_base or 2: path_base, 3: name_base:, 4: date format(optional) ')
        return [None]*2
    geo_info = GeoInfo()
    area_base = geo_info.get_area_definition(resampler_l[0])
    if area_base is None:
        print(f'[ERROR] Area definition for base file {resampler_l[0]} is not valid')
        return [None]*2
    area_data = geo_info.get_area_definition(resampler_l[1])
    if area_data is None:
        print(f'[ERROR] Area definition for base file {resampler_l[0]} is not valid')
        return [None]*2
    file_base = None
    if len(resampler_l)==3:
        file_base = resampler_l[2]
    elif 4 <= len(resampler_l) <= 5:
        date_format = resampler_l[4] if len(resampler_l) == 5 else '%Y%j'
        file_base = get_input_file(resampler_l[2], resampler_l[3], date_format, input_date)
    if file_base is None:
        print(f'[ERROR] File base for resampler could not be retrieved.')
        return [None] * 2
    if not os.path.isfile(file_base):
        print(f'[ERROR] Resampler file base {file_base} is not available.')
        return [None]*2
    #lat_base,lon_base = get_lat_long_arrays(file_base)
    info_dims = get_spatial_dims_arrays(file_base)
    resampler = Resampler()

    resampler.set_area_definitions(area_base,area_data)

    return info_dims, resampler

def get_resampler_from_info_and_file_ref(info,file_ref,input_date):
    resampler = info['resampler']
    if len(resampler)==1:
        file_base = resampler[0]
    else:
        date_format = resampler[2] if len(resampler) == 3 else '%Y%j'
        file_base = get_input_file(resampler[0], resampler[1], date_format, input_date)
    if file_base is None:
        print(f'[ERROR] File base for resampler could not be retrieved.')
        return [None] * 2
    if not os.path.isfile(file_base):
        print(f'[ERROR] Resampler file base {file_base} is not available.')
        return [None] * 2
    lat_base,lon_base = get_lat_long_arrays(file_base)
    lat_data,lon_data = get_lat_long_arrays(file_ref)
    resampler = Resampler()
    resampler.set_area_definitions_from_lat_lon_arrays(lat_base, lon_base, lat_data, lon_data)
    info_dims = {
        'y_name': 'lat',
        'x_name': 'lon',
        'y_array': lat_base,
        'x_array': lon_base,
        'lat_name': 'lat',
        'lon_name': 'lon',
        'lat_array': None,
        'lon_array': None
    }
    return info_dims,resampler

def get_lat_long_arrays(file_nc):
    dset = Dataset(file_nc)
    lat_array = dset.variables['lat'][:]
    lon_array = dset.variables['lon'][:]
    dset.close()
    return lat_array,lon_array

def get_spatial_dims_arrays(file_nc):
    y_array,x_array = None,None
    y_name, x_name = None, None
    lat_name,lon_name = None,None
    dset = Dataset(file_nc)
    for name in dset.variables:
        if name.lower().startswith('lat'):
            lat_name = name
        if name.lower().startswith('lon'):
            lon_name = name
        var_dimensions = dset.variables[name].dimensions
        if len(var_dimensions)==3 and len(dset.dimensions[var_dimensions[0]])==1:
            y_name = var_dimensions[1]
            y_array = dset.variables[y_name][:]
            x_name = var_dimensions[2]
            x_array = dset.variables[x_name][:]
    lat_array, lon_array = None,None
    if lat_name != y_name and lon_name != x_name:
        lat_array = dset.variables[lat_name][:]
        lon_array = dset.variables[lon_name][:]

    dset.close()

    info_dims = {
        'y_name': y_name,
        'x_name': x_name,
        'y_array': y_array,
        'x_array': x_array,
        'lat_name': lat_name,
        'lon_name': lon_name,
        'lat_array': lat_array,
        'lon_array': lon_array
    }

    return info_dims



def run_dataset(dataset_type,input_date,options):
    # date_minus_1w = input_date - timedelta(days=8)
    # date_minus_2w = input_date - timedelta(days=16)
    if dataset_type == 'CandP':
        print(f'[INFO] Starting production of Classification and Probability Dataset for date: {input_date.strftime("%Y-%m-%d")}')
        return run_classification(options,input_date,week=0)

    if dataset_type == 'SST-1w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of SST composite for date: {input_date.strftime("%Y-%m-%d")} - 1 week')
        return run_sst(options, input_date,week=-1)

    if dataset_type == 'MLD-1w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of MLD composite for date: {input_date.strftime("%Y-%m-%d")} - 1 week')
        return run_mld(options, input_date,week=-1)

    if dataset_type == 'CDOM-2w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of CDOM composite for date: {input_date.strftime("%Y-%m-%d")} - 2 weeks')
        return run_cdom(options, input_date, week=-2)

    if dataset_type == 'CDOM':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of CDOM composite for date: {input_date.strftime("%Y-%m-%d")}')
        return run_cdom(options, input_date, week=0)

    if dataset_type == 'CHL-1w':
        print(f'[INFO] Dataset: {dataset_type}. Starting production of CHL composite for date: {input_date.strftime("%Y-%m-%d")} -1 week')
        return run_chl(options, input_date, week = -1)


    return None

def run_chl(options,input_date,week=0):
    info = options.get_options_as_dict('CHL_COMPOSITE')
    info['week'] = week
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)
    check_files, file_ref, unavailable_files = composite.check_input_files()
    if check_files == 0 and info['download'] is None:
        print(f'[ERROR] Files to compute the chl-a composite are not available.')
        return None

    if info['resampler'] is not None:
        type_resampler = info['type_resampler']
        if type_resampler == 'file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler == 'projections':
            info_dims, resampler = get_resampler_from_area_defs(info, input_date)
        if resampler is None:
            print(f'[ERROR] Resampler for SST dataset could not be initialized.')
            return None
        composite.resampler = resampler
        # info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        # composite.resampler = resampler
    else:
        #lat_base, lon_base = get_lat_long_arrays(file_ref)
        info_dims = get_spatial_dims_arrays(file_ref)

    array_out, indices_valid = composite.compute_composite()

    chl = xr.DataArray(
        np.squeeze(array_out),
        name="CHL",  # Name the variable in the xarray
        dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
        coords={info_dims['y_name']:info_dims['y_array'], info_dims['x_name']:info_dims['x_array']}  # Use the existing coordinates from the input data
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        chl['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        chl['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

    # chl = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="CHL",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', get_date_week(input_date,week),create_sub_dirs=True, none_if_not_exists=False)
    chl.to_netcdf(file_out)
    print(f'[INFO] CHL composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out



def run_cdom(options,input_date,week = 0):
    info = options.get_options_as_dict('CDOM_COMPOSITE')
    info['week'] = week
    if info['input_type']=='cdom_daily':
        file_out = cdom_main.launch_multiple_cdom_files(input_date,info)
        return file_out
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)
    check_files, file_ref, unavailable_files = composite.check_input_files()

    if check_files == 0 and info['download'] is None:
        print(f'[ERROR] Files to compute the chl-a composite are not available.')
        return None

    if info['resampler'] is not None:
        type_resampler = info['type_resampler']
        if type_resampler == 'file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler == 'projections':
            info_dims, resampler = get_resampler_from_area_defs(info, input_date)
        if resampler is None:
            print(f'[ERROR] Resampler for SST dataset could not be initialized.')
            return None
        composite.resampler = resampler
        # lat_base, lon_base, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        # composite.resampler = resampler
    else:
        info_dims = get_spatial_dims_arrays(file_ref)
        #lat_base, lon_base = get_lat_long_arrays(file_ref)

    array_out, indices_valid = composite.compute_composite()
    indices_valid_by_band = [(np.array([x]).astype(np.int32),) + indices_valid for x in range(6)]
    cdomModel = CdomModel()
    nowstr = cdomModel.set_df_from_arrays(array_out[indices_valid_by_band[0]], array_out[indices_valid_by_band[1]], array_out[indices_valid_by_band[2]],array_out[indices_valid_by_band[3]], array_out[indices_valid_by_band[4]], array_out[indices_valid_by_band[5]],date_here=input_date)
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

    cdom_array_2d = np.ma.masked_all(array_out.shape[1:],dtype=cdom_array.dtype)
    cdom_array_2d[indices_valid] = cdom_array[:]

    # acdom = xr.DataArray(
    #     cdom_array_2d,
    #     name="Acdom_sat",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    acdom = xr.DataArray(
        cdom_array_2d,
        name="Acdom_sat",  # Name the variable in the xarray
        dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
        coords={info_dims['y_name']: info_dims['y_array'], info_dims['x_name']: info_dims['x_array']}
        # Use the existing coordinates from the input data
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        acdom['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        acdom['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', get_date_week(input_date,week),create_sub_dirs=True, none_if_not_exists=False)
    acdom.to_netcdf(file_out)
    print(f'[INFO] CDOM composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out

def run_mld(options,input_date,week = 0):
    info = options.get_options_as_dict('MLD_COMPOSITE')
    info['week'] = week
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)

    check_files, file_ref, unavailable_dates = composite.check_input_files()
    if check_files == 0 and info['download'] is None:
        print(f'[ERROR] Files to compute the MLD composite are not available.')
        return None

    if info['download'] is not None and check_files <= 1:
        if len(composite.list_files)>1:
            print(f'[ERROR] Download is not available for multiple list_files')
            return None
        print(f'[WARNING] MLD daily files are not available for {len(unavailable_dates)}/{composite.n_days} dates. Trying download....')
        options_download = options.get_download_options(info['download'])
        launcher = LaunchDownload(options_download, unavailable_dates)
        if launcher.launch_download():
            check_files, file_ref, unavailable_files = composite.check_input_files()
            if check_files == 0:
                print(f'[ERROR] Files to compute the MLD composite are not available.')
                return None
        else:
            print(f'[ERROR] Download of files to compute the MLD composite was not successful.')
            return None

    if info['resampler'] is not None:
        type_resampler = info['type_resampler']
        if type_resampler == 'file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler == 'projections':
            info_dims, resampler = get_resampler_from_area_defs(info, input_date)
        if resampler is None:
            print(f'[ERROR] Resampler for MLD dataset could not be initialized.')
            return None
        composite.resampler = resampler
        # lat_base, lon_base, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        # if resampler is None:
        #     print(f'[ERROR] Resampler for MLD dataset could not be initialized.')
        #     return None
        #
        # composite.resampler = resampler
    else:
        info_dims = get_spatial_dims_arrays(file_ref)
        #lat_base, lon_base = get_lat_long_arrays(file_ref)

    array_out, indices_valid = composite.compute_composite()
    mld = xr.DataArray(
        np.squeeze(array_out),
        name="MLD",  # Name the variable in the xarray
        dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
        coords={info_dims['y_name']: info_dims['y_array'], info_dims['x_name']: info_dims['x_array']}
        # Use the existing coordinates from the input data
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        mld['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        mld['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])
    # sst = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="MLD",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )
    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', get_date_week(input_date,week), create_sub_dirs=True,none_if_not_exists=False)
    mld.to_netcdf(file_out)
    print(f'[INFO] MLD composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out


def run_sst(options,input_date,week=0):
    info = options.get_options_as_dict('SST_COMPOSITE')
    info['week'] = week
    composite = Composite(input_date)
    composite.set_info_var_and_files(info)

    check_files, file_ref, unavailable_dates = composite.check_input_files()
    if check_files == 0 and info['download'] is None:
        print(f'[ERROR] Files to compute the chl-a composite are not available.')
        return None

    if info['download'] is not None and check_files <= 1:
        if len(composite.list_files)>1:
            print(f'[ERROR] Download is not available for multiple list_files')
            return None
        print(f'[WARNING] SST daily files are not available for {len(unavailable_dates)}/{composite.n_days} dates. Trying download....')
        options_download = options.get_download_options(info['download'])
        launcher = LaunchDownload(options_download, unavailable_dates)
        if launcher.launch_download():
            check_files, file_ref, unavailable_files = composite.check_input_files()
            if check_files == 0:
                print(f'[ERROR] Files to compute the SST composite are not available.')
                return None
        else:
            print(f'[ERROR] Download of files to compute the SST composite was not successful.')
            return None


    if info['resampler'] is not None:
        type_resampler = info['type_resampler']

        if type_resampler=='file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler=='projections':
            info_dims, resampler = get_resampler_from_area_defs(info,input_date)
        if resampler is None:
            print(f'[ERROR] Resampler for SST dataset could not be initialized.')
            return None
        composite.resampler = resampler
    else:
        #lat_base, lon_base = get_lat_long_arrays(file_ref)
        info_dims = get_spatial_dims_arrays(file_ref)

    array_out, indices_valid = composite.compute_composite()
    sst = xr.DataArray(
        np.squeeze(array_out),
        name="SST",  # Name the variable in the xarray
        dims=[info_dims['y_name'], info_dims['x_name']],  # Dimensions are assumed to be latitude and longitude
        coords={info_dims['y_name']: info_dims['y_array'], info_dims['x_name']: info_dims['x_array']}# Use the existing coordinates from the input data
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        sst['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        sst['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])
    # sst = xr.DataArray(
    #     np.squeeze(array_out),
    #     name="SST",  # Name the variable in the xarray
    #     dims=["lat", "lon"],  # Dimensions are assumed to be latitude and longitude
    #     coords={"lat":lat_base, "lon": lon_base}  # Use the existing coordinates from the input data
    # )

    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j',get_date_week(input_date,week),create_sub_dirs=True, none_if_not_exists=False)
    sst.to_netcdf(file_out)
    print(f'[INFO] SST composite for date {input_date.strftime("%Y-%m-%d")} is saved to {file_out}')

    return file_out

def run_multiple_classification(input_date,info):
    if info['file_class'] is None:
        print(f'[ERROR] Option file_class with the name format of the Classification files for each day in the composite is required.')
        return None
    if info['input_path_class'] is None:
        info['input_path_class'] = info['input_path']
    if info['input_path_class_organization'] is None:
        info['input_path_class_organization'] = info['input_path_organization']
    info_class = info.copy()
    info_class['input_path'] = info['input_path_class']
    info_class['input_path_organization'] = info['input_path_class_organization']
    info_class['list_files'] = [info['file_class']]
    info_class['list_files_format'] = [info['file_class_format']]
    info_class['list_var'] = info['var_class']



    composite = Composite(input_date)
    composite.set_info_var_and_files(info_class)
    check_files, file_ref, unavailable_files = composite.check_input_files()
    if len(unavailable_files) == 0:
        info_dims = cf.get_spatial_dims_arrays(file_ref, None)

    if len(unavailable_files) > 0:
        for unavailable_date in unavailable_files:
            print(f'[INFO] Check CandP (OWT) for date: {unavailable_date}')
            input_date_here = dt.strptime(unavailable_date, '%Y-%m-%d')
            composite_day = Composite(input_date_here)
            info_day = info.copy()
            info_day['week'] = 0
            info_day['dates_0w'] = [0, 0]
            composite_day.set_info_var_and_files(info_day)
            check_files, file_ref, unavailable_files = composite_day.check_input_files()
            info_dims = cf.get_spatial_dims_arrays(file_ref, None)

            array_out, indices_valid = composite_day.compute_composite()
            shape_out = array_out.shape[1:]
            shape_out_prob = shape_out + (17,)
            valid_array = np.zeros(shape_out).astype(np.bool)

            valid_array[indices_valid] = True
            valid_array_prob = np.tile(valid_array.flatten(), 17).reshape((17, shape_out[0], shape_out[1]))
            valid_array_prob = np.moveaxis(valid_array_prob, 0, 2)

            class_array, prob_array, flag1_array, flag2_array, flag3_array, flag4_array, pclass = run_classification_impl(array_out, valid_array,valid_array_prob,shape_out,shape_out_prob)
            dataset_out = xr.Dataset(
                {
                    "Class": ([info_dims['y_name'], info_dims['x_name']], class_array),
                    "Probability": (["pclass", info_dims['y_name'], info_dims['x_name']],
                                    np.moveaxis(prob_array, 2, 0)),
                    "Flag1": ([info_dims['y_name'], info_dims['x_name']], flag1_array),
                    "Flag2": ([info_dims['y_name'], info_dims['x_name']], flag2_array),
                    "Flag3": ([info_dims['y_name'], info_dims['x_name']], flag3_array),
                    "Flag4": ([info_dims['y_name'], info_dims['x_name']], flag4_array),
                },
                coords={
                    info_dims['y_name']: info_dims['y_array'],
                    info_dims['x_name']: info_dims['x_array'],
                    "pclass": pclass
                }
            )
            if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
                dataset_out['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
                dataset_out['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

            file_out = cf.get_input_file(info['input_path_class'], info['file_class'], info['file_class_format'],input_date_here,create_sub_dirs=True, none_if_not_exists=False)

            dataset_out.to_netcdf(file_out)
            print(f'[INFO] Dataset Classification and Probability for single day saved to {file_out}')
        check_files, file_ref, unavailable_files = composite.check_input_files()

    if check_files==0:
        print(f'[ERROR] No daily CDOM files are available and could not be created.')
        return None
    if check_files==1:
        print(f'[WARNING] Some of the daily files are not available for the composite.')


    prob_array,class_array,indices_valid = composite.compute_composite_prob_and_class(type_composite=info['composite_class'])
    pclass = np.arange(0, prob_array.shape[0]).astype(np.int8)
    dataset_out = xr.Dataset(
        {
            "Class": ([info_dims['y_name'], info_dims['x_name']], class_array),
            "Probability": (["pclass", info_dims['y_name'], info_dims['x_name']], prob_array),
        },
        coords={
            info_dims['y_name']: info_dims['y_array'],
            info_dims['x_name']: info_dims['x_array'],
            "pclass": pclass
        }
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        dataset_out['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        dataset_out['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

    file_out = get_input_file(info['output_path'], info['output_file'], '%Y%j', get_date_week(input_date,info['week']), create_sub_dirs=True,
                              none_if_not_exists=False)
    dataset_out.to_netcdf(file_out)
    print(f'[INFO] Dataset Classification and Probability saved to {file_out}')


    return file_out

def run_classification(options,input_date,week=0):

    info = options.get_options_as_dict('CLASS_COMPOSITE')
    info['week'] = week
    if info['input_type']=='class_daily':
        return run_multiple_classification(input_date,info)


    composite = Composite(input_date)
    composite.set_info_var_and_files(info)

    check_files, file_ref, unavailable_files = composite.check_input_files()
    if check_files == 0 and info['download'] is None:
        print(f'[ERROR] Files to compute the OWT composite are not available.')
        return None

    if info['resampler'] is not None:
        type_resampler = info['type_resampler']
        if type_resampler == 'file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler == 'projections':
            info_dims, resampler = get_resampler_from_area_defs(info, input_date)
        if resampler is None:
            print(f'[ERROR] Resampler for SST dataset could not be initialized.')
            return None
        composite.resampler = resampler
        # lat_base, lon_base, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        # composite.resampler = resampler
    else:
        #lat_base, lon_base = get_lat_long_arrays(file_ref)
        info_dims = get_spatial_dims_arrays(file_ref)


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
            "Class": ([info_dims['y_name'], info_dims['x_name']], class_array),
            "Probability": (["pclass", info_dims['y_name'], info_dims['x_name']], np.moveaxis(prob_array,2,0)),
            "Flag1": ([info_dims['y_name'], info_dims['x_name']], flag1_array),
            "Flag2": ([info_dims['y_name'], info_dims['x_name']], flag2_array),
            "Flag3": ([info_dims['y_name'], info_dims['x_name']], flag3_array),
            "Flag4": ([info_dims['y_name'], info_dims['x_name']], flag4_array),
        },
        coords={
            info_dims['y_name']: info_dims['y_array'],
            info_dims['x_name']: info_dims['x_array'],
            "pclass": pclass
        }
    )
    if info_dims['lat_array'] is not None and info_dims['lon_array'] is not None:
        dataset_out['lat'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lat_array'])
        dataset_out['lon'] = ((info_dims['y_name'], info_dims['x_name']), info_dims['lon_array'])

    file_out = get_input_file(info['output_path'],info['output_file'],'%Y%j',get_date_week(input_date,week),create_sub_dirs=True,none_if_not_exists=False)
    dataset_out.to_netcdf(file_out)
    print(f'[INFO] Dataset Classification and Probability saved to {file_out}')

    return file_out



def run_classification_impl(array_out,valid_array,valid_array_prob,shape_out,shape_out_prob):
    print(f'[INFO] Running classification...')
    C, P, flag1, flag2, flag3, flag4 = classification(array_out[0, :].flatten(), array_out[1, :].flatten(),
                                                      array_out[2, :].flatten(), array_out[3, :].flatten(),
                                                      array_out[4, :].flatten(), array_out[5, :].flatten())

    class_array = np.ma.array(np.reshape(C, shape_out))
    class_array[valid_array == False] = np.ma.masked
    P = np.moveaxis(P, 0, 1)
    prob_array = np.ma.array(np.reshape(P, shape_out_prob))
    prob_array[valid_array_prob == False] = np.ma.masked
    flag1_array = np.ma.array(np.reshape(flag1, shape_out))
    flag1_array[valid_array == False] = np.ma.masked
    flag2_array = np.ma.array(np.reshape(flag2, shape_out))
    flag2_array[valid_array == False] = np.ma.masked
    flag3_array = np.ma.array(np.reshape(flag3, shape_out))
    flag3_array[valid_array == False] = np.ma.masked
    flag4_array = np.ma.array(np.reshape(flag4, shape_out))
    flag4_array[valid_array == False] = np.ma.masked
    class_array = np.ma.masked_invalid(class_array)
    prob_array = np.ma.masked_invalid(prob_array)
    flag1_array = np.ma.masked_invalid(flag1_array)
    flag2_array = np.ma.masked_invalid(flag2_array)
    flag3_array = np.ma.masked_invalid(flag3_array)
    flag4_array = np.ma.masked_invalid(flag4_array)
    pclass = np.arange(17).astype(np.int8)

    return class_array, prob_array, flag1_array, flag2_array, flag3_array, flag4_array, pclass

def create_file_with_empty_doc(input_date,file_ref,file_out,variable_ref):

    print(f'[INFO][DOCWritter] Creating file with empty DOC variable: {file_out}')
    print(f'[INFO][DOCWritter] - Reading reference file: {file_ref}')
    dset = Dataset(file_ref)
    if variable_ref is None:
        for var in dset.variables:
            if len(dset.variables[var].shape)==3 and dset.variables[var].shape[0]==1:
                variable_ref = var
    array_ref = dset.variables[variable_ref][:]
    lat_array = dset.variables['lat'][:]
    lon_array = dset.variables['lon'][:]
    dset.close()
    create_doc_file_impl(input_date,file_out,file_ref,None,array_ref,lat_array,lon_array)

def create_doc_file_impl(input_date,file_out,file_ref,array_doc,array_ref,lat_array,lon_array):
    docw = DOCWritter(file_out, file_ref, input_date)
    print(f'[INFO][DOCWritter] - Setting and adding dimensions...')
    if array_doc is not None:
        docw.set_dimensions(array_doc)
    elif array_ref is not None:
        docw.set_dimensions(array_ref)

    if not docw.create_dimensions():
        docw.close_and_remove()
        return
    print(f'[INFO][DOCWritter] - Adding variables...')
    if not docw.create_time_variable():
        docw.close_and_remove()
        return
    if not docw.create_lat_variable(lat_array):
        docw.close_and_remove()
        return
    if not docw.create_lon_variable(lon_array):
        docw.close_and_remove()
        return
    if not docw.create_doc_variable(array_doc):
        docw.close_and_remove()
        return
    print(f'[INFO][DOCWritter] - Adding attributes...')
    docw.add_global_variables()
    docw.close_file()
    print(f'[INFO][DOCWritter] Completed')

def test():
    dir_base = '/mnt/c/DATA/CARBON_OUTPUT/2026/158'
    check = xr.open_dataset(os.path.join(dir_base,'doc_2026158_cnrgoscarbon.nc'))['doc'].data.all()== xr.open_dataset(os.path.join(dir_base,'doc_2026158.nc'))['doc'].data.all()
    print(check)
    return True

def main(args_d):
    # if test():##uncomment for quick testing
    #     return

    # input_date = cf.get_date_arg(args_d['date'])
    # if input_date is None:
    #     return

    start_date, end_date = cf.get_start_end_date(args_d['start_date'], args_d['end_date'])
    if start_date is None:
        return

    options = OptionsDOC(args_d['config_file'])
    if not options.VALID:
        return



    general_model_options = options.get_general_model_options()

    input_date = start_date

    while input_date <= end_date:
        print(f'[INFO] Working with date {input_date}-----------------------------------------------------------------')
        ##Getting output file
        output_file = get_input_file(general_model_options['output_path'], general_model_options['output_file'], '%Y%j', input_date,create_sub_dirs=True,none_if_not_exists=False)
        output_path_date = os.path.dirname(output_file)
        try:
            os.makedirs(output_path_date, exist_ok=True)
        except OSError as e:
            print(f'[ERROR] Output path {output_path_date} does not exist and could not be created. Exception: {e}. Please review permissions')
            input_date = input_date + timedelta(days=1)
            continue
        ##Getting file ref
        file_ref = get_input_file(general_model_options['path_ref'], general_model_options['file_ref'], '%Y%j', input_date,create_sub_dirs=False,none_if_not_exists=True)

        if file_ref is None or not os.path.isfile(file_ref):
            print(f'[ERROR] Reference file is not available, choose correct options for path_ref and file_ref in the configuration file, section [DOC_MODEL]. This file is required for writing the final output file')
            input_date = input_date + timedelta(days=1)
            continue

        dataset_dict = get_datasets(general_model_options,options,input_date)
        unavailable_datasets = False
        for dataset in dataset_dict:
            print(f'-------------------------------------------------------------------------------------------------------')
            if dataset_dict[dataset][0] is None:
                print(f'[INFO] Dataset {dataset} is not available. Launched run...')
                file_out = run_dataset(dataset,input_date,options)
                if file_out is None:
                    if not general_model_options['create_empty_if_not_datasets']:
                        print(f'[ERROR] Dataset {dataset} is not available and could not be created. DOC will not be created.')
                        unavailable_datasets = True
                        break
                    else:
                        print(f'[WARNING] Dataset {dataset} is not available and could not be created. A file with an empty doc variable will be created.')
                        create_file_with_empty_doc(input_date,file_ref,output_file,general_model_options['variable_ref'])
                        unavailable_datasets = True
                        break
                elif not os.path.isfile(file_out):
                    print(f'[ERROR] {file_out} is not a valid file for dataset {dataset}')
                    unavailable_datasets = True
                    break
                else:
                    dataset_dict[dataset] = [file_out]
                    print(f'[INFO] Dataset {dataset}->{file_out}')

            else:
                print(f'[INFO] Dataset {dataset}->{dataset_dict[dataset][0]}')

        if unavailable_datasets:
            input_date = input_date + timedelta(days=1)
            continue
        print(f'-------------------------------------------------------------------------------------------------------')
        print(f'[INFO] All the required datasets are available for date: {input_date.strftime("%Y-%m-%d")}')

        if args_d['only_get_datasets']:
            input_date = input_date + timedelta(days=1)
            continue

        ##Prepare the mask
        print(f'[INFO] Getting the mask...')
        mask = get_mask_from_input_datasets(dataset_dict)
        if mask is None:
            print(f'[ERROR] Mask for the input datasets could not be retrieved.')
            input_date = input_date + timedelta(days=1)
            continue


        ## Call the Run_DOC_model function, passing the datasets and the current date as arguments to compute the DOC values
        print(f'[INFO] Running the DOC model...')
        DOC = Run_DOC_model(dataset_dict, input_date)

        print(f'[INFO] Applying the mask...')
        doc_array = np.ma.array(DOC['doc'].data)
        doc_array[0,mask] = np.ma.masked


        dref = Dataset(file_ref)
        lat_array = dref.variables['lat'][:]
        lon_array = dref.variables['lon'][:]
        dref.close()
        create_doc_file_impl(input_date,output_file,file_ref,doc_array,None,lat_array,lon_array)
        print(f'[INFO] Output file has been generated.')
        input_date = input_date + timedelta(days=1)

    # # Save the DOC and DOC_abc datasets as netCDF files in the folder path.
    # DOC.to_netcdf(output_file)  # Save the DOC dataset to a netCDF file
    # print(f'[INFO] DOC model saved to {output_file}')

    # print(f'[INFO] Applying the mask...')
    # DOC['doc'].data[0,mask] = np.nan
    #
    # # Save the DOC and DOC_abc datasets as netCDF files in the folder path.
    # DOC.to_netcdf(output_file)  # Save the DOC dataset to a netCDF file
    # print(f'[INFO] DOC model saved to {output_file}')




if __name__ == "__main__":
    print(f'[INFO] Started CNR-GOS Carbon tool!')
    print(f'[INFO] This is the script to generate DOC products.')
    parser = argparse.ArgumentParser(description="CNR-GOS Carbon Tool: DOC products")
    parser.add_argument("-v", "--verbose", help="Verbose mode.", action="store_true")
    parser.add_argument('-c', "--config_file", help="Config File.")
    parser.add_argument('-only_datasets',"--only_get_datasets",help="Mode to retrieve the datasets without launching the DOC",action="store_true")
    parser.add_argument('-sd', "--start_date", help="Start Date: YYYY-mm-dd")
    parser.add_argument('-ed', "--end_date", help="End Date: YYYY-mm-dd")
    args = parser.parse_args()
    args_dict = vars(args)
    main(args_dict)


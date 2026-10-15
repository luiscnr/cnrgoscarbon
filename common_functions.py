from datetime import datetime as dt
from datetime import timedelta
import numpy as np
import glob, os
from netCDF4 import Dataset
from geoinfo import  GeoInfo
from resampler import Resampler

def get_date_arg(argdate):
    if argdate is None:
        return None
    try:
        date_out = dt.strptime(argdate, "%Y-%m-%d")
    except ValueError:
        try:
            int_date = int(argdate)
            date_out = dt.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int_date)
        except ValueError:
            date_out = None
            print(f'[ERROR] {argdate} is not a valid date in format YYYY-MM-DD or relative integer' )
    return date_out

def get_start_end_date(argstart,argend):
    start_date = get_date_arg(argstart)
    end_date = get_date_arg(argend) if argend is not None else start_date

    if start_date is None or end_date is None:
        return [None]*2
    if end_date < start_date:
        print(f'[ERROR] End date {end_date} should be greater or equal than start date {start_date}')
        return [None]*2
    return start_date,end_date

def get_start_end_dates_composite(input_date,info,week):
    dates_key = f'dates_{int(week * (-1))}w'
    info_dates = info[dates_key]
    start_date, end_date = [None]*2
    #print(info_dates)
    if len(info_dates)==1:
        end_date = input_date + timedelta(info_dates[0])
        start_date = end_date - timedelta(days=info['n_days']-1)
    elif len(info_dates)==2:
        start_date = input_date + timedelta(days=info_dates[0])
        end_date = input_date + timdelta(days=info_dates[1])
    return start_date,end_date

def get_input_file_composite(input_date,start_date,end_date,path_composite,path_composite_org,file_composite,file_composite_format):
    path_composite = path_composite.replace('$INPUT_DATE$',input_date.strftime(path_composite_org))
    path_composite = path_composite.replace('$START_DATE$', start_date.strftime(path_composite_org))
    path_composite = path_composite.replace('$END_DATE$', end_date.strftime(path_composite_org))

    file_composite = file_composite.replace('$INPUT_DATE$', input_date.strftime(file_composite_format))
    file_composite = file_composite.replace('$START_DATE$', start_date.strftime(file_composite_format))
    file_composite = file_composite.replace('$END_DATE$', end_date.strftime(file_composite_format))

    output_file = os.path.join(path_composite,file_composite)
    if os.path.isfile(output_file):
        return output_file
    else:
        print(f'[WARNING] File composite {output_file} is not available. Please review: path_composite,path_composite_org, file_composite, file_composite_format')
        return None

def get_resampler_from_info(input_date,info,file_ref,key=''):

    resampler, info_dims = None, None

    if info['resampler_reference_file'] is not None:
        file_ref = info['resampler_reference_file']

    if info['resampler'] is not None:
        type_resampler = info['type_resampler']
        if type_resampler == 'file_ref':
            info_dims, resampler = get_resampler_from_info_and_file_ref(info, file_ref, input_date)
        if type_resampler == 'projections':
            info_dims, resampler = get_resampler_from_area_defs(info, input_date)

    if resampler is None:
        print(f'[ERROR] Resampler for {key} dataset could not be initialized.')
        info_dims = get_spatial_dims_arrays(file_ref, None)

    return info_dims,resampler

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
    info_dims = get_spatial_dims_arrays(file_base,None)
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



def get_files_by_pattern(directory, pattern):
    """
    Finds files in the specified directory that match a given pattern.

    Args:
    - directory (str): Path to the directory containing the files.
    - pattern (str): The pattern to search for (e.g., "*2024-12-04*.nc").

    Returns:
    - List of matching filenames.
    """
    search_path = f"{directory}/{pattern}"
    matching_files = glob.glob(search_path)
    return matching_files

def get_input_file(input_path,name_file,name_file_date_format,date_here,ref='',none_if_not_exists=True,create_sub_dirs=False,folder_format='%Y/%j',real_date=None):
    if real_date is None:
        name_file = name_file.replace('$DATE$',date_here.strftime(name_file_date_format))
    else:
        name_file = name_file.replace('$DATE$','$DATE1$_$DATE2$')
        name_file = name_file.replace('$DATE1$', date_here.strftime(name_file_date_format))
        name_file = name_file.replace('$DATE2$', real_date.strftime(name_file_date_format))
    #folder_format = '%Y/%j'
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

##first file from the list of input files
def get_reference_file_and_sources(date_run,options):
    input_path = options['input_path'] if 'input_path' in options else None
    input_path_organization = options['input_path_organization'] if 'input_path_organization' in options else None
    list_files = options['list_files'] if 'list_files' in options else None
    list_files_format = options['list_files_format'] if 'list_files_format' in options else None

    if input_path is None or input_path_organization is None or list_files is None or list_files_format is None:
        return None
    reference_file = None
    source_name_files = []
    for ifile in range(len(list_files)):
        iformat = ifile if len(list_files_format)==len(list_files) else 0
        this_file = get_input_file(input_path,list_files[ifile],list_files_format[iformat],date_run,folder_format=input_path_organization)
        if this_file is not None:
            if reference_file is None:
                reference_file = this_file
            source_name_files.append(os.path.basename(this_file))
    return reference_file,source_name_files


def get_input_valid_array_from_options(date_run,options):
    input_path = options['input_path'] if 'input_path' in options else None
    input_path_organization = options['input_path_organization'] if 'input_path_organization' in options else None
    list_files = options['list_files'] if 'list_files' in options else None
    list_files_format = options['list_files_format'] if 'list_files_format' in options else None
    list_var = options['list_var'] if 'list_var' in options else None
    return get_input_valid_array_from_multiple_files(date_run,input_path,input_path_organization,list_files,list_files_format,list_var)

def get_input_valid_array_from_multiple_files(date_run,input_path,input_path_organization,list_files,list_files_format,list_var):

    if input_path is None or input_path_organization is None or list_files is None or list_files_format is None or list_var is None:
        return [None]*5
    # list_files_format = self.options_cdom['list_files_format']
    # list_files = self.options_cdom['list_files']
    # list_var = self.options_cdom['list_var']

    input_path_date = os.path.join(input_path, date_run.strftime(input_path_organization))
    n_var = len(list_var)
    array_out, valid_array, info_dims = [None] * 3
    for ivar, var_name in enumerate(list_var):
        input_file_format = list_files_format[ivar] if len(list_files_format) == len(list_var) else list_files_format[0]
        input_file = list_files[ivar] if len(list_files) == len(list_var) else list_files[0]
        input_path = os.path.join(input_path_date, input_file.replace('$DATE$', date_run.strftime(input_file_format)))
        if os.path.exists(input_path):
            dset = Dataset(input_path)
            array_here = np.squeeze(dset.variables[var_name][:])
            if info_dims is None:
                # lat_base = dset.variables['lat'][:]
                # lon_base = dset.variables['lon'][:]
                info_dims = get_spatial_dims_arrays(None,dset)

            dset.close()
            if array_out is None:
                array_out = np.ma.masked_all((n_var,) + array_here.shape)
            array_out[ivar, :] = array_here[:]
            if valid_array is None:
                valid_array = np.where(array_here.mask == False, 1, 0)
            else:
                valid_array = np.logical_and(valid_array, np.where(array_here.mask == False, 1, 0))
        else:
            print(f'[ERROR] File {input_path} is not available')
    indices_valid = np.where(valid_array == 1) if valid_array is not None else None

    return array_out, valid_array, info_dims, indices_valid

def get_spatial_dims_arrays(file_nc,dset):
    y_array,x_array = None,None
    y_name, x_name = None, None
    lat_name,lon_name = None,None
    if file_nc is not None and dset is None:
        dset = Dataset(file_nc)
    for name in dset.variables:
        if name.lower().endswith('_bnds'):
            continue
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
        if len(var_dimensions)==2:
            y_name = var_dimensions[0]
            y_array = dset.variables[y_name][:]
            x_name = var_dimensions[1]
            x_array = dset.variables[x_name][:]
    lat_array, lon_array = None,None
    if lat_name != y_name and lon_name != x_name:
        lat_array = dset.variables[lat_name][:]
        lon_array = dset.variables[lon_name][:]

    if file_nc is not None:
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
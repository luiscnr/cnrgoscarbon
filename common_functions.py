from datetime import datetime as dt
from datetime import timedelta
import numpy as np
import glob, os
from netCDF4 import Dataset

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
    array_out, valid_array, lat_base, lon_base = [None] * 4
    for ivar, var_name in enumerate(list_var):
        input_file_format = list_files_format[ivar] if len(list_files_format) == len(list_var) else list_files_format[0]
        input_file = list_files[ivar] if len(list_files) == len(list_var) else list_files[0]
        input_path = os.path.join(input_path_date, input_file.replace('$DATE$', date_run.strftime(input_file_format)))
        if os.path.exists(input_path):
            dset = Dataset(input_path)
            array_here = np.squeeze(dset.variables[var_name][:])
            if lat_base is None and lon_base is None:
                lat_base = dset.variables['lat'][:]
                lon_base = dset.variables['lon'][:]
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

    return array_out, valid_array, lat_base, lon_base, indices_valid
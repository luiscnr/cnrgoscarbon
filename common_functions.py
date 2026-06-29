from datetime import datetime as dt
from datetime import timedelta
import glob, os

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
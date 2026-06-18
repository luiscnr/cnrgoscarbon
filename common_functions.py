from datetime import datetime as dt
from datetime import timedelta
import glob

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

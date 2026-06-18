from datetime import timedelta
from netCDF4 import Dataset
import numpy as np
import os
from resampler import Resampler

class Composite:

    def __init__(self,date_ref):
        self.n_days = 8
        self.date_ref = date_ref

        ##file and vars info
        self.input_path = None
        self.input_path_organization= '%Y/%j'
        self.list_files = []
        self.list_files_format = ['%Y%j']
        self.list_var = []

        ##resampler tool
        self.resampler = None

        #depth integrator
        self.depth_integrator={
            'index_min':0,
            'index_max':None
        }


    def set_info_var_and_files(self,info):
        if 'input_path' in info:
            self.input_path = info['input_path']
        if 'input_path_organization' in info:
            self.input_path_organization = info['input_path_organization']
        if 'list_files' in info:
            self.list_files = info['list_files']
        if 'list_files_format' in info:
            self.list_files_format = info['list_files_format']
        if 'list_var' in info:
            self.list_var = info['list_var']
        if 'resampler' in info:
            self.resampler = info['resampler']


        print(f'[INFO][OPTIONS] [START] Files and variables')
        print(f'[INFO][OPTIONS] Input path: {self.input_path}')
        print(f'[INFO][OPTIONS] Input path_organization: {self.input_path_organization}')
        print(f'[INFO][OPTIONS] Number of files: {len(self.list_files)} -> {self.list_files}')
        print(f'[INFO][OPTIONS] Number of files format {len(self.list_files_format)} -> {self.list_files_format}')
        print(f'[INFO][OPTIONS] Number of variables: {len(self.list_var)} -> {self.list_var}')
        print(F'[INFO][OPTIONS] [STOP] Files and variables')

        if self.input_path is None:
            print(f'[ERROR] Input path is required')
            return False

        return True

    ##Main method, could launch more options. At the moment, only averages of the last n_days including date_ref
    def compute_composite(self):
        start_date = self.date_ref-timedelta(days=self.n_days-1)
        end_date = self.date_ref
        print(f'[INFO] Start date: {start_date.strftime("%Y-%m-%d")} End date: {end_date.strftime("%Y-%m-%d")}')
        return self.compute_average(start_date,end_date)

    ##return the first existing file, to be used as ref to get lat_array,lon_array....
    def get_file_ref(self):
        work_date = self.date_ref - timedelta(days=self.n_days - 1)
        end_date = self.date_ref
        while work_date <= end_date:
            for ifile,name_file in enumerate(self.list_files):
                input_file_format = self.list_files_format[ifile] if len(self.list_files) == len(self.list_files_format) else self.list_files_format[0]
                input_path_date = os.path.join(self.input_path, work_date.strftime(self.input_path_organization))
                input_file = os.path.join(input_path_date,name_file.replace('$DATE$', work_date.strftime(input_file_format)))
                if os.path.exists(input_file):
                    return input_file
            work_date = work_date + timedelta(days=1)
        return None

    def check_input_files(self):

        n_files = len(self.list_files)
        work_date = self.date_ref - timedelta(days=self.n_days - 1)
        end_date = self.date_ref
        print(f'[INFO] Checking input files for composite interval from {work_date} to {end_date}')
        is_file_available = np.zeros((self.n_days,n_files))
        iday = 0
        unavailable_dates = []
        while work_date <= end_date:
            for ifile, name_file in enumerate(self.list_files):
                input_file_format = self.list_files_format[ifile] if len(self.list_files) == len(
                    self.list_files_format) else self.list_files_format[0]
                input_path_date = os.path.join(self.input_path, work_date.strftime(self.input_path_organization))
                input_file = os.path.join(input_path_date, name_file.replace('$DATE$', work_date.strftime(input_file_format)))
                if os.path.exists(input_file):
                    is_file_available[iday,ifile]=1
                else:
                    work_date_str = work_date.strftime("%Y-%m-%d")
                    if work_date_str not in unavailable_dates:
                        unavailable_dates.append(work_date_str)
                    print(f'[WARNING] {input_file} for date {date} is not available')
            work_date = work_date +timedelta(days=1)
            iday = iday + 1


        n_files_available = np.sum(is_file_available,axis=0)

        if np.min(n_files_available)==self.n_days:
            print(f'[INFO] File availability for composite is complete.')
            return 2,unavailable_dates

        elif np.min(n_files_available)>0:
            print(f'[WARNING] Files are not available for {len(unavailable_dates)} days')
            return 1,unavailable_dates

        else:
            print(f'[WARNING] Files are not available for all the days')
            return 0,unavailable_dates

    ##Simple average
    def compute_average(self,start_date,end_date):

        valid_array = None

        n_var = len(self.list_var)
        array_out =None

        for ivar, var_name in enumerate(self.list_var):
            input_file_format = self.list_files_format[0]
            input_file = self.list_files[0]
            if len(self.list_var) == len(self.list_files):
                if len(self.list_files) == len(self.list_files_format):
                    input_file_format = self.list_files_format[ivar]
                input_file = self.list_files[ivar]
            array_avg = self.get_stat_array('avg',start_date,end_date,input_file,input_file_format,var_name)
            if array_avg is None:
                return [None]*2
            if array_out is None:
                array_out = np.ma.masked_all((n_var,)+array_avg.shape)
            array_out[ivar,:] = array_avg[:]
            if valid_array is None:
                valid_array = np.where(array_avg.mask==False,1,0)
            else:
                valid_array = np.logical_and(valid_array,np.where(array_avg.mask==False,1,0))


        indices_valid = np.where(valid_array==1) if valid_array is not None else None
        if indices_valid is not None:
            print(f'[INFO] Number of valid pixels common for all the bands: {len(indices_valid[0])}')

        return array_out,indices_valid






    def get_indices_valid(self,start_date,end_date):
        #a pixel is considered valid only if it's valid for all the variables(rrs bands)
        valid_array = None
        print(f'[INFO] Getting valid indices for composite interval from {start_date} to {end_date}')
        for ivar,var_name in enumerate(self.list_var):
            work_date = start_date
            array_n_dates = None
            n_days_invalid = 0
            input_file_format = self.list_files_format[0]
            input_file = self.list_files[0]
            if len(self.list_var) == len(self.list_files):
                if len(self.list_files) == len(self.list_files_format):
                    input_file_format = self.list_files_format[ivar]
                input_file = self.list_files[ivar]

            while work_date <= end_date:

                array = self.get_data_array(work_date,input_file,input_file_format,var_name)



                if array is not None:
                    if array_n_dates is None:
                        array_n_dates = np.zeros(array.shape)
                    array_n_dates[array.mask==False] = array_n_dates[array.mask==False] + 1
                else:
                    n_days_invalid = n_days_invalid + 1
                work_date = work_date + timedelta(days=1)

            if n_days_invalid == self.n_days:
                print(f'[ERROR] No valid data was retrieved for variable {var_name} for the composite time period. Stopping.')
                return None
            elif n_days_invalid > 0:
                print(f'[WARNING] Data for some days was not available for variable {var_name} for the composite time period. Mean is only bases on {n_days_invalid} days of expected {self.n_days} days')


            if valid_array is None:
                valid_array = array_n_dates>=1
            else:
                valid_array = np.logical_and(valid_array,array_n_dates>=1)



        indices_valid = np.where(valid_array==True)

        print(f'[INFO] Getting valid indices: Completed')

        return indices_valid

    def get_stat_array(self,stat,start_date,end_date,input_file,input_file_format,var_name):
        n_days = (end_date-start_date).days + 1
        all_array = None
        work_date = start_date
        idate = 0
        n_no_data = 0
        while work_date <= end_date:
            array = self.get_data_array(work_date,input_file,input_file_format,var_name)
            if self.resampler is not None and array is not None:
                array = self.resampler.compute_nn_resampled_array(array)
            if array is not None:
                if all_array is None:
                    output_shape = (n_days,)+array.shape
                    all_array = np.ma.masked_all(output_shape)
                all_array[idate,:] = array[:]
            else:
                print(f'[WARNING] Data for date {work_date.strftime("%Y-%m-%d")} are not available for variable {var_name}')
                n_no_data = n_no_data + 1

            idate = idate + 1
            work_date = work_date + timedelta(days=1)

        if all_array is None:
            print(f'[ERROR] No data was available for none of the dates in the interval from {start_date} to {end_date}. {stat} could not be computed')
            return None

        if n_no_data<0:
            n_data = n_days-n_no_data
            print(f'[WARNING] No data was available for sames dates in the interval from {start_date} to {end_date}. {stat} could be computed with only {n_data} days.')

        array_result = None
        if stat=='avg':
            array_result = np.ma.mean(all_array,axis=0)

        if array_result is not None:
            print(f'[INFO] {stat} for variable {var_name} for period from {start_date} to {end_date}: {np.ma.count(array_result)} valid pixels')

        return array_result


    def get_data_array(self,work_date,input_file,input_file_format,var_name):
        input_path_date = os.path.join(self.input_path,work_date.strftime(self.input_path_organization))
        input_file = os.path.join(input_path_date, input_file.replace('$DATE$', work_date.strftime(input_file_format)))
        if not os.path.isfile(input_file):
            print(f'[WARNING] File {input_file} does not exist')
            return None


        dset = Dataset(input_file)
        array = dset.variables[var_name][:] if var_name in dset.variables else None
        dset.close()

        array = np.squeeze(array)

        if len(array.shape)==3:##depth variables
            array = self.get_integrated_depth(array)

        return array

    def get_integrated_depth(self,array):
        index_min = self.depth_integrator['index_min']
        index_max = self.depth_integrator['index_max']
        if index_min is None:
            return None

        if index_max is None:
            index_max = index_min


        if index_min==index_max:
            return array[index_min,:]
        else:
            return None
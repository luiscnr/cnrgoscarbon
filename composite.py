from datetime import timedelta
from datetime import datetime as dt
from netCDF4 import Dataset
import numpy as np
import os


class Composite:

    def __init__(self,date_composite):
        self.n_days = 8
        self.date_composite = date_composite
        self.date_ref = None

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
        if 'input_path' in info and info['input_path'] is not None:
            self.input_path = info['input_path']
        if 'input_path_organization' in info and info['input_path_organization'] is not None:
            self.input_path_organization = info['input_path_organization']
        if 'list_files' in info and info['list_files'] is not None:
            self.list_files = info['list_files']
        if 'list_files_format' in info and info['list_files_format'] is not None:
            self.list_files_format = info['list_files_format']
        if 'list_var' in info and info['list_var'] is not None:
            self.list_var = info['list_var']
        if 'resampler' in info and info['resampler'] is not None:
            self.resampler = info['resampler']

        week = 0
        if 'week' in info and info['week'] is not None:
            week = int(info['week'])
        dates_key =  f'dates_{int(week*(-1))}w'
        dates_values = [0]
        if dates_key in info and info[dates_key] is not None:
            dates_values = info[dates_key]


        if len(dates_values) == 2:##start and end dates are already defined
            self.n_days = (dates_values[1]-dates_values[0])+1
            self.date_ref = self.date_composite + timedelta(days=dates_values[1])
        else:
            self.date_ref =  self.date_composite+timedelta(days=dates_values[0])
            self.n_days = 8
            if 'n_days' in info and info['n_days'] is not None:
                self.n_days = info['n_days']



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

    def set_dates_composite(self):
        week = 0
        if 'week' in info and info['week'] is not None:
            week = int(info['week'])
        dates_key = f'dates_{int(week * (-1))}w'
        dates_values = [0]
        if dates_key in info and info[dates_key] is not None:
            dates_values = info[dates_key]

        if len(dates_values) == 2:  ##start and end dates are already defined
            self.n_days = (dates_values[1] - dates_values[0]) + 1
            self.date_ref = self.date_composite + timedelta(days=dates_values[1])
        else:
            self.date_ref = self.date_composite + timedelta(days=dates_values[0])
            self.n_days = 8
            if 'n_days' in info and info['n_days'] is not None:
                self.n_days = info['n_days']



    ##Main method, could launch more options. At the moment, only averages of the last n_days including date_ref
    def compute_composite(self,type_composite=None):
        start_date = self.date_ref-timedelta(days=self.n_days-1)
        end_date = self.date_ref
        print(f'[INFO] Start date: {start_date.strftime("%Y-%m-%d")} End date: {end_date.strftime("%Y-%m-%d")}')
        return self.compute_composite_impl(start_date,end_date,type_composite=type_composite)

    def compute_composite_prob_and_class(self,type_composite=None):
        if type_composite is None:
            return [None] * 2
        start_date = self.date_ref - timedelta(days=self.n_days - 1)
        end_date = self.date_ref
        print(f'[INFO] Start date: {start_date.strftime("%Y-%m-%d")} End date: {end_date.strftime("%Y-%m-%d")}')
        input_file_format = self.list_files_format[0]
        input_file = self.list_files[0]

        prob_result = self.get_stat_array('avg', start_date, end_date, input_file, input_file_format, 'Probability',is_depth=False)
        class_result = np.ma.array(np.ma.argmax(prob_result, axis=0) + 1) ##class between 1 and 18
        mask_result = np.ma.count_masked(prob_result, axis=0)
        class_result[mask_result == prob_result.shape[0]] = np.ma.masked
        classes_available = np.unique(class_result)
        n_valid = np.ma.count(class_result)
        print(f'[INFO] OWT Results for {n_valid} pixels:')
        for class_available in classes_available:
            if np.ma.is_masked(class_available):
                continue
            n_class = np.ma.sum(class_result == class_available)
            p_class = (n_class/n_valid)*100
            print(f'[INFO] - OWT {class_available} -> {n_class} pixels ({p_class:.2f}%)')
        valid_array = np.where(class_result.mask == False, 1, 0)

        return prob_result,class_result,valid_array

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
        file_ref = None
        while work_date <= end_date:
            for ifile, name_file in enumerate(self.list_files):
                input_file_format = self.list_files_format[ifile] if len(self.list_files) == len(
                    self.list_files_format) else self.list_files_format[0]
                input_path_date = os.path.join(self.input_path, work_date.strftime(self.input_path_organization))
                input_file = os.path.join(input_path_date, name_file.replace('$DATE$', work_date.strftime(input_file_format)))
                if os.path.exists(input_file):
                    is_file_available[iday,ifile]=1
                    if file_ref is None:
                        file_ref = input_file
                else:
                    work_date_str = work_date.strftime("%Y-%m-%d")
                    if work_date_str not in unavailable_dates:
                        unavailable_dates.append(work_date_str)
                    print(f'[WARNING] {input_file} for date {work_date_str} is not available')
            work_date = work_date +timedelta(days=1)
            iday = iday + 1


        n_files_available = np.sum(is_file_available,axis=0)

        if np.min(n_files_available)==self.n_days:
            print(f'[INFO] File availability for composite is complete.')
            return 2,file_ref,unavailable_dates

        elif np.min(n_files_available)>0:
            print(f'[WARNING] Files are not available for {len(unavailable_dates)} days')
            return 1,file_ref,unavailable_dates

        else:
            print(f'[WARNING] Files are not available for all the days')
            return 0,file_ref,unavailable_dates

    ##Compute composite impl
    def compute_composite_impl(self,start_date,end_date,type_composite=None):
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
            array_result = None
            if type_composite is None: ##avg by default
                array_result = self.get_stat_array('avg',start_date,end_date,input_file,input_file_format,var_name)

            if array_result is None:
                return [None]*2
            if array_out is None:
                array_out = np.ma.masked_all((n_var,)+array_result.shape)
            array_out[ivar,:] = array_result[:]
            if valid_array is None:
                valid_array = np.where(array_result.mask==False,1,0)
            else:
                valid_array = np.logical_and(valid_array,np.where(array_result.mask==False,1,0))


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

    def get_stat_array(self,stat,start_date,end_date,input_file,input_file_format,var_name,is_depth=True):
        n_days = (end_date-start_date).days + 1
        all_array = None
        work_date = start_date
        idate = 0
        n_no_data = 0
        while work_date <= end_date:
            array = self.get_data_array(work_date,input_file,input_file_format,var_name,is_depth=is_depth)
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


    def get_data_array(self,work_date,input_file,input_file_format,var_name,is_depth=True):
        input_path_date = os.path.join(self.input_path,work_date.strftime(self.input_path_organization))
        input_file = os.path.join(input_path_date, input_file.replace('$DATE$', work_date.strftime(input_file_format)))
        if not os.path.isfile(input_file):
            print(f'[WARNING] File {input_file} does not exist')
            return None


        dset = Dataset(input_file)
        array = dset.variables[var_name][:] if var_name in dset.variables else None
        dset.close()

        array = np.squeeze(array)

        if len(array.shape)==3 and is_depth:##depth variables
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
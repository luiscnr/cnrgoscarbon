import os,sys
from datetime import datetime as dt



class LaunchDownload(object):

    def __init__(self,options,list_dates):
        self.options = options
        self.list_dates = list_dates
        self.types = ['CMEMS']
        self.verbose = True

    def launch_download(self):
        if self.options['type']=='CMEMS':
            return self.launch_cmems_download()
        else:
            print(f'{self.options["type"]} download is not implemented. Please choose among {self.types}.')
            return False

    def check_cmems_download(self):
        path_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        eistools_path = os.path.join(path_base,'eistools')
        if not os.path.isdir(eistools_path):
            print(f'[ERROR] eistools path {eistools_path} does not exist. You could clone the code from GitHub repository:')
            print(f'cd {path_base}')
            print(f'git clone https://github.com/luiscnr/eistools.git')
            return False
        sys.path.append(eistools_path)
        try:
            from cmems_lois import CMEMS_LOIS
        except Exception as ex:
            print(f'[ERROR] CMEMS_LOIS class could not be imported. Exception: {ex}')
            return False
        return True

    def launch_cmems_download(self):
        if not self.check_cmems_download():
            return False
        from cmems_lois import CMEMS_LOIS
        clois = CMEMS_LOIS(self.verbose)

        cmems_options = {
            'date_list': [dt.strptime(x,'%Y-%m-%d') for x in self.list_dates],
            'product': self.options['product'],
            'dataset': self.options['dataset'],
            'bucket': self.options['bucket'],
            'endpoint': self.options['endpoint'],
            'tag':self.options['tag'],
            'remote_name_abs':self.options['remote_name_abs']
        }
        output_directory = self.options['output_path']
        ods = self.options['output_path_structure']
        output_files = clois.make_cmems_download(cmems_options,True, output_directory, ods, True)

        if self.options['output_file'] is not None:
            output_file_base = self.options['output_file']
            output_file_format = self.options['output_file_format']

            for output_file in output_files:
                output_name = os.path.basename(output_file)
                date_here = dt.strptime(output_name.split('_')[0],'%Y%m%d')
                output_rename = output_file_base.replace('$DATE$',date_here.strftime(output_file_format))
                if output_rename != output_name:
                    file_new = os.path.join(os.path.dirname(output_file),output_rename)
                    os.rename(output_file,file_new)
                    print(f'[INFO] Renamed {output_file} to {file_new}')

        return True
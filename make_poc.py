import argparse,os
import common_functions as cf
import numpy as np
from options.options_manager import OptionsManager
from bbp import bbp_run
from poc import PocAlgorithms

class OptionsPOC:
    def __init__(self,config_file):
        file_opt = os.path.join(os.path.dirname(__file__),'options/poc_options.ini')
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

    def get_poc_options(self):
        return self.get_options_as_dict('POC_DAILY')

    def get_chl_options(self):
        return self.get_options_as_dict('CHL_DAILY')

def main(args_d):
    input_date = cf.get_date_arg(args_d['date'])
    if input_date is None:
        return

    options = OptionsPOC(args_d['config_file'])
    if not options.VALID:
        return

    poc_options = options.get_poc_options()
    bands = np.array(poc_options['bands'])
    array_rrs, valid_array, lat_base, lon_base, indices_valid = cf.get_input_valid_array_from_options(input_date,poc_options)
    if indices_valid is None:
        return
    nbands = array_rrs.shape[0]
    if len(bands)!=nbands:
        print(f'[ERROR] Number of bands in the Rrs array {nbands} is not equal to the number of bands of the band list given in the configuration file')
        return
    shape_orig = array_rrs.shape[1:]
    chl_options = options.get_chl_options()
    array_chl, valid_chl, lat_base, lon_base, indices_chl = cf.get_input_valid_array_from_options(input_date,chl_options)
    array_chl = np.squeeze(array_chl)

    if array_chl.shape != shape_orig:
        print(f'[ERROR] Rrs array shape {shape_orig} does not match chl-a array shape {array_chl.shape}')
        return

    valid_array = np.where((valid_array == 1) & (valid_chl == 1),1,0)
    indices_valid = np.where(valid_array == 1)
    nvalid = len(indices_valid[0])
    print(f'[INFO] Number of valid pixels to process POC: {nvalid}')
    mask_rrs = np.tile(valid_array.flatten(),6).reshape(array_rrs.shape)
    array_rrs = np.reshape(array_rrs[mask_rrs==1],(nbands,nvalid))
    array_chl = array_chl[valid_array==1]

    ##bbp
    brun = bbp_run(bands)
    bbp490 = brun.run_bbp_qaa(array_rrs)



    poc_run = PocAlgorithms(array_rrs,bbp490,array_chl,bands=bands)
    poc_run.run_poc_ocroc()
    # poc_run.run_poc_le()
    # poc_run.run_poc_tran()
    # poc_run.run_poc_loisel()
    # poc_run.run_owt()








if __name__ == "__main__":
    print(f'[INFO] Started CNR-GOS Carbon tool!')
    print(f'[INFO] This is the script to generate POC products.')
    parser = argparse.ArgumentParser(description="CNR-GOS Carbon Tool: POC products")
    parser.add_argument("-v", "--verbose", help="Verbose mode.", action="store_true")
    parser.add_argument('-c', "--config_file", help="Config File.")
    parser.add_argument('-only_datasets',"--only_get_datasets",help="Mode to retrieve the datasets without launching the DOC",action="store_true")
    parser.add_argument('-d', "--date",help="Input Date: YYYY-mm-dd")
    args = parser.parse_args()
    args_dict = vars(args)
    main(args_dict)
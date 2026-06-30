
import BSC_QAA.bsc_qaa_EUMETSAT as bsc


class bbp_run:
    def __init__(self,bands):
        print('[INFO] Started BBP run')
        self.bands = bands

    def run_bbp_qaa(self,input_rrs):
        print(f'[INFO] Using QAA algorithm....')
        results = bsc.qaa(input_rrs,self.bands)
        print(f'[INFO] Finished QAA algorithm.')
        return results['bbp490']

# def tal():
#     print('tal')
#     import sys
#     sys.path.append('/home/lois/PycharmProjects/hypernets_val')
#     import BSC_QAA.bsc_qaa_EUMETSAT as bsc
#     bands = [412, 443, 490, 510, 555, 670]
#     file = '/mnt/c/DATA/INPUT_MULTI_MED/2026/135/X2026135-rrs$BAND$-med-hr.nc'
#     array = np.ma.masked_all((6,1580,3308))
#     valid_array = np.zeros((1580,3308))
#     for iband,band in enumerate(bands):
#         dset = Dataset(file.replace('$BAND$',str(band)))
#         array_here = np.squeeze(dset.variables[f'RRS{band}'][:])
#         valid_array[array_here.mask==False] = valid_array[array_here.mask==False]+1
#         array[iband,:] = array_here[:]
#         dset.close()
#
#     indices_valid = np.where(valid_array==6)
#
#
#
#
#     array_tal = array[:,indices_valid[0],indices_valid[1]]
#
#
#     out = bsc.qaa(array_tal,bands)
#     bbp490 = np.squeeze(out['bbp490'])
#     print(bbp490.shape)
#
#
#     return True

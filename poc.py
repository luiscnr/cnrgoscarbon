import numpy as np
from Run_CLA.Run_classification import classification

class PocAlgorithms:
    def __init__(self,rrs_array,bbp_array,chl_array,bands=None):
        self.rrs_array = rrs_array
        self.bbp_array = bbp_array
        self.chl_array = chl_array
        self.wl_diff_max = 5
        self.brefs = None
        if bands is not None:
            self.bands = bands
        else:
            self.bands = [412, 443, 490, 510, 555, 670]
        self.VALID = self.check_indices_bands()


        self.POC_Le = None
        self.POC_Tran = None
        self.POC_Loisel = None
        self.Class = None
        self.proba = None



    def run_poc_le(self):
        if not self.VALID:
            return False
        if self.POC_Le is not None:
            return True
        print(f'[INFO] Running POC Le Algorithm....')
        try:
            self.POC_Le = 10 ** (
                    2.7116
                    - 221.71 * self.rrs_array[self.brefs['490'],:]
                    + 196.76 * self.rrs_array[self.brefs['510'],:]
                    - 30.525 * self.rrs_array[self.brefs['555'],:]
                    + 39.222 * self.rrs_array[self.brefs['670'],:]
            )
            return True
        except Exception as ex:
            print(f'[ERROR] POC Le Algorithm failed: {ex}')
            return False

    def run_poc_tran(self):
        if not self.VALID:
            return False
        if self.POC_Tran is not None:
            return True
        print(f'[INFO] Running POC Tra Algorithm....')
        try:
            R1 = self.rrs_array[self.brefs['670'],:] / self.rrs_array[self.brefs['490'],:]
            R2 = self.rrs_array[self.brefs['670'],:] / self.rrs_array[self.brefs['510'],:]
            R3 = self.rrs_array[self.brefs['670'],:] / self.rrs_array[self.brefs['555'],:]
            MBR = np.max((R1, R2, R3), axis=0)
            X = np.log10(MBR)
            self.POC_Tran = 10 ** (0.928 * X + 2.875)
            return True
        except Exception as ex:
            print(f'[ERROR] POC Tran algorithm failed: {ex}')
            return False

    def run_poc_loisel(self):
        if not self.VALID:
            return False
        if self.POC_Loisel is not None:
            return True
        print(f'[INFO] Running POC Loisel Algorithm....')
        try:
            self.POC_Loisel = (400 / 0.0096) * self.bbp_array * self.chl_array ** (0.253)
            return True
        except Exception as ex:
            print(f'[ERROR] POC Loisel algorithm failed: {ex}')
            return False

    def run_owt(self):
        if not self.VALID:
            return False
        if self.Class is not None and self.proba is not None:
            return True

        print(f'[INFO] Running classification...')
        try:
            self.Class, self.proba, _, _, _, _ = classification(self.rrs_array[self.brefs['412'],:], self.rrs_array[self.brefs['443'],:],
                                              self.rrs_array[self.brefs['490'],:], self.rrs_array[self.brefs['510'],:],
                                              self.rrs_array[self.brefs['555'],:], self.rrs_array[self.brefs['670'],:])

            return True
        except Exception as ex:
            print(f'[ERROR] Classification OWT algorithm failed: {ex}')
            return False

    def run_poc_ocroc(self):
        if not self.VALID:
            return None
        if not self.run_poc_le():
            return None
        if not self.run_poc_tran():
            return None
        if not self.run_poc_loisel():
            return None
        if not self.run_owt():
            return None

        flag1 = (
                (self.Class == 0)
                & (self.rrs_array[self.brefs['412'],:] > self.rrs_array[self.brefs['490'],:])
                & (self.rrs_array[self.brefs['490'],:] > self.rrs_array[self.brefs['670'],:])
        )

        flag2 = self.rrs_array[self.brefs['670'],:] < 0.0001

        flag3 = (
                (self.rrs_array[self.brefs['412'],:] > self.rrs_array[self.brefs['443'],:])
                & (self.rrs_array[self.brefs['490'],:] > self.rrs_array[self.brefs['443'],:])
        )

        # Weighted POC for the different OWC
        proba_tran = np.sum(self.proba[1:8, :], axis=0)
        proba_loisel = np.sum(self.proba[8:, :], axis=0)

        poc_weight = (
                self.proba[0, :] * self.POC_Le
                + proba_tran * self.POC_Tran
                + proba_loisel * self.POC_Loisel
        )

        # flag1 : class 1 probability is ignored and other probabilities are renormalized
        flag1[10000:40000] = True
        if np.sum(flag1)>0:
            denom = 1 - self.proba[0, flag1]
            valid = denom != 0
            flag1_indices = np.where(flag1)
            rows = flag1_indices[0][valid]
            poc_weight[rows] = (
                    (proba_tran[rows] / denom[valid]) * self.POC_Tran[rows]
                    + (proba_loisel[rows] / denom[valid]) * self.POC_Loisel[rows]
            )
        ##flag 2: Loisel
        if np.sum(flag2):
            poc_weight[flag2] = self.POC_Loisel[flag2]
        ##flag 3 : Loisel
        if np.sum(flag3):
            poc_weight[flag3] = self.POC_Loisel[flag3]

        return poc_weight

    def check_indices_bands(self):
        n_bands  = len(self.bands)
        if n_bands!=self.rrs_array.shape[0]:
            print(f'[ERROR] Number of bands should be equal to the first dimension in the rrs array.')
            return False
        n_data = self.rrs_array.shape[1]
        if n_data!=self.chl_array.shape[0]:
            print(f'[ERROR] Number of spectra ({n_data}) should be equal to the number of data in the chl array.')
            return False
        if n_data!=self.chl_array.shape[0]:
            print(f'[ERROR] Number of spectra ({n_data}) should be equal to the number of data in the bbp array.')
            return False

        bands_ref = np.reshape(np.tile(np.array([412, 443, 490, 510, 555, 670]),n_bands),(n_bands,6))
        input_bands = np.reshape(np.repeat(self.bands,6),(n_bands,6))
        diffs = np.abs(input_bands-bands_ref)
        min_indices = np.argmin(diffs,axis=0)
        min_diff = np.min(diffs,axis=0)
        if np.max(min_diff) > self.wl_diff_max:
            indices_oor = np.where(min_diff>self.wl_diff_max)
            bands_ref_oor = np.array([412, 443, 490, 510, 555, 670])[indices_oor]
            input_bands_oor = np.array(self.bands)[indices_oor]
            print(f'[ERROR] The required band(s) {bands_ref_oor.tolist()} show wavelengths ({input_bands_oor.tolist()}) over the allowed difference of {self.wl_diff_max} nm')
            return False
        else:
            refs = ['412', '443', '490', '510', '555', '670']
            self.brefs = {refs[iref]:int(min_indices[iref]) for iref in range(len(refs))}
            return True



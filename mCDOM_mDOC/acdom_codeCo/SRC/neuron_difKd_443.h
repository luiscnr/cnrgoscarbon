#include <stdio.h>
#define MAX_DNE 6
/* =======================================================================================================
 * OLCI 
 * ======================================================================================================= */
/* Definition  des variables pour le reseau avec Rrs490/Rrs555 >= .85 */
/* nombre de couches cachees - hidden layer number */
#define rsup_DNC 2
/* nombre de donnees d entree - input data number*/
#define rsup_DNE 5
/* nombre de neurones de la premiere couche cachee - number of neuron in the first hidden layer */
#define rsup_DNC1 8
/* nombre de neurones de la deuxieme couche cachee */
#define rsup_DNC2 8
/* nombre de donnees de sortie - nb output*/
#define rsup_DNS 1
/* nombre de neurones d'entree + sortie - nb input + nb output*/
#define rsup_DNES 6

/* LUTs file names */
#define rsup_D_LUT_POIDS "KdOLCI_poids_ascii_5x1_hh_8_8_muw_sup_443_555.sn"
#define rsup_D_LUT_MOY "Moy_KdOLCI_IOCCG_diff_443_555_muw.dat"
#define rsup_D_LUT_ECART "Ecart_KdOLCI_diff_443_555_muw.dat"


/* Definition  des variables pour le reseau avec Rrs490/Rrs555 < .85 */
/* nombre de couches cachees - hidden layer number */
#define rinf_DNC 2
/* nombre de donnees d entree - input data number*/
#define rinf_DNE 6
/* nombre de neurones de la premiere couche cachee - number of neuron in the first hidden layer */
#define rinf_DNC1 8
/* nombre de neurones de la deuxieme couche cachee */
#define rinf_DNC2 8
/* nombre de donnees de sortie - nb output*/
#define rinf_DNS 1
/* nombre de neurones d'entree + sortie - nb input + nb output*/
#define rinf_DNES 7

/* LUTs file names */
#define rinf_D_LUT_POIDS "KdOLCI_poids_ascii_6x1_hh_8_8_muw_inf_443_555.sn"
#define rinf_D_LUT_MOY "Moy_KdOLCI_IOCCG_diff_443_555_muw.dat"
#define rinf_D_LUT_ECART "Ecart_KdOLCI_diff_443_555_muw.dat"

/* LUTs parameters definition */
float rsup_Db1[rsup_DNC1], rsup_Db2[rsup_DNC2], rsup_Db3;
float rsup_Dw1[rsup_DNE][rsup_DNC1], rsup_Dw2[rsup_DNC1][rsup_DNC2], rsup_Dw3[rsup_DNC2];
float rsup_Dmoy[rsup_DNES], rsup_Decart[rsup_DNES];

float rinf_Db1[rinf_DNC1], rinf_Db2[rinf_DNC2], rinf_Db3;
float rinf_Dw1[rinf_DNE][rinf_DNC1], rinf_Dw2[rinf_DNC1][rinf_DNC2], rinf_Dw3[rinf_DNC2];
float rinf_Dmoy[rinf_DNES], rinf_Decart[rinf_DNES];




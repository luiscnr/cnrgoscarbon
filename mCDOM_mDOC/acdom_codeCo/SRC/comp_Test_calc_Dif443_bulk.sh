gcc -c neuron_difKd_443.c -Wall -g
gcc -c function_acdom.c -Wall -g
gcc Test_calc_Dif443.c -o Test_calc_Dif443 function_acdom.o neuron_difKd_443.o -lm -Wall -g

#!/bin/bash
for FILE in `ls *.csv`
do

cd /Users/GabiB/Dropbox/PhD_ACRI_CNES/CodigosPython/FromDavid/acdom_codeCo/gabi_acdom443/SRC/

./Test_calc_Dif443 /Volumes/GABRIELA/PhD_ACRI_CNES/DATA/GlobColour/L3m_1997-2019_25km_8D/RrsComplete/Input/${FILE} /Volumes/GABRIELA/PhD_ACRI_CNES/DATA/GlobColour/L3m_1997-2019_25km_8D/RrsComplete/Output/${FILE}

done

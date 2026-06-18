gcc -c neuron_difKd_443.c -Wall -g
gcc -c function_acdom.c -Wall -g
gcc Test_calc_Dif443.c -o Test_calc_Dif443 function_acdom.o neuron_difKd_443.o -lm -Wall -g

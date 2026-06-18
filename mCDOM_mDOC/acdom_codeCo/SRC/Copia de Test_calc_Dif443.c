#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <math.h>
#include <string.h>
#include <memory.h>

#include "neuron_difKd_443.h"
#define NBLO 6
#define idx490 2
#define idx560 4

/* PROTOTYPES */
extern void  neuron_lect_LUTs_dif443(char *LUT_PATH);
extern float rinf_D443_neuron_passe_avant(float input[MAX_DNE]);
extern float rsup_D443_neuron_passe_avant(float input[MAX_DNE]);

/*-----------------------------------------------------------------------------
  Linear interpolation
 -----------------------------------------------------------------------------*/
float interp_line(x1,x2,x,y1,y2)
float x1,x2, x;
float y1, y2;
{
  float a,b,y;
  a=(y2-y1)/(x2-x1);
  b=y1-(a*x1);
  y=a*x+b;
  return y;
}

int main (int argc, char *argv[])
{
  FILE *fic_in, *fic_out;
  float  RRS[NBLO], INDIF[MAX_DNE], ASOL, muw,id;
  int    status,j;
  double diffKd;
  
  if(argc != 3){
    printf("Nombre d'arguments %d invalide\n", argc);
    printf("Lancer avec en arguments :\n - fichier d'input contenant sur chaque ligne: ID, Rrs[412, 443, 490, 510, 560, 665], ASOL\n - nom du fichier de sortie\n");
    exit(-1);
  }
  
  neuron_lect_LUTs_dif443("../LUTS");
  
  if((fic_in=fopen(argv[1],"r"))==NULL)  {perror(argv[1]); exit(-1);}

  if((fic_out=fopen(argv[2],"w"))==NULL) {perror(argv[2]); exit(-1);}
  fprintf(fic_out,"id DiffKd443\n");
  while((status=fscanf(fic_in,"%f %f %f %f %f %f %f %f", &id, &RRS[0], &RRS[1], &RRS[2], &RRS[3], &RRS[4], &RRS[5], &ASOL)) == 8)
  {
    muw = (float)cos(asin(sin(((double)ASOL)*M_PI/180.)/1.34));
    if ( RRS[idx490]/RRS[idx560] >= .85 ){
      if (RRS[1]>0. && RRS[2]>0. && RRS[3]>0. && RRS[4]>0.){
        for (j=0; j<rsup_DNE-1; j++)
          INDIF[j]  = RRS[j+1];
        INDIF[rsup_DNE-1] = muw;
        diffKd = (double)rsup_D443_neuron_passe_avant(INDIF); /* calcul de la difference de Kd directement par le reseau de neurones */
        fprintf(fic_out,"%g %g\n", id, diffKd);
      }
      else
        fprintf(fic_out,"-999.\n");
    }
    else{
      if (RRS[1]>0. && RRS[2]>0. && RRS[3]>0. && RRS[4]>0. && RRS[5]>0.){
        for (j=0; j<rinf_DNE-1; j++)
          INDIF[j]  = RRS[j+1];
        INDIF[rinf_DNE-1] = muw;
        diffKd = (double)rinf_D443_neuron_passe_avant(INDIF); /* calcul de la difference de Kd directement par le reseau de neurones */
        fprintf(fic_out,"%g %g\n", id, diffKd);
      }
      else
        fprintf(fic_out,"-999.\n");
    }

  }
  fclose(fic_in);
  fclose(fic_out);

  return(0);
}

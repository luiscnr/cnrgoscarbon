/*

 D. Dessailly david.dessailly@univ-littoral.fr
 2019-03-14
 Laboratoire d'Oceanoligie et Geoscience (LOG)
*/

#include <stdio.h>
#include <math.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <memory.h>
#include "neuron_difKd_443.h"

/* -------------------------------------------------------------------------------
  Lecture des differentes Look Up Tables  -  LUTs reading
   - Files names and path define in neuron_difKd443.h
 -------------------------------------------------------------------------------  */
void neuron_lect_LUTs_dif443(char LUT_PATH[])
{
  FILE *fic;
  int i,j,poub;
  char *ligne=malloc(sizeof(char)*150), nomfic[500];
  float fpoub;

  if( (poub = strcmp(LUT_PATH, "None")) == 0){
    if( (LUT_PATH = getenv("IOP_LUTS_PATH")) == NULL) {perror("IOP_LUTS_PATH"); exit(-1);}
  }
  /* ----- LUTs for Rrs490/Rrs555 >= .85 ------ */
  sprintf(nomfic,"%s/%s", LUT_PATH, rsup_D_LUT_POIDS);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fgets(ligne,150,fic);
  for(i=0; i<rsup_DNC1; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Db1[i]);
  for(i=0; i<rsup_DNC2; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Db2[i]);
  fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Db3);
  for(j=0; j<rsup_DNE; j++){
    for(i=0; i<rsup_DNC1; i++)
      fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Dw1[j][i]);
  }
  for(j=0; j<rsup_DNC1; j++){
    for(i=0; i<rsup_DNC2; i++)
      fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Dw2[j][i]);
  }
  for(i=0; i<rsup_DNC2; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rsup_Dw3[i]);
  fclose(fic);

  sprintf(nomfic,"%s/%s", LUT_PATH, rsup_D_LUT_MOY);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fscanf(fic,"%f",&fpoub); /*412*/
  fscanf(fic,"%f",&rsup_Dmoy[0]); /*443*/
  fscanf(fic,"%f",&rsup_Dmoy[1]); /*490*/
  fscanf(fic,"%f",&rsup_Dmoy[2]); /*510*/
  fscanf(fic,"%f",&rsup_Dmoy[3]); /*560*/
  fscanf(fic,"%f",&fpoub); /*620*/
  fscanf(fic,"%f",&fpoub); /*665*/
  fscanf(fic,"%f",&fpoub); /*wl*/
  fscanf(fic,"%f",&rsup_Dmoy[rsup_DNE-1]); /*muw*/
  fscanf(fic,"%f",&fpoub); /*diff(412-560)*/
  fscanf(fic,"%f",&rsup_Dmoy[rsup_DNES-1]); /*diff(443-560)*/
  fclose(fic);
  sprintf(nomfic,"%s/%s", LUT_PATH, rsup_D_LUT_ECART);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fscanf(fic,"%f",&fpoub); /*412*/
  fscanf(fic,"%f",&rsup_Decart[0]); /*443*/
  fscanf(fic,"%f",&rsup_Decart[1]); /*490*/
  fscanf(fic,"%f",&rsup_Decart[2]); /*510*/
  fscanf(fic,"%f",&rsup_Decart[3]); /*560*/
  fscanf(fic,"%f",&fpoub); /*620*/
  fscanf(fic,"%f",&fpoub); /*665*/
  fscanf(fic,"%f",&fpoub); /*wl*/
  fscanf(fic,"%f",&rsup_Decart[rsup_DNE-1]); /*muw*/
  fscanf(fic,"%f",&fpoub); /*diff(412-560)*/
  fscanf(fic,"%f",&rsup_Decart[rsup_DNES-1]); /*diff(443-560)*/
  fclose(fic);

/* ----- LUTs for Rrs490/Rrs555 < .85 ------ */
  sprintf(nomfic,"%s/%s", LUT_PATH, rinf_D_LUT_POIDS);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fgets(ligne,150,fic);
  for(i=0; i<rinf_DNC1; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Db1[i]);
  for(i=0; i<rinf_DNC2; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Db2[i]);
  fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Db3);
  for(j=0; j<rinf_DNE; j++){
    for(i=0; i<rinf_DNC1; i++)
      fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Dw1[j][i]);
  }
  for(j=0; j<rinf_DNC1; j++){
    for(i=0; i<rinf_DNC2; i++)
      fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Dw2[j][i]);
  }
  for(i=0; i<rinf_DNC2; i++)
    fscanf(fic,"%d %d %f",&poub,&poub,&rinf_Dw3[i]);
  fclose(fic);

  sprintf(nomfic,"%s/%s", LUT_PATH, rinf_D_LUT_MOY);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fscanf(fic,"%f",&fpoub); /*412*/
  fscanf(fic,"%f",&rinf_Dmoy[0]); /*443*/
  fscanf(fic,"%f",&rinf_Dmoy[1]); /*490*/
  fscanf(fic,"%f",&rinf_Dmoy[2]); /*510*/
  fscanf(fic,"%f",&rinf_Dmoy[3]); /*560*/
  fscanf(fic,"%f",&fpoub); /*620*/
  fscanf(fic,"%f",&rinf_Dmoy[4]); /*665*/
  fscanf(fic,"%f",&fpoub); /*wl*/
  fscanf(fic,"%f",&rinf_Dmoy[rinf_DNE-1]); /*muw*/
  fscanf(fic,"%f",&fpoub); /*diff(412-560)*/
  fscanf(fic,"%f",&rinf_Dmoy[rinf_DNES-1]); /*diff(443-560)*/
  fclose(fic);
  sprintf(nomfic,"%s/%s", LUT_PATH, rinf_D_LUT_ECART);
  if( (fic=fopen(nomfic,"r")) == NULL) {perror(nomfic); exit(-1);}
  fscanf(fic,"%f",&fpoub); /*412*/
  fscanf(fic,"%f",&rinf_Decart[0]); /*443*/
  fscanf(fic,"%f",&rinf_Decart[1]); /*490*/
  fscanf(fic,"%f",&rinf_Decart[2]); /*510*/
  fscanf(fic,"%f",&rinf_Decart[3]); /*560*/
  fscanf(fic,"%f",&fpoub); /*620*/
  fscanf(fic,"%f",&rinf_Decart[4]); /*665*/
  fscanf(fic,"%f",&fpoub);
  fscanf(fic,"%f",&rinf_Decart[rinf_DNE-1]);
  fscanf(fic,"%f",&fpoub);
  fscanf(fic,"%f",&rinf_Decart[rinf_DNES-1]);
  fclose(fic);
}

/* -------------------------------------------------------------------------------
 diffKd443 computation
 - Input:
  input[NE] = Rrs(443 490 510 560) muw
 ------------------------------------------------------------------------------- */
float rsup_D443_neuron_passe_avant(float input[MAX_DNE])
{
  float a[rsup_DNC1], b[rsup_DNC2], y=0.0, x[rsup_DNE];
  int i,j;

  /* Normalisation */
  for(i=0; i<rsup_DNE; i++){
    x[i] = ((2./3.)*(input[i]-rsup_Dmoy[i]))/rsup_Decart[i];
  }

  for(i=0;i<rsup_DNC1;i++){
    a[i] = 0.0;
    for(j=0;j<rsup_DNE;j++){
      a[i] += (x[j]*rsup_Dw1[j][i]);
    }
    a[i] = 1.715905*(float)tanh((2./3.)*(double)(a[i] + rsup_Db1[i]));
  }
  for(i=0;i<rsup_DNC2;i++){
    b[i] = 0.0;
    for(j=0;j<rsup_DNC1;j++){
      b[i] += (a[j]*rsup_Dw2[j][i]);
    }
    b[i] = 1.715905*(float)tanh((2./3.)*(double)(b[i] + rsup_Db2[i]));
  }
  for(j=0;j<rsup_DNC2;j++){
    y += (b[j]*rsup_Dw3[j]);
  }

  /* Denormalisation */
  y = 1.5*(y + rsup_Db3)*rsup_Decart[rsup_DNES-1] + rsup_Dmoy[rsup_DNES-1];
  return(y);
}

/* -------------------------------------------------------------------------------
 Calcul de la diffKd a partir des poids
 - Input:
  input[NE] = Rrs(443 490 510 560 665) muw
 ------------------------------------------------------------------------------- */
float rinf_D443_neuron_passe_avant(float input[MAX_DNE])
{
  float a[rinf_DNC1], b[rinf_DNC2], y=0.0, x[rinf_DNE];
  int i,j;

  /* Normalisation */
  for(i=0; i<rinf_DNE; i++){
    x[i] = ((2./3.)*(input[i]-rinf_Dmoy[i]))/rinf_Decart[i];
  }

  for(i=0;i<rinf_DNC1;i++){
    a[i] = 0.0;
    for(j=0;j<rinf_DNE;j++){
      a[i] += (x[j]*rinf_Dw1[j][i]);
    }
    a[i] = 1.715905*(float)tanh((2./3.)*(double)(a[i] + rinf_Db1[i]));
  }
  for(i=0;i<rinf_DNC2;i++){
    b[i] = 0.0;
    for(j=0;j<rinf_DNC1;j++){
      b[i] += (a[j]*rinf_Dw2[j][i]);
    }
    b[i] = 1.715905*(float)tanh((2./3.)*(double)(b[i] + rinf_Db2[i]));
  }
  for(j=0;j<rinf_DNC2;j++){
    y += (b[j]*rinf_Dw3[j]);
  }

  /* Denormalisation */
  y = 1.5*(y + rinf_Db3)*rinf_Decart[rinf_DNES-1] + rinf_Dmoy[rinf_DNES-1];
  return(y);
}

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <math.h>


extern float interp_line(float x1, float x2, float x, float y1, float y2);

/*-----------------------------------------------------------------------------
  Linear interpolation
 
float interp_line(x1,x2,x,y1,y2)
float x1,x2, x;
float y1, y2;
{
  float a,b,y;
  a=(y2-y1)/(x2-x1);
  b=y1-(a*x1);
  y=a*x+b;
  return y;
}-----------------------------------------------------------------------------*/

/* ----------------------------------------------------------------------------
 * calcul du DOC
 * ref : Vantrepotte
 ---------------------------------------------------------------------------- */
float calc_DOC(float acdom_412)
{
  float DOC;
  DOC = 1/((float)pow(10.,(0.7109*log10((double)acdom_412)-2.1722)))*acdom_412;
  return(DOC);
}

/*---------------------------------------------------------------*/
/*  Acdom  methode de Vantrepotte et Loisel                          */
/* Calcul de la différence de Kd 412-555                         */
/*---------------------------------------------------------------*/
float calc_diffKd_IOCCG(double lograp, float thetas)
{
  float res;
  float k1, k2;

/* version 412 */
 if(thetas <= 30.)
  {
    k1 = (float)pow(10.,(-0.06348084*lograp*lograp*lograp + 0.254858*lograp*lograp -1.22384*lograp -0.89454));
    k2 = (float)pow(10.,(-0.12484*lograp*lograp*lograp + 0.160857*lograp*lograp -1.2292*lograp -0.886471));
    res = interp_line(0.,30.,thetas,k1,k2);
  }
  else
  {
    k1 = (float)pow(10.,(-0.12484*lograp*lograp*lograp + 0.160857*lograp*lograp -1.2292*lograp -0.886471));
    k2 = (float)pow(10.,(-0.535652*lograp*lograp*lograp  -0.224119*lograp*lograp -1.18114*lograp -0.840784));
    res = interp_line(30.,60.,thetas,k1,k2);
  }

  return res;
}

/*---------------------------------------------------------------*/
/*  Acdom methode de Vantrepotte et Loisel                       */
/* Inputs :
 * - Rrs440
 * - Rrs555
 * - thetas
 *  - diffKd : si diffKd == -999 on calcule la differentce de Kd avec la methode de Vantrepotte/loisel
 *             sinon diffKd doit être initialisé avec la valeur calculee par la methode de Jamet (perceptron multicouche)
 * Output :
 *  acdom412 */
/*---------------------------------------------------------------*/
float calc_acdom_VL(double Rrs440, double Rrs555, float thetas, double diffKd)
{
  float acdom;
  double residu, X, lograp;

  /* Si diffKd est calcule par la methode Vantrepotte/loisel */
  if(diffKd < -998){
    lograp = log10(Rrs440/Rrs555);
    diffKd = calc_diffKd_IOCCG(lograp, thetas);
  }
  residu = pow(10.,-0.26 + 1.147 * log10(diffKd) -0.009 * log10(diffKd) * log10(diffKd));
  X = log10(diffKd-residu);
  acdom = (float)pow(10.,0.1548*X*X +1.1939*X +0.0689);

  return(acdom);
}


/*---------------------------------------------------------------*/
/*  Acdom methode de Swan et al 2013
 * */
float calc_acdom_Swan(float acdm443)
{
  float sig, acdomSwan;
  sig = 0.02 + 0.01 * powf(M_E, -80.66*acdm443);
  acdomSwan = 0.46*acdm443 * powf(M_E,(-sig*(412-443.)));
  
  return(acdomSwan);
}


// /* ----------------------------------------------------------------------------
//  * calcul de acdom 412 OLD OLD OLD
//  * ref : Mannino
//  ---------------------------------------------------------------------------- */
// float calc_acdom412_Manino(float Rrs490, float Rrs555)
// {
//   float res;
//   res = (float)log((double)(((Rrs490/(Rrs555))-0.6666)/3.73))/(-16.344);
//   return(res);
// }


/* ----------------------------------------------------------------------------
 * calcul de acdom 412 Aurin Appl. Sci. 2018 doi:10.3390/app8122687
 * ref : Mannino
 ---------------------------------------------------------------------------- */
float calc_acdom412_Aurin(float Rrs443, float Rrs490, float Rrs510, float Rrs555)
{
  float res;
  double B0=-6.004, B1=-0.861, B2=-0.006, B3=-0.345, B4=0.515;
  res = (float)pow(M_E, ( B0 + B1*log((double)Rrs443) + B2*log((double)Rrs490) + B3*log((double)Rrs510) + B4*log((double)Rrs555) ) );
  return(res);
}



// 
// /* ----------------------------------------------------------------------------
//  * calcul de acdom 412
//  * ref : D'sa
//  ---------------------------------------------------------------------------- */
// float calc_acdom412_Dsa(float Rrs510, float Rrs555)
// {
//   float res;
//   res = 0.177*(float)pow((double)(Rrs510 / Rrs555),-2.123);
//   return(res);
// }
// 
// /* ----------------------------------------------------------------------------
//  * calcul de acdom 412
//  * ref : D'sa
//  ---------------------------------------------------------------------------- */
// float calc_acdom412_Tiwari(float Rrs490, float Rrs670)
// {
//   float res;
//   res = (float)pow(10., 0.625*log10((double)(Rrs670/Rrs490))-.3);
//   return(res);
// }
// 
// /* ----------------------------------------------------------------------------
//  * calcul de acdom / atot
//  * ref : Bellanger
//  ---------------------------------------------------------------------------- */
// float calc_acdomSatot(float RRS[NBLO+1])
// {
//   float res, alpha=-0.387, beta=-0.387, chi=0.577, delta=-0.390;
//   res = alpha + beta*(float)log10((double)(RRS[0]/RRS[4])) + chi*(float)log10((double)(RRS[2]/RRS[4])) + delta*(float)log10((double)RRS[4]);
//   return(res);
// }

/* ----------------------------------------------------------------------------
 * acdom 443 Gabi
 * 
 ---------------------------------------------------------------------------- */
float calc_acdom443(double diffkd)
{
  double pdp, x, pacdom;
  
  pdp    = pow(10.,(0.906040175463018*log10(diffkd)-0.5259306235301482));
  x      = diffkd-pdp;
  pacdom = pow(10.,( 0.9901899987526812*log10(x)-0.05217938868943062));
  return((float)pacdom);
}

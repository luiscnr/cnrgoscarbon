#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  9 16:02:59 2024

@author: montero, after 
"""
#code after the https://github.com/manhtranduy/Chl-CONNECT.git common.classification_functions
#get GitHUb rep

import numpy as np
from scipy.integrate import trapezoid
from scipy.special import gamma, gammainc
from scipy.stats import multivariate_normal
import os

import warnings
warnings.simplefilter('ignore', RuntimeWarning)

def normalize_Rrs(Rrs,wave_lengths):
    """
    Normalizes remote sensing reflectance (Rrs) data by calculating the area under the curve for each row of data. 
    This normalization helps in preprocessing data for further analysis and classification.
    
    Parameters:
        Rrs (np.ndarray): The remote sensing reflectance data as a numpy array.
        wave_lengths (np.ndarray): The corresponding wavelengths for the Rrs data.
    
    Returns:
        np.ndarray: The normalized Rrs data.
    
    Example:
        normalized_data = normalize_Rrs(Rrs_data, wave_lengths)
    """
    area = trapezoid(Rrs, wave_lengths, axis=1)
    
    # Normalize Rrs by the calculated area
    Rrs_norm = Rrs / area[:, np.newaxis]
    return Rrs_norm




def probability(model, rrs_norm, 
                method='pdf', 
                distribution='gamma',
                logRrs=True, 
                Flag=False):
    """
    Calculates the probability of Rrs data belonging to certain OWTs using specified models and methods. 
    This function can handle transformations such as logarithmic scaling of Rrs data before processing.
    
    Parameters:
        model (tuple): The model parameters, typically including mean and covariance matrices.
        rrs_norm (np.ndarray): Normalized Rrs data on which probabilities are to be computed.
        method (str, optional): The method to compute probabilities, defaults to 'pdf'.
        distribution (str, optional): The assumed distribution for the calculation, defaults to 'gamma'.
        logRrs (bool, optional): Indicates if logarithmic transformation was applied, defaults to True.
    
    Returns:
        tuple: The classification results, including class probabilities and, optionally, other metrics.
    
    Example:
        class_probs = probability(model, normalized_data, method='pdf', distribution='gamma', logRrs=True)
    """
   # Transform Rrs
    if logRrs:
        rrs_input = np.log10(rrs_norm.astype(float))
    else:
        rrs_input = rrs_norm

    # Find indices of rows without NaNs
    valid_indices = ~np.isnan(rrs_input).any(axis=1) & ~np.isinf(rrs_input).any(axis=1)
    valid_rrs_input = rrs_input[valid_indices]
        
    if method == 'pdf':
        if not isinstance(model, (list, tuple)) or len(model) != 2:
            raise ValueError('Input must be a tuple or list containing covariance and mean matrices')
        cov_matrix, mean_matrix = model
        nc = mean_matrix.shape[2]  # Number of classes
        b = mean_matrix.shape[1]   # Number of bands

        
        # Calculate Mahalanobis distance and PDF only for valid rows
        D = np.empty((valid_rrs_input.shape[0], nc), dtype=np.float64)
        Pdf = np.empty((valid_rrs_input.shape[0], nc), dtype=np.float64)
        for i in range(nc):
            # Calculate Mahalanobis distance for each class
            diff = valid_rrs_input[:, np.newaxis, :] - mean_matrix[:, :, i]
            inv_cov_matrix = np.linalg.inv(cov_matrix[:, :, i])
            mahalanobis_dist = np.sum((diff @ inv_cov_matrix) * diff, axis=2)
            D[:, i] = mahalanobis_dist.reshape(-1)
            
            # Calculate PDF based on the distribution
            if distribution == 'normal':
                threshold_D=1488
                Pdf[:, i] = multivariate_normal.pdf(valid_rrs_input, mean=mean_matrix[:, :, i].ravel(), cov=cov_matrix[:, :, i])
            elif distribution == 'gamma':
                threshold_D=432
                D_over_2 = D[:, i] / 2
                Pdf[:, i] = gammainc(D_over_2, b / 2) / gamma(b / 2)
                
        
        # Treating unclssified pixels
        unclassified_ind = np.all(Pdf == 0, axis=1)
        D_tmp = D[unclassified_ind, :]
        
        # Iterate over each row in D_tmp
        for i in range(D_tmp.shape[0]):
            # Apply square root to the entire row until all elements are less than 1488
            while np.any(D_tmp[i, :] > threshold_D):
                D_tmp[i, :] = np.sqrt(D_tmp[i, :])
        
        D[unclassified_ind, :] = D_tmp
                        
        for i in range(nc):
            # Calculate PDF based on the distribution
            if distribution == 'normal':
                MS = ((2 * np.pi) ** (b / 2)) * np.sqrt(np.linalg.det(cov_matrix[:, :, i]))
                Pdf[unclassified_ind, i] = (1 / MS) * np.exp(-0.5 * D[unclassified_ind, i])
                
            elif distribution == 'gamma':
                D_over_2 = np.sqrt(D[unclassified_ind, i]) / 2 
                Pdf[unclassified_ind, i] = gammainc(D_over_2, b / 2) / gamma(b / 2)
                
                
        # Normalize probabilities
        if Flag == True:
            Pdf[:,0]= 0
            
        p = np.full((rrs_norm.shape[0], nc),np.nan)
        Pdf_sum = Pdf.sum(axis=1, keepdims=True)
        p[valid_indices] = Pdf / Pdf_sum.reshape(-1, 1)
    if method =='logreg':
        logreg_model, scaler = model
        nc = len(logreg_model.classes_)
        valid_rrs_input = scaler.transform(valid_rrs_input)

        p = np.full((rrs_norm.shape[0], nc),np.nan)
        p[valid_indices]=logreg_model.predict_proba(valid_rrs_input)

    # Determine class with highest probability
    Class = np.zeros(rrs_norm.shape[0], dtype=int)
    # max_val = np.zeros(rrs_norm.shape[0], dtype=np.float32)
    if valid_indices.any():
        Class[valid_indices] = np.argmax(p[valid_indices,:], axis=1) + 1  # Adding 1 to match MATLAB's 1-indexing
   
    
    return Class, p



def Eumetsat_classif17(Rrs,
                       method='pdf', 
                       distribution='gamma',
                       sensor='OLCI',
                       logRrs=True,
                       spectralShift=False,
                       Flag=False):
    """
    Classifies Rrs data into 17 OWTs according to Melin & Vantrepotte., (2015). 
    This function supports multiple methods and distributions,
    tailored specifically for chlorophyll data analysis from satellite imagery.
    
    Parameters:
        Rrs (np.ndarray): Remote sensing reflectance data, potentially multi-dimensional.
        method (str, optional): Classification method to use, defaults to 'pdf'.
        distribution (str, optional): Assumed distribution for classification, defaults to 'gamma'.
        sensor (str, optional): Type of sensor data being classified, defaults to 'OLCI'.
        logRrs (bool, optional): Indicates if Rrs data has been logarithmically transformed, defaults to True.
        spectralShift (bool, optional): Indicates if spectral shift corrections are applied, defaults to False.
    
    Returns:
        tuple: A tuple containing classified labels and probabilities, structured according to input dimensions.
    
    Example:
        predicted_classes, probabilities = Eumetsat_classify17(Rrs_data)
    """
    if isinstance(Rrs, list):
        Rrs = np.stack(Rrs,2)
        
    if sensor == 'OLCI':
        waveLengths_visible=[412,443,490,510,560,665]
    elif sensor =='MODIS':
        waveLengths_visible=[412,443,488,531,551,667]
    elif sensor == 'MSI':
        waveLengths_visible=[443,490,560,665]

    if len(Rrs.shape)==2:
        if Rrs.shape[1]!=len(waveLengths_visible):
            AssertionError(f'Rrs must contain {len(waveLengths_visible)} columns corresponding to \
                           {waveLengths_visible} of {sensor} sensor')
        rows, cols = (-1,1)
    elif len(Rrs.shape)==3:
        if Rrs.shape[2]!=len(waveLengths_visible):
            AssertionError(f'Rrs must contain {len(waveLengths_visible)} components in the 3rd dimension corresponding to \
                           {waveLengths_visible} of {sensor} sensor')
        rows, cols, bands = Rrs.shape
        Rrs = Rrs.reshape(rows * cols, bands)
        
    if spectralShift:
        neg_mask=np.any(Rrs<0,axis=1)
        neg_vals=Rrs[neg_mask,np.argmin(Rrs[neg_mask,:],axis=1)]
        Rrs[neg_mask,:]=Rrs[neg_mask,:]+abs(neg_vals.reshape(-1,1))+10**-6
    
    Rrs[Rrs>10]=np.nan

    Rrs_norm = normalize_Rrs(Rrs,waveLengths_visible)
    #
    file_path = os.path.join(os.path.dirname(__file__),'LUTs',sensor,'17OWTs',method)

    if method == 'pdf':
        covariance_matrix_17 = np.full((6,6,17),np.nan)
        mean_matrix_17 = np.full((1,6,17),np.nan)
    
        for i in range(17):
            cov_file = os.path.join(file_path, f'Cov17_C{i+1}.txt')
            mean_file = os.path.join(file_path, f'Mean17_C{i+1}.txt')
    
            try:
                covariance_matrix_17[:, :, i] = np.loadtxt(cov_file)  # Load covariance matrix from file
                mean_matrix_17[:, :, i] = np.loadtxt(mean_file).T
            except:
                covariance_matrix_17[:, :, i] = np.loadtxt(cov_file, delimiter=',')  # Load covariance matrix from file
                mean_matrix_17[:, :, i] = np.loadtxt(mean_file, delimiter=',').T
    
        model=(covariance_matrix_17,mean_matrix_17)
    elif method == 'logreg':
        import joblib
        if logRrs:
            model_logreg = joblib.load(os.path.join(file_path,'logRrs','17OWTs_logreg.pkl'))
            scaler = joblib.load(os.path.join(file_path,'logRrs','17OWTs_logreg_scaler.pkl'))
        else:
            model_logreg = joblib.load(os.path.join(file_path,'Rrs','17OWTs_logreg.pkl'))
            scaler = joblib.load(os.path.join(file_path,'Rrs','17OWTs_logreg_scaler.pkl'))


        model = (model_logreg,scaler)

    Class,p = probability(model, Rrs_norm,method=method,distribution=distribution,logRrs=logRrs)
    Class[np.all(np.isnan(Rrs),axis=1)]=0
    p[np.all(np.isnan(Rrs),axis=1),:]=np.nan
    Class = Class.reshape(rows,cols).flatten()
    P=[]
    for i in range(p.shape[1]):
        P.append(p[:,i].reshape(rows,cols))
    return Class, P




def classification(NRRS412, NRRS443, NRRS490, NRRS510, NRRS560, NRRS665):
    
    
    ip1=[NRRS412, NRRS443, NRRS490, NRRS510, NRRS560, NRRS665]
    ip=np.array(ip1).T
 
    
    C,P= Eumetsat_classif17(ip)
    del ip
   
    Flag1 = (NRRS665 < 0.0001)
    Flag2 = (NRRS412 > NRRS443) & (NRRS443 > NRRS490)
    Flag3 = (NRRS412 > NRRS490) & (NRRS490 > NRRS560)
    Flag4 = (Flag3==True) & (np.array(C) == 1)
    

    #relaunch Classification if Flag4 is true => False indentification of class 1
  
  
    flagged_ip = [np.array(data)[Flag4] for data in ip1]
    flagged_ip=np.array(flagged_ip).T
    
 
    Cflag, Pflag = Eumetsat_classif17(flagged_ip, Flag=True)
    #remove 
    
    del flagged_ip
    
    # Step 3: Replace old C values with new ones
    C[Flag4 ==True] = Cflag

    #transform P and Pflag into an np.array and squeeze them 
    P     = np.array(P).squeeze()
    Pflag = np.array(Pflag).squeeze()
    
    # Step 4: Replace old P values with new ones
    for i in range(17):
       P[i][Flag4==True] = Pflag[i] # Replace rows in each probability array

   
    return C, P, np.array(Flag1), np.array(Flag2), np.array(Flag3), np.array(Flag4)


    




























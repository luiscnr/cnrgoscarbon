#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 14:27:24 2024

@author: montero
"""

import os

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

import numpy as np
#import datetime

import xarray as xr
import tensorflow as tf

import pandas as pd

# Just disables the warning, doesn't take advantage of AVX/FMA to run faster

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import time
#import datetime as dt

#from netCDF4 import Dataset


def get_model_path():
    # Get the absolute path of the current script (Run_DOC.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the model folder relative to this script
    model_path = os.path.join(current_dir, "ANN")
    
    return model_path



def Run_DOC_model(datasets, date):
    

    #get paths to ANN related files, situated in the same fodler
    path_models = get_model_path()

  
    ######################### LOAD SCALERS AND TARGET SCALER ######################
    
    # Load the pre-trained normalization/scaling models (scalers) to transform the
    # input data and target.
    # These scalers are used to normalize or scale the data before model prediction.
    # 'sca' and 'scb' are the scalers used for the input features, 
    # while 'target_scaler' is used to scale the target variable.
    
    
    from joblib import load
    
    # Load the scaler for the first set of input features
    sca = load(path_models+'/sca_scaler_1.pkl')
    
    # Load the scaler for the second set of input features
    scb = load(path_models+'/scb_scaler_2.pkl')
    
    # Load the scaler for the target variable (dependent variable)
    target_scalera = load(path_models+'/y_scaler_1.pkl')
    
    # Load the scaler for the target variable (dependent variable)
    target_scalerb = load(path_models+'/y_scaler_2.pkl')
    
   


    # ################################# LOAD MODEL ##################################


    from keras.models import load_model
    

    
    #####################################
    # MODEL 5 - Load pre-trained models
    # Path to the directory where the models are stored
   
    
    # Load the first neural network model (ANN model 1) using custom loss function for model 1
    model_ANNa = load_model(path_models + '/DOCANN1.keras', compile=False)
    
    # Load the second neural network model (ANN model 2) using custom loss function for model 2
    model_ANNb = load_model(path_models + '/DOCANN2.keras', compile=False)
    
    # Display summaries of the two models to show their architecture and details
    print("Model loaded\n")
    model_ANNa.summary(), model_ANNb.summary()
    
    print("\n")
    
    
      
    #################### Create Function of NaN in Probabilities ##################
    
    # This function calculates and adjusts DOC values based on class probabilities, 
    # handling NaN values. It uses a threshold of 80% for probability sums to 
    # adjust DOC values (doca, docb, docc) accordingly, applying conditions 
    # to fill or modify missing data.
    
    
 

    def jointdoc(Proba, limit, doca, docb, docc, threshold=0.8):
        """
        Fuse three DOC maps (doca, docb, docc) using probability weights.
        - If all three maps exist → probability-weighted mean
        - If one or two are NaN → probability-weighted fusion of available ones
        - If only one available but below threshold → NaN
        
        Returns:
            A (np.ndarray): fused DOC map
            case_map (np.ndarray): integer case identifier
            """
    
       # --- Extract probability subsets ---
      
        Pa = Proba.sel(pclass=np.arange(limit + 1, 10)).sum(dim='pclass').values
        Pb = Proba.sel(pclass=np.arange(10, 18)).sum(dim='pclass').values
        Pc = Proba.sel(pclass=np.arange(1, limit + 1)).sum(dim='pclass').values
    
       # Ensure arrays are numpy
        doca = np.asarray(doca)
        docb = np.asarray(docb)
        docc = np.asarray(docc)

       # Prepare outputs
        A = np.full_like(doca, np.nan, dtype=float)
        case_map = np.zeros_like(doca, dtype=int)

       # --- CASE 10: All maps valid → probability-weighted mean ---
        mask_all = (~np.isnan(doca)) & (~np.isnan(docb)) & (~np.isnan(docc))
        denom = (Pa + Pb + Pc)
        valid = mask_all & (denom > 0)
        A[valid] = (Pa[valid] * doca[valid] +
                    Pb[valid] * docb[valid] +
                    Pc[valid] * docc[valid]) / denom[valid]
        case_map[valid] = 10

       # --- CASE 1: doca missing → fuse docb + docc ---
        mask = (np.isnan(doca)) & (~np.isnan(docb)) & (~np.isnan(docc))
        valid = (Pb >= 0.4) & (Pc >= 0.4) & ((Pb + Pc) >= 0.8)
        denom = (Pb + Pc)
        good = mask & valid & (denom > 0)
        A[good] = (Pb[good] * docb[good] + Pc[good] * docc[good]) / denom[good]
        case_map[good] = 1

       # --- CASE 2: docb missing → fuse doca + docc ---
        mask = (~np.isnan(doca)) & (np.isnan(docb)) & (~np.isnan(docc))
        valid = (Pa >= 0.4) & (Pc >= 0.4) & ((Pa + Pc) >= 0.8)
        denom = (Pa + Pc)
        good = mask & valid & (denom > 0)
        A[good] = (Pa[good] * doca[good] + Pc[good] * docc[good]) / denom[good]
        case_map[good] = 2
    
       # --- CASE 3: docc missing → fuse doca + docb ---
        mask = (~np.isnan(doca)) & (~np.isnan(docb)) & (np.isnan(docc))
        valid = (Pa >= 0.4) & (Pb >= 0.4) & ((Pa + Pb) >= 0.8)
        denom = (Pa + Pb)
        good = mask & valid & (denom > 0)
        A[good] = (Pa[good] * doca[good] + Pb[good] * docb[good]) / denom[good]
        case_map[good] = 3
    
       # --- CASE 4–6: only one DOC available and strong enough ---
        mask = (~np.isnan(doca)) & np.isnan(docb) & np.isnan(docc)
        good = mask & (Pa >= threshold)
        A[good] = doca[good]
        case_map[good] = 6
    
        mask = np.isnan(doca) & (~np.isnan(docb)) & np.isnan(docc)
        good = mask & (Pb >= threshold)
        A[good] = docb[good]
        case_map[good] = 5

        mask = np.isnan(doca) & np.isnan(docb) & (~np.isnan(docc))
        good = mask & (Pc >= threshold)
        A[good] = docc[good]
        case_map[good] = 4
    
       # --- Remaining pixels ---
        case_map[np.isnan(A)] = -1
    
        return A
        
   


    
    
    ###### MAIN #####
    
    
    # Set the limit for class selection and define parameters (slope and intercept) 
    # for the Vantrepotte model (Class 1). These values are used for calculations 
    
    limit = 1
    slope = 0.7627844657135349
    intercept = -2.226636156872628
    
    
   

    #start timer
    start_time = time.time()
    print(f"Create DOC for date: {date.strftime('%Y-%m-%d')}\n")

    #################### Load Environmental Data for Analysis ##################

    # Load datasets for specific environmental variables (SST, MLD, CHL, CDOM) 
        # for the current date, previous week, and two weeks ago. These are used in analysis:
        # - SST, MLD, and CHL are from the previous week.
        # - CDOM is loaded for two weeks ago and the current date.
        # - Class_Prop contains class probabilities for the current date.


    SST = xr.open_dataset(datasets['SST-1w'][0])
    MLD = xr.open_dataset(datasets['MLD-1w'][0])
    CHL = xr.open_dataset(datasets['CHL-1w'][0])

    CDOM = xr.open_dataset(datasets['CDOM-2w'][0])
    
    CDOM_d = xr.open_dataset(datasets['CDOM'][0])
    Class_Prop = xr.open_dataset(datasets['CandP'][0])
   
    #limit the MLD at 50m  
    MLD = MLD.where(MLD.isnull() | (MLD <= 150), other=150)

    # Replace all instances of class 0 in the 'Class' variable with NaN to exclude them from calculations.
    Class_Prop = Class_Prop.where(Class_Prop.Class != 0, np.nan)
    # Adjust the class indices by adding 1 to match the real cases.
    # This ensures the 'pclass' coordinate aligns with the actual class numbers.
    Class_Prop = Class_Prop.assign_coords(pclass=Class_Prop['pclass'] + 1)
    Proba    = Class_Prop.Probability
    Cla  = Class_Prop.Class

    # Extract and flatten environmental variables used for the ANN for the current dataset:
    file_VAR0 = np.log10(CDOM[list(CDOM.data_vars)[0]])
    file_VAR1 = SST[list(SST.data_vars)[0]]
    file_VAR2 = MLD[list(MLD.data_vars)[0]]
    file_VAR3 = np.log10(CHL[list(CHL.data_vars)[0]])
    
    VAR_Cdom = np.log10(CDOM_d[list(CDOM_d.data_vars)[0]]) 


    ################# Vectorize Data for Neural Networks ###############   
    # Prepare input data for two neural networks (A and B) by creating DataFrames:
    # - Network A uses four predictors: acdom_sat_2weeks, SST_1week, MLD_1week, and CHL-OC5_1week.
    # - Network B uses three predictors: acdom_sat_2weeks, SST_1week, and MLD_1week.

    # For Network A
    dfa = pd.DataFrame({
        'acdom_sat_2weeks': file_VAR0.values.flatten(),
        'SST_1week': file_VAR1.values.flatten(),
        'MLD_1week': file_VAR2.values.flatten(),
        'CHL-OC5_1week': file_VAR3.values.flatten()
    })

    # For Network B
    dfb = pd.DataFrame({
        'acdom_sat_2weeks': file_VAR0.values.flatten(),
        'SST_1week': file_VAR1.values.flatten(),
        'MLD_1week': file_VAR2.values.flatten()
    })
          
    ################### Predict DOC with Neural Networks ################

          
    # Use the prepared data to predict DOC values for specific class ranges
    # using two neural networks:
        # - Network A: Predicts for Classes 2-9 using the scaled input predictorsA.
        # - Network B: Predicts for Classes 10-17 using the scaled input predictorsB.
        # The predictions are inverse-transformed to return to the original scale.

    # Network A: Classes 4-9
    print("Launching ANNa")
    Xa = sca.transform(dfa)  # Scale predictors for Network A
    doca_1 = model_ANNa.predict(Xa)  # Predict DOC values
    doca = np.squeeze(target_scalera.inverse_transform(doca_1)) # Inverse transform predictions
    del dfa, Xa, doca_1  # Free up memory

    # Network B: Classes 10-17
    print("Launching ANNb")
    Xb = scb.transform(dfb)  # Scale predictors for Network B
    docb_1 = model_ANNb.predict(Xb)  # Predict DOC values
    docb = np.squeeze(target_scalerb.inverse_transform(docb_1))  # Inverse transform predictions
    del dfb, Xb, docb_1  # Free up memory

    # Calculate DOC for Classes 1using Vantrepotte's method.
    print("Launching Vantrepotte")
    a_star_est = 10**(slope * VAR_Cdom + intercept)  # Estimate a* based on log-transformed CDOM
    docc = (10**VAR_Cdom / a_star_est)  # Compute DOC for Classes 1
    
    
    # --- Reshape to 2D arrays and wrap as xarray ---
    if "y" in CDOM_d.variables and "x" in CDOM_d.variables:
        use_lat_lon = False
        y_dim = "y"
        x_dim = "x"
        y_array = CDOM_d.y
        x_array = CDOM_d.x
        lat = CDOM_d.lat
        lon = CDOM_d.lon
    else:
        y_dim = "lat"
        x_dim = "lon"
        y_array = CDOM_d.lat
        x_array =  CDOM_d.lon
        lat = None
        lon = None
        #lat = CDOM_d.lat
        #lon = CDOM_d.lon

    shape2D = (len(y_array), len(x_array))
    doca = xr.DataArray(doca.reshape(shape2D), coords=[y_array, x_array], dims=[y_dim, x_dim])
    docb = xr.DataArray(docb.reshape(shape2D), coords=[y_array, x_array], dims=[y_dim, x_dim])
    docc = xr.DataArray(docc.values.reshape(shape2D), coords=[y_array, x_array], dims=[y_dim, x_dim])

    # shape2D = (len(lat), len(lon))
    # doca = xr.DataArray(doca.reshape(shape2D), coords=[lat, lon], dims=["lat", "lon"])
    # docb = xr.DataArray(docb.reshape(shape2D), coords=[lat, lon], dims=["lat", "lon"])
    # docc = xr.DataArray(docc.values.reshape(shape2D), coords=[lat, lon], dims=["lat", "lon"])

    # Combine DOC predictions from all sources (Vantrepotte, Network A, and Network B).
    ComDOC = jointdoc(Proba, limit, doca, docb, docc)
    
    # Clean up variables to free memory.
    del file_VAR0, file_VAR1, file_VAR2, file_VAR3
    
    # --- Apply DOC quality filter ---
    ComDOC = np.where(ComDOC >= 40, ComDOC, np.nan)
    
    # --- Create flag for Class == 1 pixels ---
    class_flag = np.where(Cla.values == 1, 1, 0).reshape(shape2D)
    # flag_da = xr.DataArray(
    #     data=class_flag[None, :, :],
    #     dims=["time", "lat", "lon"],
    #     coords={"time": [date], "lat": lat, "lon": lon},
    #     name="class_1_flag"
    #     )

    # DOC = xr.DataArray(
    #     data=np.reshape(ComDOC, (1, *np.shape(MLD[list(MLD.data_vars)[0]]))),  # Reshape DOC data to match the shape of CDOM
    #     dims=["time", "lat", "lon"],  # Define dimensions: time, latitude, and longitude
    #     coords={
    #         'time': [date],  # Time coordinate for the current date
    #         'lat': CDOM_d.lat,  # Latitude coordinate from the CDOM dataset
    #         'lon': CDOM_d.lon  # Longitude coordinate from the CDOM dataset
    #         },
    #     name='doc'  # Name of the variable
    #     )

    flag_da = xr.DataArray(
        data=class_flag[None, :, :],
        dims=["time", y_dim, x_dim],
        coords={"time": [date], y_dim: y_array, x_dim: x_array},
        name="class_1_flag"
    )
    DOC = xr.DataArray(
        data=np.reshape(ComDOC, (1, *np.shape(MLD[list(MLD.data_vars)[0]]))),
        # Reshape DOC data to match the shape of CDOM
        dims=["time", y_dim, x_dim],  # Define dimensions: time, latitude, and longitude
        coords={
            'time': [date],  # Time coordinate for the current date
            y_dim: y_array,  # Latitude coordinate from the CDOM dataset
            x_dim: x_array  # Longitude coordinate from the CDOM dataset
        },
        name='doc'  # Name of the variable
    )

    if lat is not None and lon is not None:
        DOC['lat'] = ((y_dim, x_dim), lat.data)
        DOC['lon'] = ((y_dim, x_dim), lon.data)


    # --- Create Dataset with both DOC and flag ---
    DOC_ds = xr.Dataset({
        'doc': DOC,
        'class_1_flag': flag_da
        })



        # End timer
    end_time = time.time()
    
   
    #Calculate elapsed time minutes
    elapsed_time = (end_time - start_time)/60
    print("Elapsed time: ", elapsed_time) 
 
    del doca, docb, docc
          

    return DOC_ds
    











          


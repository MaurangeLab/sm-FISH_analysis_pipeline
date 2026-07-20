# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 14:31:35 2026

@author: ramis
"""
import os
import sys
import pandas as pd
import numpy as np
import tifffile as tif
from scipy.ndimage import generate_binary_structure, binary_dilation

#=================================================================================================




#Before starting, write the path to your files here
path = "/Users/name/Documents/Repertoire/"





#==================================================================================================

if "name" in path :
    print("Write the right path before starting")
    sys.exit()

files = os.listdir(path)
folder_name= files[0]
files.remove("Model")
convention_names = ["chinmo_threshold_", "composite_", "detected_", "merge_threshold_", 
                    "merge_", "shrinked_", ".xlsx"]

if os.path.isdir(path + folder_name) :
    path = path + folder_name + "/"
    stock=""
    stock2=""
    for i in os.listdir(path):
        for a in convention_names:
            if a == convention_names[len(convention_names)-1] and a not in i:
                print("Using following file : ", i)
                file_name = i[0:-4]
                break
            elif a in i :
                break
                
                
elif folder_name[-4:]==".tif" or folder_name[-4:]==".czi":
    print("You submitted an image. This program needs at least the following files :",
          "data_, -intensity-measurements.xlsx, shrinked_, merge_threshold_.",
          "You can find information about those files in the GitHub.")

#Getting the files we will use here
data = pd.read_excel(path + "data_" + file_name + ".xlsx")
csvarray = pd.read_excel(path + file_name + '-intensity-measurements.xlsx')
maskDAPI = tif.imread(path + "shrinked_" + file_name + ".tif")
maskProbe = tif.imread(path + "merge_threshold_" + file_name + ".tif")

#Checking every spot for changes
cl = -1
for _, row in data.iterrows():
    if cl<len(data):
        cl+=1
        if row["Spot_labels"]!= 0 and not pd.isna(row["Spot_labels"]) and row["Spot_labels"] in csvarray["Label"].tolist():
            data.loc[data["Spot_labels"]==row["Spot_labels"], "Spot_mean_intensity"] = csvarray["Mean"][csvarray["Label"]==row["Spot_labels"]].iloc[0]
            data.loc[data["Spot_labels"]==row["Spot_labels"], "Spot_volume"] = csvarray["Volume"][csvarray["Label"]==row["Spot_labels"]].iloc[0]

        if row["Spot_labels"]== 0 or pd.isna(row["Spot_labels"]):
            if data["Neuroblast_labels"][cl-1]==row["Neuroblast_labels"]:
                data = data.drop([cl])
                cl= cl-1
                data.loc[cl, "Spot_number/cell"] += -1
                
            elif data["Neuroblast_labels"][cl-1]!=row["Neuroblast_labels"]:
                data.loc[data["Spot_labels"]==row["Spot_labels"], "Spot_mean_intensity"] = "no_site"
                data.loc[data["Spot_labels"]==row["Spot_labels"], "Spot_volume"] = "no_site"

#Preparing a new dataframe ("Spot_numbers") which will contain representative information about the analysis
SN = [0, 1, 2]
Type_I = [0, 0, 0]
Type_II = [0, 0, 0]
Mean_intensity =[np.nan, 0, 0]
Mean_volume = [np.nan, 0, 0]
#For every line of the Dataframe obtained by analysis, we get every information :
    #Spot number per cell type, mean intensity, volume...
for _, row in data.iterrows():
        if not pd.isna(row["Spot_number/cell"]):
            Nspot = int(row["Spot_number/cell"])
        if row["Neuroblasts_Types"]=="II":
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Type_II[2] += 1
            else :
                Type_II[Nspot] += 1
        elif row["Neuroblasts_Types"]=="I":
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Type_I[2] += 1
            else :
                Type_I[Nspot] += 1
        if not row["Spot_number/cell"]==0:
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Mean_intensity[2] += row["Spot_mean_intensity"]
                Mean_volume[2] += row["Spot_volume"]
            else :
                Mean_intensity[Nspot] += row["Spot_mean_intensity"]
                Mean_volume[Nspot] += row["Spot_volume"]

#Getting the means for every condition
Mean_intensity = [np.nan, Mean_intensity[1]/(Type_I[1]+Type_II[1]), 
                  Mean_intensity[2]/((Type_I[2]+Type_II[2])*2)]

Mean_volume = [np.nan, Mean_volume[1]/(Type_I[1]+Type_II[1]), 
               Mean_volume[2]/((Type_I[2]+Type_II[2])*2)]

Type_I = [str(Type_I[0]) + " / " + str(round((Type_I[0]*100)/sum(Type_I),2))+"%", 
          str(Type_I[1]) + " / " + str(round((Type_I[1]*100)/sum(Type_I),2))+"%", 
          str(Type_I[2]) + " / " + str(round((Type_I[2]*100)/sum(Type_I),2))+"%"]

Type_II = [str(Type_II[0]) + " / " + str(round((Type_II[0]*100)/sum(Type_II),2))+"%", 
          str(Type_II[1]) + " / " + str(round((Type_II[1]*100)/sum(Type_II),2))+"%", 
          str(Type_II[2]) + " / " + str(round((Type_II[2]*100)/sum(Type_II),2))+"%"]


#Creation of the dataframe
Spot_numbers = pd.DataFrame({"Spot_number/cell": SN,
                             "Type I": Type_I,
                             "Type II": Type_II,
                             "Mean_intensities": Mean_intensity,
                             "Mean_volumes": Mean_volume})
        
# Creation of excel files to store these data as tabs
try :
    colonnes = data.columns
    data.to_excel(path + "data_" + file_name + ".xlsx",
               columns=colonnes.tolist(), index=False, engine="openpyxl")
    colonnes = Spot_numbers.columns
    Spot_numbers.to_excel(path + "Spot_numbers_" + file_name + ".xlsx",
                      columns=colonnes.tolist(), index=False, engine="openpyxl")
except PermissionError:
    print("Permission denied. Close the opened excel tab(s) from this stack and restart.")




#Creating an image that will allow us to see clearly and rapidly the results of the analysis

#First channel will simply be the segmented cells
ch1 = maskDAPI.astype(np.uint16)

#Second channel will contain green halos for each type II detected cell
ch2 = np.zeros_like(maskDAPI, dtype=np.float32)
#This allow us to create a 2D halo instead of 3D one
struct_2d = generate_binary_structure(2, 1)  
struct_3d = struct_2d[np.newaxis, :, :]

#Construction of the halos by dilating and then removing each cell to itself
for _, row in data.iterrows():
    if row["Neuroblasts_Types"]== "II":
        mask   = maskDAPI == row["Neuroblast_labels"]
        dilated = binary_dilation(mask, structure=struct_3d, iterations=15)
        halo   = dilated & ~mask 
        ch2[halo]= 7

#3rd and 4th channels will respectively be non kept spots and kept spots
#Obtaining the list of spots in the final array (kept spots)
spots = data["Spot_labels"][0:-1]
spots[spots=="no_site"]=0
kept_labels = spots.tolist()

ch3 = np.zeros_like(maskProbe, dtype=np.uint16)
ch4 = np.zeros_like(maskProbe, dtype=np.uint16)

#If a point is not in the kept ones, then he will go in the 3rd channel
for label in np.unique(maskProbe[maskProbe!=0]):
    if label == 0:
        continue
    if label in kept_labels:
        ch4[maskProbe == label] = label
    else:
        ch3[maskProbe == label] = label

#Creating the image, with dimensions like (N slices, N channels, N y pixels, N x pixels)
composite = np.stack([ch1, ch2, ch3, ch4], axis=1)

tif.imwrite(
    path + "composite_" + file_name + ".tif",
    composite,
    imagej=True,
    metadata={"axes": "ZCYX"}
)

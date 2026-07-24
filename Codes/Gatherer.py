import pandas as pd
import os
import glob
import numpy as np
import sys

#====================================================================================================
#Make sure to enter your path
path = "/Users/name/Documents/Repertoire/"

#Enter here the name you want to give to the data gathered in this group of files
group_name = "condition1"

#Enter here the name of the types considered in the group of file you want to gather information from
group1 = "type_I" #Enter the name of the first cell type 
group2 = "type_II" #Enter the name of the second cell type

#================================================================================================





if group_name=="":
    group_name = input("Enter a group name : ",)

group_name += "_global"

if "name" in path:
    print("Put your own path")
    sys.exit()
    
#Getting the names of the folder to gather information from
files = os.listdir(path)
file_name=""
files.remove("Model")

if os.path.isdir(path + group_name):
    print("Not creating a new folder for global data since one already exists")
    files.remove(group_name)
else :
    os.mkdir(path + group_name)
    
#Creating the lists that will be used
SS_I = {group1 : [], group2 : []}
SS_V = {group1 : [], group2 : []}
SD_I = {group1 : [], group2 : []}
SD_V = {group1 : [], group2 : []}
N_per_type = [[],[]]
Type_I = [None] * 3 * len(files)
Type_II = [None] * 3 * len(files)
Sample_number = [None] * 3 * len(files)
cl=0
cl2 = 1
MI = [np.nan] * len(files)
MV = [np.nan] * len(files)


#Gathering spot intensity and volume in function of their type and number in cell
#as well as proportions about spot number per cell
#It uses data_ and Spot_numbers_ excel files to get these information
for i in files: 
    data_files = glob.glob(path + i + "/" + 'data_*.xlsx') 
    spot_files = glob.glob(path + i + "/" + 'Spot_numbers_*.xlsx')
    try :
        Select_latest_file = max(data_files, key=os.path.getctime)
    except ValueError:
        print("Seems like you have a folder that does not contain the expected files.")
        print("You should move or supress it")
        print(f"===>Folder name : {i}")
        sys.exit()
    print("\n","File selected is: ",Select_latest_file,"\n")
    data  = pd.read_excel(Select_latest_file)
    stock = ""
    for a in data["Neuroblast_labels"]:
        Type = data["Neuroblasts_Types"][data["Neuroblast_labels"]==a].iloc[0]
        SN = data["Spot_number/cell"][data["Neuroblast_labels"]==a].iloc[0]
        
        try:
            if SN == 1:    
                SS_I[Type].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[0], 2))
                SS_V[Type].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[0], 2))
    
            if SN == 2 and stock != a:
                SD_I[Type].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[0], 2))
                SD_V[Type].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[0], 2))
                SD_I[Type].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[1], 2))
                SD_V[Type].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[1], 2))
        except KeyError:
            print("You might not have entered the right type : ", 
                  f"You entered {group1} and {group2} but detected type in data_ file is {Type}")
            sys.exit()
        stock = a
    for i in [group1, group2]:
        SS_I[i].append(np.nan)
        SS_V[i].append(np.nan)
        SD_I[i].append(np.nan)
        SD_V[i].append(np.nan)
    N_per_type[0].append(str(data["Neuroblasts_Types"].tolist().count(group1)) + " cells")
    N_per_type[1].append(str(data["Neuroblasts_Types"].tolist().count(group2)) + " cells")
    N_per_type[0].append("Next")
    N_per_type[1].append("Next")  
    
    Select_latest_file = max(spot_files, key=os.path.getctime)
    print("\n","File selected is: ",Select_latest_file,"\n")
    spots  = pd.read_excel(Select_latest_file)
    for a in spots["Spot_number/cell"]:
        
        try:
            string = spots[group1][spots["Spot_number/cell"]==a].iloc[0].strip()
        except KeyError:
            print("You might not have entered the right type : ", 
                  f"No column is named {group1} in Spot_numbers_ file")
        idx1 = string.find("/")
        idx2 = string.find("%")
        #print(cl, float(string[idx1 + 2:idx2]))
        Type_I[cl] = float(string[idx1 + 2:idx2])
        
        try:
            string = spots[group2][spots["Spot_number/cell"]==a].iloc[0].strip()
        except KeyError:
            print("You might not have entered the right type : ", 
                  f"No column is named {group1} in Spot_numbers_ file")
        idx1 = string.find("/")
        idx2 = string.find("%")
        Type_II[cl] = float(string[idx1 + 2:idx2])
        Sample_number[cl]= "Sample_n°" + str(int(cl2))
        cl+=len(files)
        
        if a>0:
            MI.append(float(spots["Mean_intensities"][spots["Spot_number/cell"]==a].iloc[0]))
            MV.append(spots["Mean_volumes"][spots["Spot_number/cell"]==a].iloc[0])
    cl+= -3*len(files)+1
    cl2 += 1
    

#Tab with information on every spot in the group
gathered = pd.DataFrame({group1 : pd.Series(N_per_type[0]),
                         "Isolated_spots_Intensity": pd.Series(SS_I[group1]),
                         "Isolated_spots_Volume": pd.Series(SS_V[group1]),
                         "Double_spots_Intensity": pd.Series(SD_I[group1]),
                         "Double_Spots_Volume": pd.Series(SD_V[group1]),
                         group2 : pd.Series(N_per_type[1]),
                        "ISI": pd.Series(SS_I[group2]),
                        "ISV": pd.Series(SS_V[group2]),
                        "DSI": pd.Series(SD_I[group2]),
                        "DSV": pd.Series(SD_V[group2])})


SN=[]
cl=0
for f in range(0, 3):
    for i in range(0, len(files)):
        SN.append(cl)
    cl+=1
#Tab with proportions and means from all the stacks
Global_numbers = pd.DataFrame({"Sample_number": Sample_number,
                               "Spot_number/cell": SN,
                               group1: Type_I,
                               group2: Type_II,
                               "Mean_intensities": MI,
                               "Mean_volumes": MV})


# =============================================================================
#Saving the tabs in a new folder 
try :    
    colonnes = gathered.columns
    gathered.to_excel(path + group_name + "/Global_data_" + group_name + ".xlsx",
           columns=colonnes.tolist(), index=False, engine="openpyxl")
    colonnes = Global_numbers.columns
    Global_numbers.to_excel(path + group_name + "/Global_numbers_" + group_name + ".xlsx",
           columns=colonnes.tolist(), index=False, engine="openpyxl")
    print("""Done""")
except Exception as e:
    if type(e)==PermissionError:
        print("===> Close the opened tab(s) Global_data_ and/or Global_numbers_ and restart")
    else : 
        raise e

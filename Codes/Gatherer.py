import pandas as pd
import os
import glob
import numpy as np
import sys

#===============================================================================================
#Make sure to enter your path and the name of the group you are interested in
path = "/Users/name/Documents/Repertoire/"
group_name = ""




#===============================================================================================



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
SS_I = [[],[]]
SS_V = [[],[]]
SD_I = [[],[]]
SD_V = [[],[]]
N_per_type = [[],[]]
Type_I = [None] * 3 * len(files)
Type_II = [None] * 3 * len(files)
cl=0
MI = [np.nan] * len(files)
MV = [np.nan] * len(files)

#Gathering spot intensity and volume in function of their type and number in cell
#as well as proportions about spot number per cell
#It uses data_ and Spot_numbers_ excel files to get these information
for i in files: 
    #Recognizing the data_ and Spot_numbers_ files by their prefix
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
        
        if SN == 1:    
            SS_I[len(Type)-1].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[0], 2))
            SS_V[len(Type)-1].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[0], 2))

        if SN == 2 and stock != a:
            SD_I[len(Type)-1].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[0], 2))
            SD_V[len(Type)-1].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[0], 2))
            SD_I[len(Type)-1].append(round(data["Spot_mean_intensity"][data["Neuroblast_labels"]==a].iloc[1], 2))
            SD_V[len(Type)-1].append(round(data["Spot_volume"][data["Neuroblast_labels"]==a].iloc[1], 2))
        stock = a
    for i in range(0,2):
        SS_I[i].append(np.nan)
        SS_V[i].append(np.nan)
        SD_I[i].append(np.nan)
        SD_V[i].append(np.nan)
    N_per_type[0].append(str(data["Neuroblasts_Types"].tolist().count("I")) + " cells")
    N_per_type[1].append(str(data["Neuroblasts_Types"].tolist().count("II")) + " cells")
    N_per_type[0].append("Next")
    N_per_type[1].append("Next")  
  
    Select_latest_file = max(spot_files, key=os.path.getctime)
    print("\n","File selected is: ",Select_latest_file,"\n")
    spots  = pd.read_excel(Select_latest_file)
    for a in spots["Spot_number/cell"]:
        #Getting percentages from every Spot_numbers_ files
        string = spots["Type I"][spots["Spot_number/cell"]==a].iloc[0].strip()
        idx1 = string.find("/")
        idx2 = string.find("%")
        #print(cl, float(string[idx1 + 2:idx2]))
        Type_I[cl] = float(string[idx1 + 2:idx2])
        
        string = spots["Type I"][spots["Spot_number/cell"]==a].iloc[0].strip()
        idx1 = string.find("/")
        idx2 = string.find("%")
        Type_II[cl] = float(string[idx1 + 2:idx2])
        cl+=len(files)
        if a>0:
            MI.append(float(spots["Mean_intensities"][spots["Spot_number/cell"]==a].iloc[0]))
            MV.append(spots["Mean_volumes"][spots["Spot_number/cell"]==a].iloc[0])
    cl+= -3*len(files)+1

#Tab with information on every spot in the group
gathered = pd.DataFrame({"Type_II" : pd.Series(N_per_type[1]),
                         "Isolated_spots_Intensity": pd.Series(SS_I[1]),
                         "Isolated_spots_Volume": pd.Series(SS_V[1]),
                         "Double_spots_Intensity": pd.Series(SD_I[1]),
                         "Double_Spots_Volume": pd.Series(SD_V[1]),
                         "Type_I" : pd.Series(N_per_type[0]),
                        "ISI": pd.Series(SS_I[0]),
                        "ISV": pd.Series(SS_V[0]),
                        "DSI": pd.Series(SD_I[0]),
                        "DSV": pd.Series(SD_V[0])})


SN=[]
cl=0
for f in range(0, 3):
    for i in range(0, len(files)):
        SN.append(cl)
    cl+=1
#Tab with proportions and means from all the stacks
Global_numbers = pd.DataFrame({"Spot_number/cell": SN,
                               "Type_I": Type_I,
                               "Type_II": Type_II,
                               "Mean_intensities": MI,
                               "Mean_volumes": MV})


# =============================================================================
#Saving the tabs in a new folder 
try :    
    colonnes = gathered.columns
    gathered.to_excel(path + group_name + "/Global_data_" + group_name + ".xlsx",
           columns=colonnes.tolist(), index=False, engine="openpyxl")
    colonnes = spots.columns
    spots.to_excel(path + group_name + "/Global_numbers_" + group_name + ".xlsx",
           columns=colonnes.tolist(), index=False, engine="openpyxl")
    print(""""Done""")
except Exception as e:
    if type(e)==PermissionError:
        print("===> Close the opened tab(s) Global_data_ and/or Global_numbers_ and restart")
    else : 
        raise e

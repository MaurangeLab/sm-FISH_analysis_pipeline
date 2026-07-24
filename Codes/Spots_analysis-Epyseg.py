import pandas as pd
import tifffile as tif
import numpy as np
import matplotlib.pyplot as plt
import time
import openpyxl
import sys
import statistics as stats
from scipy.ndimage import generate_binary_structure, binary_dilation
from sklearn.mixture import GaussianMixture
    
#Getting the information from main and extracting whole base image
file_name = sys.argv[1]
prot_yn = sys.argv[2]
type_channel = int(sys.argv[5])
prot_channel = int(sys.argv[3])
path = sys.argv[4]
group1 = sys.argv[6]
group2 = sys.argv[7]
marked = sys.argv[8]

#Setting the not_marked group
not_marked = group1 if group2==marked else group2
# Extracting respectively : whole 4D stack, cell segmentation image, only spot in cells image, all spots image, protein indicating type image, spot detection from AI image, measurements array
all_channels = tif.imread(path + file_name + ".tif")

maskDAPI = tif.imread(path + "shrinked_" + file_name +
                      ".tif")
                      
maskProbe = tif.imread(path + "merge_threshold_" + file_name + ".tif")

maskProbelong = tif.imread(path + "chinmo_threshold_" + file_name + "-lbl.tif")

maskDetected = tif.imread(path + "detected_" + file_name + ".tif")

csvarray = pd.read_excel(path + file_name + '-intensity-measurements.xlsx')

#Boolean mask to tell where theres a cell and where not (True/False)
mask2 = maskDAPI > 0
#Boolean mask to tell where theres a spot and where not (True/False)
mask3 = maskProbe > 0

#  Pixels that are in the cells, for probe and segmentation channel
#It will allow us to make probe and cell correspond
probe_labels = maskProbe[mask2]
dapi_labels = maskDAPI[mask2]

#Construction of a Dataframe with every pixel's probability to be a point, for each point.
#It will be useful to know which points in a cell belongs to the cell : We will obtain the mean probability of a spot to be a spot and compare it to other points from the same cell
site_proba = maskDetected[mask3]
proba_df = pd.DataFrame({"Spot_labels": maskProbelong[mask3],
                         "Proba": site_proba})

if prot_yn == "y":
    chinmoIM_labels = all_channels[:, prot_channel][mask2]
else:
    #Producing a mask of nan (Not A Number, undefined values) in case we dont have information about protein of interest
    chinmoIM_labels = np.zeros_like(maskDAPI)
    chinmoIM_labels = chinmoIM_labels.astype("float")
    chinmoIM_labels[chinmoIM_labels == 0] = np.nan
    chinmoIM_labels = chinmoIM_labels[mask2]


# Array containing only the pixels in the cells
# And there correspondances on the spots (gene of interest), protein indicating type (type), and protein of interest
list_cells = pd.DataFrame({"Dapi_labels": dapi_labels,
                           "Probe_labels": probe_labels,
                           "Gene_expression": chinmoIM_labels
                           })

# We sort the values in the array from smaller to bigger based on the values in Dapi_labels
list_cells = list_cells.sort_values(by="Dapi_labels", ascending=True)

#Creating the lists that will constitute the columns of the final arraydapi_labels = []
dapi_labels = []
asense_labels = []
probe_labels = []
chinmoIM_labels = []
Intensities = []
Volumes = []
Spot_number = []
stock = ""

#Cell and points coordinates to obtain their pixel number
coordsMerge = np.argwhere(maskProbe)
valuesMerge = maskProbe[tuple(coordsMerge.T)]
coordsTotal = np.argwhere(maskProbelong)
valuesTotal = maskProbelong[tuple(coordsTotal.T)]
coordsCells = np.argwhere(maskDAPI)
valuesCells = maskDAPI[tuple(coordsCells.T)] 

#---------------------------------------------------------------------------

#The following part of the code uses the distribution of mean asense fluorescence
#to determine cell type, with GaussianMixture which segregates the two groups
#AI helped me to build it
distrib = []
dapi_list = []

maskAsense = all_channels[:,type_channel]
for i in np.unique(maskDAPI[maskDAPI!=0]):
    distrib.append(stats.mean(maskAsense[maskDAPI==i].tolist()))
    dapi_list.append(i)

df = pd.DataFrame({"cell_label": dapi_list,
                   "asense_intensity": distrib})  

intensities = df["asense_intensity"].values.reshape(-1, 1)

gmm = GaussianMixture(n_components=2, random_state=0, n_init=10)
gmm.fit(intensities)

proba = gmm.predict_proba(intensities)

means = gmm.means_.flatten()
low_group_idx = np.argmin(means)

df[not_marked] = proba[:, low_group_idx]
proba2=np.delete(proba, low_group_idx, axis=1)
df[marked] = proba2 

#---------------------------------------------------------------------------

#substract = (maskProbelong==0).astype(np.uint8) * all_channels[:, 2]
#substract = substract.mean()


#A function that the main loop will use to determine the best points in a cell based on their volume in the cell and probability to be a point
#If more than 2 points are detected, only the top 2 will stay
def best_points(spot_parameters):
    ranking = []
    #We determine distance to ideal to rank spots
    #Bigger is the distance, lower is the ranking
    dist={}
    for k, (p1, p2) in spot_parameters.items():
        dist[k]= np.sqrt((1-p1)**2 + (1-p2)**2)
    ranking = sorted(spot_parameters, key=lambda k: dist[k])
    return ranking

# For each cell
for i in np.unique(list_cells["Dapi_labels"]):
    #Comparing probabilities to be a type I or type II according to GaussianMixture
    if df[marked][df["cell_label"]==i].iloc[0]>df[not_marked][df["cell_label"]==i].iloc[0]:
        asense_labels.append(marked)
    elif  df[marked][df["cell_label"]==i].iloc[0]<df[not_marked][df["cell_label"]==i].iloc[0]:
        asense_labels.append(not_marked)
        
    #Gathering of mean protein of interest fluorescence (or adding a nan)
    if prot_yn == "y":
        chinmoIM_labels.append(stats.mean(
            list_cells["Gene_expression"][list_cells["Dapi_labels"] == i]))
    elif prot_yn == "n":
        chinmoIM_labels.append(np.nan)
        
    spot_count = 0
    # Starting to count and select spots in the cell
    subtab = list_cells["Probe_labels"][list_cells["Dapi_labels"] == i]
    # If at least one point is detected in the cell
    if np.any(subtab):
        spot_parameters = {}
        #We retrieve the percentages of in cell volumes and the average probabilities that they are points
        for p in np.unique(subtab[subtab!=0]):
            #p = 343
            n_stacks_merge = len(coordsMerge[valuesMerge == p][:, 0])
            n_stacks_total = len(coordsTotal[valuesTotal == p][:, 0])
            #n_stacks_merge / n_stacks_total corresponds to the porportion of the number of voxels 
            #that are into the parent cell, and is calculated for every spot
            if (n_stacks_merge / n_stacks_total) > 0.5:
                #If more than 50% of the spot volume is in the cell, we add the precedent 
                #information as well as mean probability of every voxel constituting the spot
                spot_parameters[p]= [round((n_stacks_merge / n_stacks_total), 2), round(stats.mean(proba_df["Proba"][proba_df["Spot_labels"]==p]),2)]
        
        if np.any(spot_parameters):
            #We rank the point according to their parameters described before
            #We keep them according to their ranking
            ranking = best_points(spot_parameters)
            
            if len(ranking)==1:
                dapi_labels.append(i)
                probe_labels.append(ranking[0])
                # We get the intensity
                serMean = csvarray["Mean"][csvarray["Label"] == ranking[0]]
                Intensities.append(round((serMean.iloc[0]),2))
                #We get the volume
                serVol = csvarray["Volume"][csvarray["Label"] == ranking[0]]
                Volumes.append(serVol.iloc[0])
                spot_count += 1
            
            #If there is more than 1 point we keep the best two
            if len(ranking)>1 :
                dapi_labels += 2 * [i]
                asense_labels.append("")
                chinmoIM_labels.append("")
                probe_labels += ranking[0:2]
                for a in ranking[0:2]:
                    # We get the intensity
                    serMean = csvarray["Mean"][csvarray["Label"] == a]
                    Intensities.append(round((serMean.iloc[0]),2))
                    #We get the volume
                    serVol = csvarray["Volume"][csvarray["Label"] == a]
                    Volumes.append(serVol.iloc[0])
                    spot_count += 1
        
        #Supressing the points that did not rank high enough
        elif not np.any(spot_parameters):
            for b in np.unique(subtab):
                if b > 0:
                    calc = (list_cells["Dapi_labels"] == i) & (list_cells["Probe_labels"] == b)
                    list_cells.loc[calc, "Probe_labels"] = 0
                    
    # If at last not relevant points are detected in the cell
    if not np.any(np.unique(list_cells["Probe_labels"][list_cells["Dapi_labels"] == i])):
        dapi_labels.append(i)
        probe_labels.append(0)
        Intensities.append("no_site")
        Volumes.append("no_site")

    # We add the number of spots attributed to the cell
    Spot_number.append(int(spot_count))
    Spot_number += (spot_count-1)*[""]

#We establish the final array putting data in relation
cores = pd.DataFrame({"Neuroblast_labels": dapi_labels,
                      "Neuroblasts_Types": asense_labels,
                      "Spot_labels": probe_labels,
                      "Spot_mean_intensity": Intensities,
                      "Spot_volume": Volumes,
                      "Spot_number/cell": Spot_number,
                      "Gene_expression": chinmoIM_labels
                      })

#Preparing a new dataframe ("Spot_numbers") which will contain representative information about the analysis

SN = [0, 1, 2]
Type_I = [0, 0, 0]
Type_II = [0, 0, 0]
Mean_intensity =[np.nan, 0, 0]
Mean_volume = [np.nan, 0, 0]
#For every line of the Dataframe obtained by analysis, we get every information :
    #Spot number per cell type, mean intensity, volume...
for _, row in cores.iterrows():
        if row["Neuroblasts_Types"]==group2:
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Type_II[2] += 1
            else :
                Type_II[row["Spot_number/cell"]] += 1
        elif row["Neuroblasts_Types"]==group1:
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Type_I[2] += 1
            else :
                Type_I[row["Spot_number/cell"]] += 1
        if not row["Spot_number/cell"]==0:
            if pd.isna(row["Spot_number/cell"]) or row["Spot_number/cell"]=="":
                Mean_intensity[2] += row["Spot_mean_intensity"]
                Mean_volume[2] += row["Spot_volume"]
            else :
                Mean_intensity[row["Spot_number/cell"]] += row["Spot_mean_intensity"]
                Mean_volume[row["Spot_number/cell"]] += row["Spot_volume"]

#Getting the intensity, volume and spot number means for every condition
try :
    Mean_intensity = [np.nan, Mean_intensity[1]/(Type_I[1]+Type_II[1])] + ([Mean_intensity[2]/((Type_I[2]+Type_II[2])*2)] if 2 in cores["Spot_number/cell"].tolist() else [0])
    
    Mean_volume = [np.nan, Mean_volume[1]/(Type_I[1]+Type_II[1])] + ([Mean_volume[2]/((Type_I[2]+Type_II[2])*2)] if 2 in cores["Spot_number/cell"].tolist() else [0])
except ZeroDivisionError:
    Mean_intensity = [np.nan, 0, 0]
    Mean_volume = [np.nan, 0, 0]
    
Type_I = [str(Type_I[0]) + " / " + str(round((Type_I[0]*100)/sum(Type_I),2))+"%", 
          str(Type_I[1]) + " / " + str(round((Type_I[1]*100)/sum(Type_I),2))+"%"] + ([str(Type_I[2]) + " / " + str(round((Type_I[2]*100)/sum(Type_I),2))+"%"] if 2 in cores["Spot_number/cell"].tolist() else [0])

Type_II = [str(Type_II[0]) + " / " + str(round((Type_II[0]*100)/sum(Type_II),2))+"%", 
          str(Type_II[1]) + " / " + str(round((Type_II[1]*100)/sum(Type_II),2))+"%"] + ([str(Type_II[2]) + " / " + str(round((Type_II[2]*100)/sum(Type_II),2))+"%"] if 2 in cores["Spot_number/cell"].tolist() else [0])

#Creation of the dataframe
Spot_numbers = pd.DataFrame({"Spot_number/cell": SN,
                             group1: Type_I,
                             group2: Type_II,
                             "Mean_intensities": Mean_intensity,
                             "Mean_volumes": Mean_volume})

# Creation of excel files to store these data as tabs
colonnes = cores.columns
cores.to_excel(path + "data_" + file_name + ".xlsx",
           columns=colonnes.tolist(), index=False, engine="openpyxl")
colonnes = Spot_numbers.columns
Spot_numbers.to_excel(path + "Spot_numbers_" + file_name + ".xlsx",
                  columns=colonnes.tolist(), index=False, engine="openpyxl")

#Creating an image that will allow us to see clearly and rapidly the results of the analysis

#First channel will simply be the segmented cells
ch1 = maskDAPI.astype(np.uint16)

#Second channel will contain green halos for each type II detected cell
ch2 = np.zeros_like(maskDAPI, dtype=np.float32)
#This allow us to create a 2D halo instead of 3D one
struct_2d = generate_binary_structure(2, 1)  
struct_3d = struct_2d[np.newaxis, :, :]

#Construction of the halos by dilating and then removing each cell to itself
for _, row in cores.iterrows():
    if row["Neuroblasts_Types"]== group2:
        mask   = maskDAPI == row["Neuroblast_labels"]
        dilated = binary_dilation(mask, structure=struct_3d, iterations=15)
        halo   = dilated & ~mask 
        ch2[halo]= df[group2][df["cell_label"]==row["Neuroblast_labels"]].iloc[0]


#3rd and 4th channels will respectively be non kept spots and kept spots
#Obtaining the list of spots in the final array (kept spots)
spots = cores["Spot_labels"][0:-1]
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


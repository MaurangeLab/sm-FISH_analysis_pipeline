import os
from czifile import CziFile
from aicspylibczi import CziFile as aics
import subprocess
import time
import tifffile as tif
import numpy as np
import sys
from scipy import ndimage
import pandas as pd
import statistics as stats
from sklearn.mixture import GaussianMixture
import matplotlib.pyplot as plt
import imageio.v3 as iio
import traceback
import shutil
import warnings

warnings.simplefilter('ignore')

env = os.environ.copy()
env.pop("MPLBACKEND", None)

#---------------------------------------------------------------------------------------------------------------------------
#Indicate your parameters here
path = "/Users/name/Documents/Repertoire/"
seg_model_name = "Miranda2" #Enter the name of your segmentation model, contained in Model folder in Repertoire
#Don't forget the extension (if there is one)
spot_model_name = "linknet-vgg16-sigmoid-0.h5" #Enter the name of your spot detection model
#contained in Model folder in Repertoire
#Don't forget the extension (if there is one)

group1 = "type_I" #Enter the name of your first cell type ("neuron", "stem_cell", "type_I"...)
group2 = "type_II" #Enter the name of your second cell type (of interest)
marked = "type_I" #Enter the name of the group marked by immunofluorescence
segmentation_channel = 0 #Segmentation channel
smFISH_channel = 1 #sm-FISH channel
type_channel = 2 #Channel used to determine cell type
prot_channel = 3 #Channel for protein of interest / channel you don't need to analyse
prot_yn = "n" # "y" if you want to quantify protein of interest, "n" if you dont 
#if you don't, nothing will be made out of the "chinmoprot_channel" channel

#-------------------------------------------------------------------------------------------------------


if "name" in path :
    print("Write the right path before starting")
    sys.exit()

#setting base directory, files to analyse, convention_names
not_marked = group1 if group1==marked else group2
path_out = path
turns_count = 0
files = os.listdir(path)
file_name=""
files.remove("Model")
errors = []
convention_names = ["masks", "chinmo_threshold_", "composite_", "detected_", "merge_threshold_", 
                    "merge_", "shrinked_", ".xlsx", ".csv"]

while True : 
    #Resetting path for every new image to analyse
    path = path_out
    
    #We use try so that if there's an error during the analysis and there's more images 
    #to analyse after, the program won't stop just because of the error
    #It will just quit analysing this file and get to the following one
    try :
        #Default parameters are segmentation and detection activated
        seg = "y"
        detect = "y"
        print("\n")
        
        #Identifying the type of file that the code will be working on
        if os.path.isdir(path + files[turns_count]) :
            file_type= "Folder"
            #As it's a folder, it means that the user could want to analyse again previously 
            #analysed stack
            #It means that we need to identify the base tiff file and start analysing with its name
            path = path + files[turns_count] + "/"
            stock=""
            stock2=""
            for i in os.listdir(path):
                for a in convention_names:
                    if a == convention_names[len(convention_names)-1] and a not in i:
                        if i[-4:]==".tif":
                            print("Using following file : ", i)
                            file_name = i[0:-4]
                            break
                        elif i[-4:]==".czi":
                            print(f"The found raw file in the {files[turns_count]} folder is a czi.",
                                  "Duplicate it and replace the czi image by the resulting tif image")
                        else :
                            print(f"Found a raw file ({i}) which hasn't been recognized")
                    elif a in i :
                        #If the segmentation and detection files already exist, we wont do it again
                        if a == "shrinked_":
                            seg="n"
                        if a == "detected_":
                            detect = "n"
                        break
            
            
            
        elif str(files[turns_count])[-4:]==".tif":
            file_type= "Tiff"
            file_name = files[turns_count][0:-4]
            
            #As image is a tiff, we will put it in a new folder to analyse it
            path = path_out + file_name + "/"
            os.mkdir(path)
            print("Using following file : ", files[turns_count])
            shutil.move(path_out + file_name + ".tif", path + "/" + file_name + ".tif")
            
            
            
        elif str(files[turns_count])[-4:]==".czi":
            file_type= "Czi"
            file_name = files[turns_count][0:-4]
            
            #Obtaining czi image pixel sizes
            img = aics(path_out + files[turns_count])
            metadata = img.meta 
            scaling_x = float(metadata.find(".//ScalingX").text) * 1e6  # m → µm conversion
            scaling_y = float(metadata.find(".//ScalingY").text) * 1e6
            scaling_z = float(metadata.find(".//ScalingZ").text) * 1e6
            #Duplicating the czi file to a tif file in a new folder, that will contain
            #analysis results, and injecting pixel size and depth into metadata
            img = CziFile(path + files[turns_count])
            img = img.asarray()
            img = np.squeeze(img)
            img = np.transpose(img, (1, 0, 2, 3))
            path = path + files[turns_count][0:-4] + "/"
            os.mkdir(path)
            print("Using following file : ", files[turns_count])
            tif.imwrite(path + files[turns_count][0:-4] + ".tif", img,
                        imagej=True,
                        resolution = (1/scaling_x, 1/scaling_y),
                        metadata={
            'axes': 'ZCYX',
            'spacing': scaling_z,
            'unit': 'um',
        })
            
        
        if seg == "y":
            print("Segmentation")
            #Segmentation script lauching. It needs special environnement called "segment" to work. Descriptions of the necessary environments are in the README.
            result_seg = subprocess.run(
                 f'conda run -n segment python segmentation_cellpose-Epyseg.py "{file_name}" "{seg}" "{path}" "{path_out}" "{segmentation_channel}" "{seg_model_name}"',
                 shell=True,
                 env=env,
                 capture_output=True,
                 text=True)
            
            if result_seg.stderr=="":
                print("Done")
            
        if detect=="y":
            print("Spots detection")
            #Spot Detection script lauching. It needs "chinmospots" environment.
            result_detect = subprocess.run(
                f'conda run -n chinmospots python spot_segmentation.py "{file_name}" "{path}"  "{path_out}" "{smFISH_channel}" "{spot_model_name}"',
                shell=True,
                env=env,
                capture_output=True,
                text=True
                )
            if result_detect.stderr=="":
                print("Done")
        
        if seg == "y":
            if "MemoryError" in result_seg.stderr :
                print("Not enough memory available for segmentation")
                raise MemoryError
            elif result_seg.stderr!="":
                print("Error during segmentation : ")
                print(f"""
                      {traceback.format_exc()}
                      """)
        if detect == "y":
            if "MemoryError" in result_detect.stderr :
                print("Not enough memory available for detection")
                raise MemoryError
            elif "IOError" in result_detect.stderr :
                print("Please enter the right spot detection model name.")
            elif "tensorflow" and "WARNING" in result_detect.stderr:
                #Passing an unuseful warning
                pass
            elif result_detect.stderr!="":
                print("Error during detection : ")
                print(f"""
                      {traceback.format_exc()}
                      """)
        
        print("Creating new images for analysis")
        #We charge the files produced earlier : AI detected spots, segmented cells and full image
        detected = tif.imread(path + "detected_" + file_name + ".tif")
        miranda = tif.imread(path + "shrinked_" + file_name + ".tif")
        all_channels = tif.imread(path + file_name + ".tif")
        
        #This will produce a file that will allow you to see clearly what points have been detected in the cells
        #You may have to use imagej adjust BC to see clearly the cell shapes
        miranda = miranda > 0
        miranda = miranda.astype(np.uint(16)) 
        merge = detected * miranda                  
        
        #Squaring every non significant value (<0.01) to artificially increase them and see clearly the cell shapes
        merge = np.where(merge<=0.01, np.sqrt(merge),merge)
        merge = merge.astype(np.float32)
        tif.imwrite(path + "merge_" + file_name + ".tif", merge)
        
        #Thresholding of points with high probability to be points (here, 0.5 means we keep only points with more than 50% chance to be points, according to the detection file)
        binary = detected>0.5
        #Thresholded image is made binary, so that we can perform connected component analysis.
        binary = binary.astype(np.uint16) * 255
        
        #connected component analysis returns "labeled" (same array as binary but every point has a specific color)
        labeled, num_features = ndimage.label(binary)
        tif.imwrite(path + "chinmo_threshold_" + file_name + "-lbl.tif", labeled)
        
        #producing a file with only points in cells
        merge_threshold = labeled * miranda
        tif.imwrite(path + "merge_threshold_" + file_name + ".tif", merge_threshold)
        
        #substract = ((labeled==0).astype(np.uint8)) * all_channels[:, 2]
        #print(stats.mean(substract.ravel().tolist()))
        #raise MemoryError
        
        print("Gathering information on every point")
        try :
            #calculating centers of mass of every point, could be useful later
            #often brings irrelevant errors
            centers = ndimage.center_of_mass(all_channels[:,smFISH_channel], labeled, range(1, num_features + 1))
        except :
            pass 
        
    #---------------------------------------------------------------------------------------------
        #This part of the code will gather following information on every point :
        # Label (color), Mean, max and min intensity, Number of Voxels, Volume (um3), and centers of mass
        # It will then save it as a .xlsx file to lend it to the final subprocess (spots_analysis)
        
        properties = iio.improps(path + file_name + ".tif", extension=".tif")
        metadata = iio.immeta(path + file_name + ".tif")
        size_of_a_pixel = 1/properties.spacing[0]
        if "spacing" in metadata.keys() :
            depth_of_a_pixel = metadata["spacing"]
        else :
            depth_of_a_pixel=0.44
            print("Pixel depth was not found, using 0.44um as default value")
        #metadata.pop("spacing")
        Label = []
        Mean = []
        Max = []
        Min = []
        NOV = []
        Volume = []
        CoM_X = []
        CoM_Y = []
        CoM_Z = []
        
        if len(np.unique(merge_threshold[merge_threshold!=0]))==0:
            print("No point has been detected inside a cell")
            raise ValueError 
        
        for i in np.unique(merge_threshold[merge_threshold!=0]):
            pixels = all_channels[:,smFISH_channel][merge_threshold==i].tolist()
            Label.append(i)
            Mean.append(stats.mean(pixels))
            Max.append(max(pixels))
            Min.append(min(pixels))
            NOV.append(len(pixels))
            Volume.append(round(len(pixels)*((size_of_a_pixel**2)*depth_of_a_pixel),3))
            CoM_X.append(centers[int(i-1)][2])
            CoM_Y.append(centers[int(i-1)][1])
            CoM_Z.append(centers[int(i-1)][0])
            
        IM = pd.DataFrame({"Label": Label,
                           "Mean": Mean,
                           "Max": Max,
                           "Min": Min,
                           "NumberOfVoxels": NOV,
                           "Volume": Volume,
                           "CenterOfMass.X": CoM_X,
                           "CenterOfMass.Y": CoM_Y,
                           "CenterOfMass.Z": CoM_Z})
        colonnes = IM.columns
        IM.to_excel(path + file_name + "-intensity-measurements.xlsx",
                          columns=colonnes.tolist(), index=False, engine="openpyxl")
        
    #------------------------------------------------------------------------------------------------------------------------------------------------------------
        #This part of the code is meant to estimate the reliability of type attribution
        #It will get the distribution of asense intensity and separate it as two gaussians
        #The first gaussian (low intensity) contains the type II and the second (high intensity) the type I 
        #It will then do the same thing 20 times with a different seed
        #And print a percentage of how many times the result was the same, estimating reliability
        #It also shows the distribution with indication of the means of the two gaussians for the user to see the result
     #--------------------------------------------------------------------------------------------------------------------------------------------------------
     
        print("Estimating types repartition")
        time.sleep(4)
        maskDAPI = tif.imread(path + "shrinked_" + file_name + ".tif")
        coordsCells = np.argwhere(maskDAPI)
        valuesCells = maskDAPI[tuple(coordsCells.T)]
        
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
        
        results = []
        for seed in range(200):
            gmm = GaussianMixture(n_components=2, random_state=seed, n_init=10)
            gmm.fit(intensities)
            results.append(gmm.predict(intensities))
        
        agreement = np.mean([np.array_equal(results[0], r) or np.array_equal(results[0], 1 - r) for r in results[1:]])
        
        proba = gmm.predict_proba(intensities)
        
        means = gmm.means_.flatten()
        low_group_idx = np.argmin(means)
        
        df[not_marked] = proba[:, low_group_idx]
        proba2=np.delete(proba, low_group_idx, axis=1)
        df[marked] = proba2
        
        plt.hist(distrib, bins=round(len(distrib)/2))
        plt.title(file_name)
        plt.axvline(means[means.tolist().index(max(means))], color='red', linestyle='--', linewidth=2)
        plt.axvline(means[means.tolist().index(min(means))], color='yellow', linestyle='--', linewidth=2)
        plt.show()
        
        print(f"Gaussian recognition stability : {agreement*100:.0f}%")
       
        result = subprocess.run(
            f'conda run -n spots_analysis python -u Spots_analysis-Epyseg.py "{file_name}" "{prot_yn}" "{prot_channel}" "{path}" "{type_channel}" {group1} {group2} {marked}',
            shell=True,
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stderr)
        
        if "MemoryError" in result.stderr :
            print("Not enough memory for analysis")
            raise MemoryError
        if "PermissionError" in result.stderr :
            print("Permission denied. Close the opened excel tab(s) from this stack and restart for this folder")
        elif result.stderr!="":
            print("Error during analysis", file_name)
            print(result.stderr)
            
    except Exception as e :
        #If there's an error, we dont want the program to stop running so that it keeps
        #analysing the other files
        #so we ignore the error but print it
        print(f"""
              {traceback.format_exc()}
              """)
        print(f"{type(e)}")
        if type(e)==MemoryError:
            print("Error is : Not enough memory available")
        
    
    finally:
        turns_count+=1
        if turns_count<len(files):
            print(str(turns_count) + "/" + str(len(files)) + " finished")
            continue
        elif turns_count==len(files):
            print("Done")
            break
            
import winsound
winsound.Beep(700, 500) 
winsound.Beep(700, 500) 

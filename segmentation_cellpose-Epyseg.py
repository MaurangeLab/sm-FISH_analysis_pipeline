import sys
import os
from cellpose import models
import tifffile as tif
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy.ndimage import distance_transform_edt

#Getting the information from main
path = sys.argv[3]
path_out = sys.argv[4]
file_name = sys.argv[1]
seg = sys.argv[2]
miranda_channel = int(sys.argv[5])

f = path + file_name + ".tif"
#Getting the whole image, then isolating the channel to segment (Default is 1)
all_channels = tif.imread(f)
image = all_channels[:,miranda_channel]

#You must have a pretrained model saved in the Model folder of your reference folder to use this
model = models.CellposeModel(gpu=False, pretrained_model=
                    path_out + "Model/Miranda2")
                    
masks_all=[]
flows_all=[]
end_z=len(image[:])

print("Producing the masks")
masks, flows, styles = model.eval(image, do_3D=False, stitch_threshold=0.5, z_axis=0)
tif.imwrite(path + 'masks_' + file_name + ".tif", masks)
            
print("Done")
            
#This will shrink the cells by 15% of their volume so that points that are nearby but that dont belong to the cells are not detected
print("Shrinking the cells")

result = np.zeros_like(masks)
labels = np.unique(masks)
labels = labels[labels != 0]
shrink_factor= 0.15

for label in labels:
    cell = (masks == label)
    shrunk = np.zeros_like(masks)
    cl1=0
    for slice_ in cell :
        if np.any(slice_):
            # distance pixel in cell-pixel of the background
            dist = distance_transform_edt(slice_)
            
            max_dist = dist.max()
            
            #thresholding
            threshold = max_dist * shrink_factor
            
            shrunk = dist > threshold
            
            result[cl1][shrunk] = label
        cl1+=1
name = path + "shrinked_" + file_name + ".tif"
tif.imwrite(name, result)
            
print("Keeping only consistant neuroblasts")
#This will get most false positive (INPs) out
masks = tif.imread(path + "shrinked_" + file_name + ".tif")
coords = np.argwhere(masks)
values= masks[tuple(coords.T)]
drops = []
masks_clean = masks.copy()
for i in np.unique(values):
    n_pixels_cell = len(coords[values==i][:, 0])
    #Sorting the cell based in their pixel number
    if n_pixels_cell < 30000 :
        drops.append(i)
        
cl=0
labels = np.unique(masks_clean)
for i in labels :
    if i in drops :
        masks_clean[masks_clean==i]=0
    elif i not in drops :
        masks_clean[masks_clean==i]=cl
        cl+=1
        
name = path + "shrinked_" + file_name + ".tif"
tif.imwrite(name, masks_clean)

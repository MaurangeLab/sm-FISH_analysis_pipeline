import sys, os, ast, time
import tifffile as tif
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tif_meta
import numpy as np
from scipy.ndimage import distance_transform_edt


#Getting the information from main
path = sys.argv[2]
file_name = sys.argv[1]
seg = ast.literal_eval(sys.argv[3])
seg_info = ast.literal_eval(sys.argv[4])

#path = 'C:/Users/ramis/Documents/Repertoire/tumors_E-L3_cd8GFP_40X__lame3-2_13-07/'
#file_name = 'tumors_E-L3_cd8GFP_40X__lame3-2_13-07'
#seg = ast.literal_eval("{'0': 'y'}")
#seg_info = ast.literal_eval("{'model_path': 'C:/Users/ramis/Documents/Repertoire/Model/Miranda2','cells_name': 'Neuroblasts', 'shrink_factor': '', 'min_size': '','channel': 0}")

miranda_channel = int(seg_info["channel"])
model_path = seg_info["model_path"]
model_version = int(float(str(seg_info.get("model_version", 2))))      # Cellpose version of the model: 2, 3 or 4


f = path + file_name + ".tif"
#Getting the whole image, then isolating the channel to segment
all_channels = tif.imread(f)
image = all_channels[:,miranda_channel]



#==================================================================================================
#Model calling and segmentation part

#You must have a pretrained model saved in the Model folder of your reference folder to use this


def use_gpu():
    """GPU when PyTorch sees one (Cellpose 2 / 3 / 4 all run on PyTorch)."""
    try:
        import torch
        return bool(torch.cuda.is_available() or
                    (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()))
    except Exception:
        return False


def segment_v2(image, model_path):
    from cellpose import models
    model = models.CellposeModel(gpu=use_gpu(), pretrained_model=model_path)
    return model.eval(image, do_3D=False, stitch_threshold=0.5, z_axis=0)[0]


def segment_v3(image, model_path):
    from cellpose import models
    # same interface as version 2 (models trained with Cellpose 3 or fine-tuned from its models)
    model = models.CellposeModel(gpu=use_gpu(), pretrained_model=model_path)
    return model.eval(image, do_3D=False, stitch_threshold=0.5, z_axis=0)[0]


def segment_v4(image, model_path):
    from cellpose import models
    # Cellpose 4 (Cellpose-SAM): no channel arguments any more; the image is given as (Z, Y, X)
    model = models.CellposeModel(gpu=use_gpu(), pretrained_model=model_path)
    return model.eval(image, do_3D=False, stitch_threshold=0.5, z_axis=0)[0]


SEGMENT = {2: segment_v2, 3: segment_v3, 4: segment_v4}


if seg[str(miranda_channel)] =="y":
    print("Producing the masks")
    try:
        import cellpose
        installed = getattr(cellpose, "version", None)
        print(f"Cellpose version of the environment: {installed if installed else 'unknown'}; "
              f"model declared as Cellpose {model_version}; GPU: {use_gpu()}")
    except Exception:
        pass
    if model_version not in SEGMENT:
        raise ValueError(f"Unsupported Cellpose version {model_version} (2, 3 or 4)")
    masks = SEGMENT[model_version](image, model_path)
    tif_meta.write_like(path + 'masks' + str(miranda_channel) + '_' + file_name + ".tif", masks, path + file_name + '.tif', axes='ZYX')
                
    print("Done")
elif seg[str(miranda_channel)] == "n":
    masks = tif.imread(path + 'masks' + str(miranda_channel) + '_' + file_name + ".tif")
#=================================================================================================


         
#This will shrink the cells by 15% of their volume so that points that are nearby but that dont belong to the cells are not detected
print("Shrinking the cells")

result = np.zeros_like(masks)
labels = np.unique(masks)
labels = labels[labels != 0]

#====> Modify this to change the kept area percentage (0.15 = 85% of cell area is kept)

# empty or 0 = no shrinking
shrink_factor = 0.0 if str(seg_info["shrink_factor"]).strip()=="" else float(str(seg_info["shrink_factor"]).replace(",", "."))

if shrink_factor > 0:    
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
    name = path + "shrinked" + str(miranda_channel) + "_" + file_name + ".tif"
    tif_meta.write_like(name, result, path + file_name + '.tif', axes='ZYX')
elif shrink_factor == 0 :
    name = path + "shrinked" + str(miranda_channel) + "_" + file_name + ".tif"
    tif_meta.write_like(name, masks, path + file_name + '.tif', axes='ZYX')

      
print("Keeping only consistant neuroblasts")
#This will get most false positive (INPs) out

# minimum size of a cell in voxels (all planes together); empty or 0 = no minimum
min_size = 0 if str(seg_info["min_size"]).strip()=="" else int(float(str(seg_info["min_size"]).replace(",", ".")))

if min_size > 0 :
    masks = tif.imread(path + "shrinked" + str(miranda_channel) + "_" + file_name + ".tif")
    coords = np.argwhere(masks)
    values= masks[tuple(coords.T)]
    drops = []
    masks_clean = masks.copy()
    for i in np.unique(values):
        n_pixels_cell = len(coords[values==i][:, 0])
        #Sorting the cell based in their pixel number
        if n_pixels_cell < min_size :
            drops.append(i)
            
    cl=0
    labels = np.unique(masks_clean)
    for i in labels :
        if i in drops :
            masks_clean[masks_clean==i]=0
        elif i not in drops :
            masks_clean[masks_clean==i]=cl
            cl+=1
            
    name = path + "shrinked" + str(miranda_channel) + "_" + file_name + ".tif"
    tif_meta.write_like(name, masks_clean, path + file_name + '.tif', axes='ZYX')

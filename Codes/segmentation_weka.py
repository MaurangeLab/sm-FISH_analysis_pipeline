"""
segmentation_weka.py  <file_name> <path> <cells|objects> <info dict>
Applies a Weka (Trainable Weka Segmentation) classifier with Fiji, without interface, then builds:
  - cells:   masks<channel>_<file>.tif   (3D connected components of the chosen class, one label per cell);
             Newmain then runs the usual shrinking / minimum size step on it
  - objects: detected<channel>_<file>.tif  (probability of the chosen class, as the other detectors write it)
info: channel, model_path, weka_mode ('2d' = plane by plane, '3d'), weka_class (1 = first class of the classifier),
fiji_path.
"""
import ast
import os
import shutil
import sys
import tempfile

import numpy as np
import tifffile as tif
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiji_tools
import tif_meta

file_name, path, kind = sys.argv[1], sys.argv[2], sys.argv[3]
info = ast.literal_eval(sys.argv[4])
channel = int(info["channel"])
mode = "3d" if str(info.get("weka_mode", "2d")).lower() == "3d" else "2d"
wanted = max(int(float(str(info.get("weka_class", 1)))), 1) - 1          # 0-based class index

exe = fiji_tools.find_executable(info.get("fiji_path"))
if exe is None or not fiji_tools.has_weka(exe):
    ok, msg = fiji_tools.check(info.get("fiji_path"))
    raise RuntimeError("Weka segmentation needs Fiji with the Trainable Segmentation plugin. " + msg)

stack = tif.imread(path + file_name + ".tif")
if stack.ndim != 4:
    raise ValueError(f"Expected a (Z, C, Y, X) image, got {stack.shape}")
img = stack[:, channel]
nz = img.shape[0]

work = tempfile.mkdtemp(prefix="weka_")
try:
    in_path, out_path = os.path.join(work, "in.tif"), os.path.join(work, "out.tif")
    tif.imwrite(in_path, img, imagej=True, metadata={"axes": "ZYX"})
    print(f"Weka segmentation ({mode}) of channel {channel} with {os.path.basename(info['model_path'])}")
    fiji_tools.run_weka(exe, work, in_path, out_path, info["model_path"], mode)
    prob = tif.imread(out_path).astype(np.float32)
finally:
    shutil.rmtree(work, ignore_errors=True)

if prob.ndim == 2:
    prob = prob[None]
if prob.shape[0] % nz != 0:
    raise RuntimeError(f"Unexpected Weka output: {prob.shape[0]} slices for {nz} planes.")
n_classes = prob.shape[0] // nz
if wanted >= n_classes:
    raise ValueError(f"The classifier has {n_classes} classes; class {wanted + 1} was asked.")
prob = prob.reshape(nz, n_classes, *prob.shape[1:])[:, wanted]
print(f"Classifier with {n_classes} classes; class {wanted + 1} used.")

if kind == "cells":
    labels, n = ndimage.label(prob > 0.5)            # 6-connectivity: planes are linked where the objects overlap
    print(f"{n} cells found")
    tif_meta.write_like(f"{path}masks{channel}_{file_name}.tif", labels, path + file_name + ".tif", axes="ZYX")
else:
    tif_meta.write_like(f"{path}detected{channel}_{file_name}.tif", prob, path + file_name + ".tif", axes="ZYX")
print("Done")

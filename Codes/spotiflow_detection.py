"""
Spotiflow detection of the points of one channel (child script of Newmain.py, run in the 'spotiflow' environment).

Arguments (same as spot_segmentation.py): file_name, path, list of the Objects entries (as text), number of the entry.
Reads  <path><file_name>.tif  (Z, C, Y, X), takes the channel of the entry and writes
       <path>spotiflow_results/<file_name>_c<channel>.csv   with the columns  z, y, x, prob, intens
       <path>spotiflow_results/<file_name>_c<channel>.csv.json   (model and threshold used: nothing is computed
       again by Newmain when they are unchanged).

Entry keys used: channel, model_path (a Spotiflow model folder, or the name of a pretrained model such as
'smfish_3d'), spotiflow_prob_thresh (empty = the optimal threshold of the model).
Coordinates are in pixels, sub-pixel, as returned by Spotiflow. prob = probability that the point is a true spot,
intens = value of the voxel of the image at the point (informative only).
"""
import sys, os, ast, json
import numpy as np
import pandas as pd
import tifffile as tif
from spotiflow.model import Spotiflow

if len(sys.argv)>1:
    file_name, path, probes, number = sys.argv[1:5]
    entry = ast.literal_eval(probes)[int(number)]
    print(file_name, path, probes, number)
else : 
    file_name = "snr1RNAi_L-L3_Mir_chinmo_Lame1-2"
    path = "C:/Users/ramis/Documents/snr1RNAi_L-L3_Mir_chinmo_Lame1-2/"
    probes = [{'model_source': 'Spotiflow', 'detection': 'Spotiflow', 'model_path': 'smfish_3d', 'objects_name': 'Spots', 'smfish_type': 'exonic probe', 'spotiflow_prob_thresh': '', 'aperture_sigmas': '3', 'get_means': 'False', 'channel': 1}]
    number = 0
    entry = probes[int(number)]
channel = int(entry["channel"])
model_ref = str(entry.get("model_path", "")).strip()
threshold = str(entry.get("spotiflow_prob_thresh", "")).strip().replace(",", ".")

image = tif.imread(path + file_name + ".tif")
if image.ndim != 4:
    raise ValueError(f"Expected a (Z, C, Y, X) image, got shape {image.shape}")
stack = image[:, channel]                                   # (Z, Y, X)

if os.path.isdir(model_ref):
    print(f"Loading the Spotiflow model {os.path.basename(os.path.normpath(model_ref))}")
    model = Spotiflow.from_folder(model_ref)
else:
    print(f"Loading the pretrained Spotiflow model '{model_ref}'")
    model = Spotiflow.from_pretrained(model_ref)

options = {}
if threshold:
    options["prob_thresh"] = float(threshold)

is_3d = getattr(getattr(model, "config", None), "is_3d", stack.shape[0] > 1)
print(f"Predicting on {stack.shape} ({'3D' if is_3d else '2D'} model)")
if is_3d:
    points, details = model.predict(stack, **options)
    points = np.asarray(points, float).reshape(-1, 3)
    prob = np.asarray(getattr(details, "prob", np.full(len(points), np.nan)), float)
    intens = np.asarray(getattr(details, "intens", np.full(len(points), np.nan)), float)
else:                                                       # 2D model: plane by plane
    rows, prob_list, intens_list = [], [], []
    for z, plane in enumerate(stack):
        pts, det = model.predict(plane, **options)
        pts = np.asarray(pts, float).reshape(-1, 2)
        rows.append(np.column_stack([np.full(len(pts), z, float), pts]))
        prob_list.append(np.asarray(getattr(det, "prob", np.full(len(pts), np.nan)), float))
        intens_list.append(np.asarray(getattr(det, "intens", np.full(len(pts), np.nan)), float))
    points = np.concatenate(rows) if rows else np.zeros((0, 3))
    prob = np.concatenate(prob_list) if prob_list else np.zeros(0)
    intens = np.concatenate(intens_list) if intens_list else np.zeros(0)

table = pd.DataFrame({"z": points[:, 0], "y": points[:, 1], "x": points[:, 2], "prob": prob, "intens": intens[:,0]})
folder = path + "spotiflow_results/"
os.makedirs(folder, exist_ok=True)
csv_file = f"{folder}{file_name}_c{channel}.csv"
table.to_csv(csv_file, index=False)
with open(csv_file + ".json", "w", encoding="utf-8") as fh:
    json.dump({"model": model_ref, "prob_thresh": threshold, "channel": channel}, fh)
print(f"{len(table)} points written to {os.path.basename(csv_file)}")

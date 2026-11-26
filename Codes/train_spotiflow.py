"""
train_spotiflow.py <session folder> <model name> <epochs> [device]
Child script of the 'Spotiflow training' tab (run in the 'spotiflow' environment).

The session folder holds  train/  and  val/  with, for each crop, <name>.tif (Z, Y, X) and <name>.csv (columns z, y, x).
The pretrained 3D smFISH model ('smfish_3d') is refined with these crops; the new model is saved in
<session>/models/<model name>/ and its detections on every crop are written in <session>/models/<model name>/predictions/
(<set>_<crop>.csv with z, y, x, prob) so that the tab can show them.
"""
import os
import sys

import numpy as np
import pandas as pd
import tifffile as tif
from spotiflow.model import Spotiflow
from spotiflow.utils import get_data

session, name, epochs = sys.argv[1], sys.argv[2], int(float(sys.argv[3]))
device = sys.argv[4] if len(sys.argv) > 4 else "auto"
save_dir = os.path.join(session, "models", name)
if os.path.exists(save_dir):
    raise FileExistsError(f"A model named '{name}' already exists in this session. Choose another name.")

train_imgs, train_spots, val_imgs, val_spots = get_data(session, include_test=False, is_3d=True)
print(f"Training crops: {len(train_imgs)} ({sum(len(s) for s in train_spots)} spots); "
      f"validation crops: {len(val_imgs)} ({sum(len(s) for s in val_spots)} spots)", flush=True)
if not len(train_imgs) or not len(val_imgs):
    raise ValueError("Both train/ and val/ need at least one annotated crop.")

print("Loading the pretrained model smfish_3d", flush=True)
model = Spotiflow.from_pretrained("smfish_3d")
print(f"Training for {epochs} epochs (device: {device})", flush=True)
model.fit(train_imgs, train_spots, val_imgs, val_spots, save_dir=save_dir,
          train_config={"num_epochs": epochs}, device=device, logger="none")

print("Applying the new model to the crops", flush=True)
model = Spotiflow.from_folder(save_dir)
out = os.path.join(save_dir, "predictions")
os.makedirs(out, exist_ok=True)
for sub in ("train", "val"):
    folder = os.path.join(session, sub)
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith((".tif", ".tiff")):
            continue
        image = tif.imread(os.path.join(folder, fname))
        points, details = model.predict(image)
        points = np.asarray(points, float).reshape(-1, 3)
        prob = np.asarray(getattr(details, "prob", np.full(len(points), np.nan)), float)
        stem = os.path.splitext(fname)[0]
        pd.DataFrame({"z": points[:, 0], "y": points[:, 1], "x": points[:, 2], "prob": prob}).to_csv(
            os.path.join(out, f"{sub}_{stem}.csv"), index=False)
        print(f"  {sub}/{fname}: {len(points)} spots", flush=True)
print("MODEL_SAVED " + save_dir, flush=True)

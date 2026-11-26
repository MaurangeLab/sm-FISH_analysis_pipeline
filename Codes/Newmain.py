"""
Newmain.py - single-cell analysis of smFISH images (refactored version)

Called by the GUI as:  python Newmain.py <base_path> <params_json> <file_or_folder>
Run without argument, it uses the test parameters defined below.

Main changes compared to the previous version:
  - per-label statistics computed in ONE pass over the image (numpy / ndimage)
    instead of one pass per cell / per spot
  - a spot belongs to a cell only if more than 50 % of ITS volume is inside THAT cell
  - normalisation rewritten (3D and global), spot's own value excluded, NaN if no reference
  - base image detected automatically, subprocesses checked on their return code
  - background study of every image (always run), optional background correction, then two independent,
    combinable quantifications: absolute (molecule count) and relative (to a reference population)
"""
print("Importing Libraries")
try:
    import os, sys, re, json, ast, subprocess, shutil, warnings, datetime
    from collections import deque
    import numpy as np
    import pandas as pd
    import tifffile as tif
    import imageio.v3 as iio
    from scipy import ndimage
    from scipy.ndimage import generate_binary_structure, binary_dilation, distance_transform_edt
    from sklearn.mixture import GaussianMixture
except ModuleNotFoundError as e:
    print(e)
    raise

warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # optics.py is next to this file
import optics
import tif_meta

env = os.environ.copy()
env.pop("MPLBACKEND", None)

# ==============================================================================
# CONSTANTS
# ==============================================================================
HALO_ITERATIONS = 15      # halo thickness (pixels) around cells of the "group 2" type
HALO_VALUE = 7            # grey value of the halo in the composite
SPOT_THRESHOLD = 0.5      # probability above which a voxel belongs to a spot
MIN_CELL_FRACTION = 0.5   # a spot must have MORE than this fraction of its volume in its cell

# Background study / correction (can be overridden by params["background"])
BG_MARGIN = 2             # voxels excluded around every detected spot when measuring the background
BG_TRIM = 1.0             # % of the brightest voxels of each cell left out of its mean (clumps of noise)
BG_MIN_VOXELS = 50        # a cell (or a cell in one plane) with fewer usable voxels is ignored
RING_GAP, RING_WIDTH = 4, 3       # ring of the Morisaki and Stasevich method (pixels): distance from the spot, width (set in the GUI)
RING_MIN_VOXELS = 20      # a ring with fewer voxels is replaced by the background of the image
BG_NONE, BG_PER_IMAGE, BG_PER_CELL, BG_RING = "No correction", "Per image", "Per cell", "Morisaki and Stasevich method"
BG_DEPTH_PERMUTATIONS = 300   # permutations of the test "does the background change with depth?"
BG_DEPTH_ALPHA = 0.05         # significance level of that test (units: cells, not voxels)
BG_DEPTH_MIN_EFFECT = 0.03    # a significant profile smaller than this (counts, peak to peak) is not applied
ABS_NONE, ABS_CALIB = "No absolute quantification", "Quantification from one molecule"
ABS_LEGACY = {"Intensity of one molecule from isolated molecules": ABS_CALIB,      # names used by earlier presets
              "Intensity of one molecule given": ABS_NONE}
DET_MODEL, DET_SPOTIFLOW = "EpySeg model", "Spotiflow"
SRC_WEKA = "Weka (Fiji)"                 # Trainable Weka Segmentation, run by Fiji without interface
DET_COORDS = "Coordinates file (z, y, x)"          # not offered in the GUI any more; kept for command-line use
SMFISH_EXONIC, SMFISH_INTRONIC = "exonic probe", "intronic probe"
INTRONIC_MAX_SPOTS = 2                             # an intronic probe labels at most the 2 transcription sites of a cell
APERTURE_SIGMAS = 3.0     # aperture of a point from a coordinates file: ellipsoid of this many PSF sigmas (97 % of the PSF)
SIZE_MIN, SIZE_MAX = 0.5, 1.5   # calibration: accepted size of an isolated molecule, in PSF sigmas (fit of sigma_xy)
CALIB_MIN_OBJECTS = 5

# 2D structuring element (XY only, not Z), used for halos and for the background study
struct_3d = generate_binary_structure(2, 1)[np.newaxis, :, :]

NORM_NONE, NORM_EXCEPT, NORM_ONLY = "No normalisation", "All except...", "Only..."
# 1. Background correction (preprocessing, per image or per spot), then two independent results that can be combined:
#    - absolute: number of RNAs / fluorophores = BgSub_Sum / intensity of one molecule (columns *_RNA_count / *_fluorophores_count)
#    - relative: ratio to a reference population (columns *_Normalized_*), computed on the corrected intensities

# Files produced by the pipeline (never the raw image)
GENERATED_PREFIXES = ("masks", "shrinked", "detected", "merge", "chinmo_threshold",
                      "composite_", "data_", "plot_data_", "background_", "calibration_", "analysis_parameters_",
                      "Spot_numbers_", "~$")

ROLE_TO_KEY = {"Cells": "seg",
               "Objects": "detect",
               "Cell type marker": "Type",
               "Protein of interest": "protein of interest"}


# ==============================================================================
# PARAMETERS
# ==============================================================================
def parse_params(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return ast.literal_eval(raw)


if len(sys.argv) > 1:
    base_path = sys.argv[1]                  # folder containing GUI and scripts
    params = parse_params(sys.argv[2])
    path = sys.argv[3]                       # analysed file / folder
    print(path)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    params = {"channels": [
        {"role": "Protein of interest", "prot_name": "DAPI", "channel": 0},
        {"role": "Cells", "model_path": "C:/Users/ramis/Documents/Repertoire/Model/Miranda2",
         "cells_name": "Neuroblasts", "shrink_factor": "", "min_size": "", "channel": 1},
        {"role": "Objects", "model_path": "C:/Users/ramis/Documents/Repertoire/Model/linknet-vgg16-sigmoid-0.h5",
         "objects_name": "Spots", "max_spots/cell": "2", "channel": 2},
        {"role": "Cell type marker", "prot_name": "Asense", "group1": "I", "group2": "II",
         "marked": "I", "associated_cells_channels": [1], "channel": 3}],
        "zstep": "",
        "normalisation": {"norm_against": "All except...", "norm_3d": "True",
                          "norm_cells_name": "Neuroblasts", "norm_cell_type": "II"}}
    path = r'C:\Users\ramis\Documents\Fabian_smFISH\Analyzed_Optic_Lobes_E-L-L3\BenoitAI--yw_E-L3_OL_40X_DAPI_Miranda_Chinmo570-15_Asense_lame2_21-04-1'

print("Acquiring parameters")

channels = {key: [] for key in ROLE_TO_KEY.values()}
for entry in params["channels"]:
    entry = dict(entry)
    channels[ROLE_TO_KEY[entry.pop("role")]].append(entry)
params["channels"] = channels

# Python interpreters of the conda environments, given by the GUI.
ENV_PYTHONS = params.get("envs", {})

norm_settings = params.get("normalisation", {})
norm_against = norm_settings.get("norm_against", NORM_NONE)
do_norm = norm_against in (NORM_ONLY, NORM_EXCEPT)
norm_3d = str(norm_settings.get("norm_3d", "False")) == "True"
norm_pop = norm_settings.get("norm_cells_name", "")        # "" or "All cells" = every population
norm_type = norm_settings.get("norm_cell_type", "")        # "" = any type
bg_settings = params.get("background", {})
bg_method = bg_settings.get("method", BG_NONE)
bg_ring = bg_method == BG_RING                    # background of every spot measured in a ring around it
bg_per_cell = bg_method == BG_PER_CELL            # background of every spot = that of its cell
bg_correction = bg_method in (BG_PER_IMAGE, BG_PER_CELL, BG_RING)
BG_MARGIN = int(bg_settings.get("margin", BG_MARGIN))
BG_TRIM = float(bg_settings.get("trim_percent", BG_TRIM))
RING_GAP = int(float(bg_settings.get("ring_gap", RING_GAP)))
RING_WIDTH = int(float(bg_settings.get("ring_width", RING_WIDTH)))
if RING_GAP < 0 or RING_WIDTH < 1:
    raise ValueError("Ring of the background correction: distance must be >= 0 and width >= 1 pixel.")

# Absolute quantification (independent of the relative comparison): background-corrected sum / intensity of one molecule
abs_settings = params.get("absolute", {})
abs_mode = abs_settings.get("mode", ABS_NONE)
abs_mode = ABS_LEGACY.get(abs_mode, abs_mode)
do_abs = abs_mode == ABS_CALIB
abs_calib = do_abs                                      # intensity of one molecule measured in each image
abs_unit = abs_settings.get("unit", "RNA")                  # "RNA" or "fluorophores": names the column
SIZE_MIN = float(str(abs_settings.get("size_min", SIZE_MIN)).replace(",", ".") or SIZE_MIN)
SIZE_MAX = float(str(abs_settings.get("size_max", SIZE_MAX)).replace(",", ".") or SIZE_MAX)
if do_abs and not bg_correction:
    raise ValueError("Absolute quantification needs a background correction (step 1).")
optics_overrides = params.get("optics", {})            # values typed in the GUI replace the metadata

if not channels["seg"]:
    raise ValueError("No channel has the role 'Cells'.")
for key, label in (("seg", "cells"), ("detect", "objects")):
    names_ = [c["cells_name" if key == "seg" else "objects_name"] for c in channels[key]]
    if len(set(names_)) != len(names_):
        raise ValueError(f"Two {label} analyses share the same name: {names_}")

norm_type_prot = None
if do_norm and norm_type:
    norm_type_prot = next((t["prot_name"] for t in channels["Type"]
                           if norm_type in (t["group1"], t["group2"])), None)
    if norm_type_prot is None:
        raise ValueError(f"Normalisation cell type '{norm_type}' is not a group of any cell type marker.")
if do_norm and norm_pop not in ("", "All cells") \
        and norm_pop not in [c["cells_name"] for c in channels["seg"]]:
    raise ValueError(f"Normalisation cell population '{norm_pop}' does not exist.")


# ==============================================================================
# SUBPROCESSES
# ==============================================================================
def env_for_python(python_exe):
    """Environment variables allowing a conda python to run without 'conda activate'."""
    root = os.path.dirname(python_exe)
    if sys.platform == "win32":
        dirs = [root] + [os.path.join(root, "Library", sub) for sub in ("mingw-w64/bin", "usr/bin", "bin")] \
               + [os.path.join(root, "Scripts")]
        prefix = root
    else:
        dirs = [root]
        prefix = os.path.dirname(root)
    e = env.copy()
    e["PATH"] = os.pathsep.join(dirs) + os.pathsep + e.get("PATH", "")
    e["CONDA_PREFIX"] = prefix
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def save_excel(out, table=None, sheets=None, critical=True):
    """
    Writes an Excel file. If it is open in Excel (PermissionError) only one clear message is shown, no traceback:
    critical files stop the analysis (exit code 1), the others only warn.
    """
    try:
        if sheets is not None:
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                for sheet, tab in sheets.items():
                    tab.to_excel(writer, sheet_name=sheet, index=False)
        else:
            table.to_excel(out, index=False, engine="openpyxl")
    except PermissionError:
        name = os.path.basename(out)
        if critical:
            print(f"ERROR: cannot save {name}. Close it in Excel (and any other program that uses it), then run the analysis again.")
            sys.exit(1)
        print(f"  Could not save {name}: close the file if it is open in Excel.")


def check_writable(out):
    """Stops early, with one clear message, when an existing result file is locked (open in Excel)."""
    if os.path.isfile(out):
        try:
            open(out, "ab").close()
        except PermissionError:
            print(f"ERROR: {os.path.basename(out)} is open in Excel. Close it, then run the analysis again.")
            sys.exit(1)


def read_output(pipe):
    """Yields (text, is_update) for the output of a child process: is_update = the line ended with a lone '\\r'
    (progress bars), which means that the next line replaces it."""
    import re
    buffer = b""
    while True:
        chunk = os.read(pipe.fileno(), 65536)
        if not chunk:
            break
        buffer += chunk
        while True:
            m = re.search(rb"\r\n|\n|\r", buffer)
            if m is None or (m.group() == b"\r" and m.end() == len(buffer)):
                break                          # a lone '\r' at the end may be the start of '\r\n'
            line, buffer = buffer[:m.start()], buffer[m.end():]
            yield line.decode("utf-8", "replace").rstrip(), m.group() == b"\r"
    if buffer:
        yield buffer.decode("utf-8", "replace").rstrip(), False


def run_in_env(env_name, script, *args, expected=None):
    """
    Runs `script` (located next to this file) in a conda environment.
    Success = return code 0 (stderr is NOT a criterion: TensorFlow, Cellpose or tqdm
    write there even when everything is fine). Output is streamed live.
    `expected`: file that must exist afterwards.
    """
    script_path = os.path.join(base_path, script)
    python_exe = ENV_PYTHONS.get(env_name) or (sys.executable if env_name == "spots_analysis" else None)
    if python_exe and os.path.isfile(python_exe):
        cmd = [python_exe, "-u", script_path, *map(str, args)]
        run_env = env_for_python(python_exe)
    else:
        conda = shutil.which("conda")
        if conda is None:
            raise RuntimeError(f"Cannot find environment '{env_name}': no interpreter path given and 'conda' not on PATH.")
        cmd = [conda, "run", "--no-capture-output", "-n", env_name, "python", "-u", script_path, *map(str, args)]
        run_env = env
    process = subprocess.Popen(cmd, cwd=base_path, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tail = deque(maxlen=40)
    for text, is_update in read_output(process.stdout):
        tail.append(text)
        # a progress bar (tqdm) rewrites its line with '\r': the GUI must replace the line, not add one
        print(("\x01" if is_update else "") + text[:500])
    code = process.wait()
    if code != 0:
        raise RuntimeError(f"{script} failed (exit code {code}). Last lines:\n" + "\n".join(tail))
    if expected and not os.path.isfile(expected):
        raise FileNotFoundError(f"{script} finished but did not produce {expected}")


# ==============================================================================
# INPUT FOLDER
# ==============================================================================
def prepare_input(path):
    """
    Returns the analysis folder (with trailing '/').
    A folder is used as is; a tif is moved into a folder of the same name;
    a czi is converted to a tif (pixel size and depth written in the metadata).
    """
    path = os.path.normpath(path)
    if os.path.isdir(path):
        folder = path
    else:
        stem, ext = os.path.splitext(path)
        name = os.path.basename(stem)
        if ext.lower() in (".tif", ".tiff"):
            folder = stem
            os.makedirs(folder, exist_ok=True)
            shutil.move(path, os.path.join(folder, name + ".tif"))
        elif ext.lower() == ".czi":
            folder = stem
            os.makedirs(folder, exist_ok=True)
            tif_meta.convert_czi(path, os.path.join(folder, name + ".tif"))
        else:
            raise ValueError(f"Unsupported input: {path}")
    return folder.replace("\\", "/").rstrip("/") + "/"


def scan_folder(path):
    """
    Finds the raw tif (every tif that is not a generated file) and the files left by a
    previous analysis. Returns (file_name, dict of sets of channel numbers).
    """
    names = os.listdir(path)
    candidates = [n for n in names if n.lower().endswith(".tif") and not n.startswith(GENERATED_PREFIXES)]
    if not candidates:
        hint = " (a .czi is present: analyse the .czi itself, it will be converted)" \
            if any(n.lower().endswith(".czi") for n in names) else ""
        raise FileNotFoundError(f"No raw .tif image found in {path}{hint}")
    if len(candidates) == 1:
        base = candidates[0]
    else:
        folder_name = os.path.basename(path.rstrip("/"))
        same_name = [n for n in candidates if n[:-4] == folder_name]
        base = same_name[0] if same_name else max(candidates, key=lambda n: os.path.getsize(path + n))
        print(f"Several .tif files found {candidates}, using {base}")

    def channel_numbers(pattern):
        return {m.group(1) for n in names if (m := re.search(pattern, n))}

    found = {"masks": channel_numbers(r"^masks(\d+)_"),
             "shrinked": channel_numbers(r"^shrinked(\d+)_"),
             "detected": channel_numbers(r"^detected(\d+)_"),
             "measured": channel_numbers(r"-(\d+)intensity-measurements\.xlsx$")}
    return base[:-4], found


path = prepare_input(path)
file_name, found = scan_folder(path)
check_writable(f"{path}data_{file_name}.xlsx")
print("Using following file : ", file_name)
base_tif = f"{path}{file_name}.tif"

# "y" = must be computed, "n" = already on disk. The segmentation script receives `seg`.
seg = {ch: "n" for ch in found["masks"]}
shrink = {ch: "n" for ch in found["shrinked"]}
for cells in channels["seg"]:
    seg.setdefault(str(cells["channel"]), "y")
    shrink.setdefault(str(cells["channel"]), "y")
detect = {ch: "n" for ch in found["detected"]}
for probe in channels["detect"]:
    detect.setdefault(str(probe["channel"]), "y")


# ==============================================================================
# CELL SEGMENTATION
# ==============================================================================
pops = []     # one dict per cell population
for count, cells in enumerate(channels["seg"], 1):
    ch = str(cells["channel"])
    shrinked_file = f"{path}shrinked{ch}_{file_name}.tif"
    def _number(v):
        v = str(v).strip().replace(",", ".")
        return float(v) if v else 0.0                   # empty = 0 = no shrinking / no minimum size
    current = {"shrink_factor": _number(cells.get("shrink_factor", "")), "min_size": _number(cells.get("min_size", ""))}
    settings_file = shrinked_file + ".json"             # settings with which the shrunk masks were made
    try:
        with open(settings_file, encoding="utf-8") as fh:
            previous = json.load(fh)
    except (OSError, ValueError):
        previous = None
    if seg[ch] == "y" or shrink[ch] == "y" or previous != current:
        print(f"Cell segmentation number {count}")
        if cells.get("model_source") == SRC_WEKA:
            if seg[ch] == "y":
                print(f"Cell segmentation with Weka (Fiji) ({cells['cells_name']})")
                run_in_env("spots_analysis", "segmentation_weka.py", file_name, path, "cells",
                           dict(cells, fiji_path=params.get("fiji_path", "")),
                           expected=f"{path}masks{ch}_{file_name}.tif")
            # shrinking / minimum size on the masks that now exist (no model involved)
            run_in_env("spots_analysis", "segmentation_cellpose-Epyseg.py", file_name, path,
                       dict(seg, **{ch: "n"}), cells, expected=shrinked_file)
        else:
            cp_env = {2: "segment", 3: "cellpose3", 4: "cellpose4"}.get(int(float(str(cells.get("model_version", 2)))), "segment")
            print(f"Cellpose environment: {cp_env}")
            run_in_env(cp_env, "segmentation_cellpose-Epyseg.py", file_name, path, seg, cells,
                       expected=shrinked_file)
        with open(settings_file, "w", encoding="utf-8") as fh:
            json.dump(current, fh)
        print("Done")
    mask = tif.imread(shrinked_file)
    ids = np.unique(mask[mask != 0])
    want_coords = str(cells.get("cell_coordinates", "False")).strip().lower() in ("true", "1", "yes")
    pops.append({"name": cells["cells_name"], "channel": ch, "mask": mask, "ids": [int(i) for i in ids],
                 "coords": want_coords,
                 "crops": cells.get("crop_settings") if str(cells.get("export_crops", "False")).lower() == "true" else None})

pop_by_channel = {p["channel"]: p for p in pops}

all_channels = tif.imread(base_tif)     # (Z, C, Y, X)
if all_channels.ndim != 4:
    raise ValueError(f"Expected a (Z, C, Y, X) image, got shape {all_channels.shape}")


# ==============================================================================
# PER-CELL CROPS (optional, one export per cell population)
# ==============================================================================
def export_crops(pop, image, settings):
    """
    Writes one tif per cell (or per cell and slice) in '<population>_crops/' inside the analysis folder.
    settings: margin, margin_unit ('px' or 'um'), mode ('3d' or '2d'), channels (channels of the base file),
    extra_slices (planes added before and after the cell), pad (fill with zeros past the image border).
    """
    st = dict(settings or {})
    mode = str(st.get("mode", "3d")).lower()
    margin = float(str(st.get("margin", 10)).replace(",", "."))
    extra = int(st.get("extra_slices", 1))
    pad = bool(st.get("pad", True))
    n_ch = image.shape[1]
    chans = [int(c) for c in st.get("channels", range(n_ch)) if 0 <= int(c) < n_ch] or list(range(n_ch))
    try:
        has_px = iio.improps(base_tif, extension=".tif").spacing is not None
    except Exception:
        has_px = False
    pixel_um, step_um = voxel_size()
    if str(st.get("margin_unit", "px")) == "um":
        if not has_px:
            print("Crops: the margin is in um but the pixel size is unknown; crops are skipped (use pixels).")
            return
        margin_px = int(round(margin / pixel_um))
    else:
        margin_px = int(round(margin))
    out_dir = f"{path}{pop['name']}_crops/"
    os.makedirs(out_dir, exist_ok=True)
    nz, _, ny, nx = image.shape
    boxes = ndimage.find_objects(pop["mask"])
    meta_res = dict(resolution=(1 / pixel_um, 1 / pixel_um)) if has_px else {}
    unit = {"unit": "um"} if has_px else {}
    count = 0
    for cell in pop["ids"]:
        box = boxes[cell - 1] if cell - 1 < len(boxes) else None
        if box is None:
            continue
        z0, z1 = box[0].start - extra, box[0].stop + extra
        y0, y1 = box[1].start - margin_px, box[1].stop + margin_px
        x0, x1 = box[2].start - margin_px, box[2].stop + margin_px
        if not pad:
            z0, z1, y0, y1, x0, x1 = max(z0, 0), min(z1, nz), max(y0, 0), min(y1, ny), max(x0, 0), min(x1, nx)
        crop = np.zeros((z1 - z0, len(chans), y1 - y0, x1 - x0), dtype=image.dtype)
        sz, sy, sx = max(z0, 0), max(y0, 0), max(x0, 0)
        ez, ey, ex = min(z1, nz), min(y1, ny), min(x1, nx)
        crop[sz - z0:ez - z0, :, sy - y0:ey - y0, sx - x0:ex - x0] = image[sz:ez][:, chans][:, :, sy:ey, sx:ex]
        if mode == "2d":
            for k in range(crop.shape[0]):
                tif_meta.write_like(f"{out_dir}{file_name}_cell{cell}_z{z0 + k}.tif", crop[k], base_tif,
                                    axes="CYX", channels=chans)
        else:
            tif_meta.write_like(f"{out_dir}{file_name}_cell{cell}.tif", crop, base_tif, axes="ZCYX", channels=chans,
                                spacing=step_um)
        count += 1
    print(f"Crops: {count} cells saved in {out_dir}")



# ==============================================================================
# CELL TYPES (Gaussian mixture on the mean marker intensity of each cell)
# ==============================================================================
types = {}          # types[marker][population][cell] = group name
if channels["Type"]:
    print("Estimating types repartition")

for type_group in channels["Type"]:
    marker_name = type_group["prot_name"]
    types[marker_name] = {}
    marker_img = all_channels[:, type_group["channel"]]
    group1, group2, marked = type_group["group1"], type_group["group2"], type_group["marked"]
    not_marked = group1 if group2 == marked else group2

    for cells_channel in type_group["associated_cells_channels"]:
        pop = pop_by_channel.get(str(cells_channel))
        if pop is None:
            raise ValueError(f"Marker {marker_name} is associated to channel {cells_channel}, which is not a Cells channel.")

        cell_ids = np.array(pop["ids"])
        # mean marker intensity of every cell, in ONE pass over the image
        distrib = ndimage.mean(marker_img, pop["mask"], cell_ids)
        df = pd.DataFrame({"cell_label": cell_ids, "fluo_intensity": distrib})
        intensities = df["fluo_intensity"].values.reshape(-1, 1)

        results = []
        for seed in range(100):
            gmm = GaussianMixture(n_components=2, random_state=seed, n_init=10)
            gmm.fit(intensities)
            results.append(gmm.predict(intensities))

        means_list = gmm.means_.ravel().tolist()
        means = gmm.means_.tolist()
        variances = [c[0][0] for c in gmm.covariances_.tolist()]
        weights = gmm.weights_.tolist()
        agreement = np.mean([np.array_equal(results[0], r) or np.array_equal(results[0], 1 - r) for r in results[1:]])

        proba = gmm.predict_proba(intensities)
        df[not_marked] = proba[:, np.argmin(means_list)]
        df[marked] = proba[:, np.argmax(means_list)]

        types[marker_name][pop["name"]] = {
            int(cell): (marked if pm > pn else not_marked)
            for cell, pm, pn in zip(df["cell_label"], df[marked], df[not_marked])}

        marked_list = ["", ""]
        marked_list[int(np.argmin(means_list))] = not_marked
        marked_list[int(np.argmax(means_list))] = marked
        df_list = [df["cell_label"].tolist(), df["fluo_intensity"].tolist(), df[not_marked].tolist(), df[marked].tolist()]
        plot_name = f"{path}plot_data_t{type_group['channel']}c{cells_channel}_{file_name}.xlsx"

        # This line is parsed by the GUI to draw the histogram: keep its format.
        print(f"distrib:{distrib.tolist()}\\{file_name}\\{means}\\{variances}\\{weights}\\{marked_list}\\{df_list}\\{plot_name}\\{marker_name}\\{pop['name']}")
        print(f"Gaussian recognition stability : {agreement * 100:.0f}%")


# ==============================================================================
# PROTEIN OF INTEREST (summed fluorescence of each cell)
# ==============================================================================
prot_fluo = {}      # prot_fluo[protein][population][cell]
if channels["protein of interest"]:
    print("Getting protein of interest fluorescence")
for prot in channels["protein of interest"]:
    prot_img = all_channels[:, prot["channel"]]
    prot_fluo[prot["prot_name"]] = {}
    for pop in pops:
        sums = ndimage.sum_labels(prot_img, pop["mask"], np.array(pop["ids"]))
        prot_fluo[prot["prot_name"]][pop["name"]] = dict(zip(pop["ids"], np.round(sums, 2).tolist()))


# ==============================================================================
# SPOTS
# ==============================================================================
_voxel = {}


def voxel_size():
    """(pixel size in um, z step in um), read once."""
    if not _voxel:
        properties = iio.improps(base_tif, extension=".tif")
        metadata = iio.immeta(base_tif)
        if properties.spacing is None:
            print("Pixel size was not found in image metadata: volumes are in voxel units.")
            pixel = 1.0
        else:
            pixel = 1 / properties.spacing[0]
        if "spacing" in metadata:
            depth = float(metadata["spacing"])
        elif str(params.get("zstep", "")).strip() != "":
            depth = float(params["zstep"])
        else:
            depth = 0.44
            print("Pixel depth was not found in image metadata, using 0.44um as default value.")
            print("You may want to indicate Z-Step in advanced parameters next time")
        _voxel.update(pixel=pixel, depth=depth)
    return _voxel["pixel"], _voxel["depth"]


for _pop in pops:
    if _pop["crops"] is not None:
        print(f"Exporting cell crops ({_pop['name']})")
        export_crops(_pop, all_channels, _pop["crops"])


_optics = {}


def optics_of(channel):
    """
    Acquisition parameters (metadata + values typed in the GUI) and PSF widths of one channel, computed once.
    Returns {"acq", "widths", "sigma_xy_vox", "sigma_z_vox", "pixel_nm", "step_nm"}; "widths" is None when a
    parameter of the PSF is missing (the GUI fields or the metadata must give it).
    """
    channel = str(channel)
    if channel in _optics:
        return _optics[channel]
    acq = optics.merge_overrides(optics.read_acquisition(base_tif, int(channel)), optics_overrides)
    pixel_um, step_um = voxel_size()
    pixel_nm = acq.get("pixel_xy_nm") or pixel_um * 1000.0
    step_nm = acq.get("step_z_nm") or step_um * 1000.0
    info = {"acq": acq, "widths": None, "sigma_xy_vox": None, "sigma_z_vox": None,
            "pixel_nm": pixel_nm, "step_nm": step_nm, "missing": optics.missing_for_psf(acq)}
    absent = optics.missing_for_psf(acq, need_pinhole=True)
    if absent:
        print(f"WARNING optics channel {channel}: not found in the image: {', '.join(absent)}. "
              "Enter them in Advanced > Optics. " + ("The PSF cannot be computed: default apertures are used."
                                                      if info["missing"] else "The PSF is computed as for a widefield microscope."))
    if not info["missing"]:
        info["widths"] = optics.psf_widths(acq, confocal=bool(acq.get("pinhole_au") or acq.get("pinhole_detector_um")))
        info["sigma_xy_vox"], info["sigma_z_vox"] = optics.sigmas_in_voxels(info["widths"], pixel_nm, step_nm)
    _optics[channel] = info
    return info


def find_coordinates_file(channel):
    """CSV of coordinates of one channel, searched in the image folder (and in a 'spotiflow_results' subfolder)."""
    folders = [path] + [path + d + "/" for d in ("spotiflow_results",) if os.path.isdir(path + d)]
    csvs = [f + n for f in folders for n in sorted(os.listdir(f)) if n.lower().endswith(".csv")]
    mine = [c for c in csvs if file_name in os.path.basename(c)]
    chan = [c for c in mine if re.search(rf"(?:^|[^a-z0-9])c(?:h|hannel)?{channel}(?:[^0-9]|$)", os.path.basename(c), re.I)]
    for group in (chan, mine, csvs):
        if len(group) == 1:
            return group[0]
        if len(group) > 1:
            raise ValueError(f"Several coordinate files could match channel {channel}: {[os.path.basename(g) for g in group]}. "
                             f"Keep one, or put '{file_name}' and 'c{channel}' in its name.")
    raise FileNotFoundError(f"No .csv coordinate file found in {path} for channel {channel} "
                            f"(its name must contain '{file_name}').")


def read_coordinates(csv_file, shape):
    """
    (points as an (n, 3) array z, y, x in voxels, extra columns). 3D tables are z, y, x (columns z, y, x or
    axis-0, axis-1, axis-2); 2D tables are y, x (axis-0, axis-1) and need an image with a single plane.
    Coordinates are in pixels, sub-pixel, the centre of the first voxel being 0 (Spotiflow convention).
    """
    df = pd.read_csv(csv_file)
    for c in list(df.columns):
        if str(c).strip().lower() in ("", "index", "unnamed: 0"):
            df = df.drop(columns=c)
    low = {str(c).strip().lower(): c for c in df.columns}
    if {"z", "y", "x"} <= low.keys():
        cols = [low["z"], low["y"], low["x"]]
    elif {"axis-0", "axis-1", "axis-2"} <= low.keys():
        cols = [low["axis-0"], low["axis-1"], low["axis-2"]]
    elif {"y", "x"} <= low.keys():
        cols = [None, low["y"], low["x"]]
    elif {"axis-0", "axis-1"} <= low.keys():
        cols = [None, low["axis-0"], low["axis-1"]]
    else:
        raise ValueError(f"{os.path.basename(csv_file)}: columns {list(df.columns)} not understood "
                         "(expected z, y, x or axis-0, axis-1, axis-2).")
    if cols[0] is None:
        if shape[0] != 1:
            raise ValueError(f"{os.path.basename(csv_file)} has 2D coordinates (y, x) but the image has {shape[0]} planes.")
        pts = np.column_stack([np.zeros(len(df)), df[cols[1]], df[cols[2]]])
    else:
        pts = df[cols].to_numpy(float)
    extra = {c: df[c].to_numpy() for c in df.columns if c not in cols}
    return pts, extra


def labels_from_coordinates(pts, shape, sigma_xy, sigma_z, k=APERTURE_SIGMAS):
    """
    Label image of a table of points: every point becomes an ellipsoid (the aperture) of radii
    k * sigma_xy (in the plane) and k * sigma_z (in depth), in voxels, centred on the sub-pixel position.
    A voxel claimed by two points goes to the nearer one (in units of the aperture). Points outside the image
    are dropped. Returns (labels, number of points kept, number dropped).
    """
    labels = np.zeros(shape, dtype=np.int32)
    best = np.full(shape, np.inf, dtype=np.float32)
    rz, rxy = k * sigma_z, k * sigma_xy
    kept = 0
    rows = []                                       # rows[label - 1] = index of the point in the table
    for row, p in enumerate(pts):
        if not (-0.5 <= p[0] < shape[0] - 0.5 and -0.5 <= p[1] < shape[1] - 0.5 and -0.5 <= p[2] < shape[2] - 0.5):
            continue
        kept += 1
        rows.append(row)
        lo = [max(int(np.floor(c - r)), 0) for c, r in zip(p, (rz, rxy, rxy))]
        hi = [min(int(np.ceil(c + r)) + 1, s) for c, r, s in zip(p, (rz, rxy, rxy), shape)]
        zz, yy, xx = np.ogrid[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        d2 = ((zz - p[0]) / rz) ** 2 + ((yy - p[1]) / rxy) ** 2 + ((xx - p[2]) / rxy) ** 2
        sl = (slice(lo[0], hi[0]), slice(lo[1], hi[1]), slice(lo[2], hi[2]))
        win = best[sl]
        better = (d2 <= 1) & (d2 < win)
        win[better] = d2[better]
        labels[sl][better] = kept
        if not (labels[sl] == kept).any():          # the aperture holds no voxel centre: take the nearest voxel
            ci = tuple(int(np.clip(round(c), 0, s - 1)) for c, s in zip(p, shape))
            labels[ci] = kept
            best[ci] = 0
    return labels, kept, len(pts) - kept, rows


def attribute_spots(labeled, mask, detected, cell_ids):
    """
    For every cell, the spots having MORE than 50 % of their volume inside THAT cell.
    Returns {cell: {spot: (fraction of spot inside the cell, mean probability inside the cell)}}.
    Only the voxels of spots are looked at (one pass, no loop over cells or spots).
    """
    result = {c: {} for c in cell_ids}
    fg = labeled > 0
    spot_v = labeled[fg].astype(np.int64)
    cell_v = mask[fg].astype(np.int64)
    inside = cell_v > 0
    if not inside.any():
        return result
    total = np.bincount(spot_v)                              # voxels of each spot
    spot_in, cell_in = spot_v[inside], cell_v[inside]
    if detected.ndim == 1:                                   # one probability per spot (indexed by label)
        prob_in = detected[spot_in].astype(np.float64)
    else:                                                    # probability map
        prob_in = detected[fg][inside].astype(np.float64)
    width = int(cell_in.max()) + 1
    # one key per (spot, cell) pair; np.unique counts the voxels of each pair
    pair_keys, inverse, counts = np.unique(spot_in * width + cell_in, return_inverse=True, return_counts=True)
    prob_sum = np.bincount(inverse.ravel(), weights=prob_in)
    pair_spot, pair_cell = pair_keys // width, pair_keys % width
    fraction = counts / total[pair_spot]
    probability = prob_sum / counts
    for s, c, f, p in zip(pair_spot.tolist(), pair_cell.tolist(), fraction, probability):
        if f > MIN_CELL_FRACTION:
            result[c][s] = (round(float(f), 2), round(float(p), 2))
    return result


def measure_spots(labeled, num, channel):
    """Mean, sum, max, volume and center of mass of every spot, computed on spot voxels only."""
    img = all_channels[:, int(channel)]
    fg = labeled > 0
    lab = labeled[fg]
    zz, yy, xx = np.nonzero(fg)
    val = img[fg].astype(np.float64)
    size = num + 1
    nvox = np.bincount(lab, minlength=size)[1:]
    total = np.bincount(lab, weights=val, minlength=size)[1:]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = total / nvox
        com_x = np.bincount(lab, weights=val * xx, minlength=size)[1:] / total
        com_y = np.bincount(lab, weights=val * yy, minlength=size)[1:] / total
        com_z = np.bincount(lab, weights=val * zz, minlength=size)[1:] / total
    vmax = ndimage.maximum(img, labeled, np.arange(1, size))
    pixel, depth = voxel_size()
    return pd.DataFrame({"Label": np.arange(1, size), "Mean": mean, "Sum": total, "Max": vmax,
                         "NumberOfVoxels": nvox, "Volume": np.round(nvox * (pixel ** 2 * depth), 3),
                         "CenterOfMass.X": com_x, "CenterOfMass.Y": com_y, "CenterOfMass.Z": com_z})


def matches_norm_target(parents):
    """True if one parent cell of the spot belongs to the population / cell type of interest."""
    for pop_name, cell in parents:
        if norm_pop not in ("", "All cells") and pop_name != norm_pop:
            continue
        if norm_type and types[norm_type_prot].get(pop_name, {}).get(cell) != norm_type:
            continue
        return True
    return False


def _tmean(v):
    """Mean of v without its brightest BG_TRIM percent (clumps of noise)."""
    v = np.asarray(v, dtype=np.float64)
    if BG_TRIM > 0 and v.size > 1:
        v = v[v <= np.quantile(v, 1 - BG_TRIM / 100)]
    return float(v.mean())


def _native(x):
    """Converts numpy values to plain python (for json)."""
    if isinstance(x, dict):
        return {k: _native(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_native(v) for v in x]
    if isinstance(x, np.ndarray):
        return _native(x.tolist())
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def _tstats(v):
    """(mean, variance, size) of v without its brightest BG_TRIM percent."""
    v = np.asarray(v, dtype=np.float64)
    if BG_TRIM > 0 and v.size > 1:
        v = v[v <= np.quantile(v, 1 - BG_TRIM / 100)]
    return float(v.mean()), float(v.var()), int(v.size)


def _backfit(cell_idx, plane_idx, n, m, n_planes, shrink, iterations=30):
    """
    Additive model  mean(cell, plane) = a[cell] + f[plane]  fitted by weighted least squares (weights = voxels).
    f is a profile in depth shared by all the cells, estimated with a light ridge (`shrink` voxels of prior at 0)
    so that planes seen in few cells do not get a noisy value. Gauge: weighted mean of f = 0.
    """
    f = np.zeros(n_planes)
    n_cells = int(cell_idx.max()) + 1
    cell_w = np.bincount(cell_idx, weights=n, minlength=n_cells)
    for _ in range(iterations):
        a = np.bincount(cell_idx, weights=n * (m - f[plane_idx]), minlength=n_cells) / cell_w
        num = np.bincount(plane_idx, weights=n * (m - a[cell_idx]), minlength=n_planes)
        den = np.bincount(plane_idx, weights=n, minlength=n_planes)
        f = num / (den + shrink)
        f -= (n * f[plane_idx]).sum() / n.sum()
    return a, f


def fit_depth_profile(plane_table, n_planes):
    """
    Does the background change with depth, once the differences between cells are taken out?
    Test on CELLS (not on voxels, which would make any tiny effect significant): the planes of each cell
    are shuffled (permutation test) and the gain of the profile is compared with the observed gain.
    The profile is applied only if the test is significant AND its peak-to-peak size is at least
    BG_DEPTH_MIN_EFFECT counts.
    """
    out = {"f": np.zeros(n_planes), "applied": False, "p": np.nan, "effect": np.nan}
    if len(plane_table) == 0:
        return out
    key = plane_table["pop"].astype(str) + "#" + plane_table["cell"].astype(str)
    cell_all = pd.factorize(key)[0]
    rows_per_cell = np.bincount(cell_all)
    keep = rows_per_cell[cell_all] >= 2                  # a cell seen in one plane says nothing about depth
    if keep.sum() < 8 or len(np.unique(plane_table["plane"].to_numpy()[keep])) < 3:
        return out
    cell_idx = pd.factorize(cell_all[keep])[0]
    plane_idx = plane_table["plane"].to_numpy(int)[keep]
    n = plane_table["voxels"].to_numpy(float)[keep]
    m = plane_table["mean"].to_numpy(float)[keep]
    if cell_idx.max() + 1 < 4:
        return out
    shrink = float(np.median(n))

    def gain(planes):
        a, f = _backfit(cell_idx, planes, n, m, n_planes, shrink)
        a0 = np.bincount(cell_idx, weights=n * m) / np.bincount(cell_idx, weights=n)
        ss0 = (n * (m - a0[cell_idx]) ** 2).sum()
        ss1 = (n * (m - a[cell_idx] - f[planes]) ** 2).sum()
        return ss0 - ss1, f

    observed, f = gain(plane_idx)
    groups = [np.flatnonzero(cell_idx == c) for c in range(cell_idx.max() + 1)]
    rng = np.random.default_rng(0)
    exceed = 0
    for _ in range(BG_DEPTH_PERMUTATIONS):
        shuffled = plane_idx.copy()
        for g in groups:
            shuffled[g] = rng.permutation(plane_idx[g])
        exceed += gain(shuffled)[0] >= observed
    seen = np.unique(plane_idx)
    out["p"] = float((1 + exceed) / (BG_DEPTH_PERMUTATIONS + 1))
    out["effect"] = float(f[seen].max() - f[seen].min())
    if out["p"] < BG_DEPTH_ALPHA and out["effect"] >= BG_DEPTH_MIN_EFFECT:
        out["applied"] = True
        out["f"] = f
    return out


def background_study(img, labeled, probe_name, channel):
    """
    Background of the probe channel, measured in the cells, away from the detected spots.
    Background voxels = voxels of a cell that are more than BG_MARGIN voxels from any detected spot.
      - per cell: trimmed mean a(cell) (BG_TRIM % brightest voxels left out) over the whole cell
      - depth: profile f(plane) common to all cells (additive model, test on cells), applied only if significant
      - B of the image = median of the a(cell), with the depth profile taken out of each of them
      - per cell mode: a(cell) pulled towards B when the cell has few voxels (empirical Bayes shrinkage)
    Each cell is handled inside its own bounding box, never with a pass over the whole volume.
    Returns a dict (B, profile, per-cell values...). Everything is also written to an Excel file.
    """
    structure = generate_binary_structure(3, 1)
    spots = labeled > 0
    nz = img.shape[0]
    small_int = np.issubdtype(img.dtype, np.integer) and img.dtype.itemsize <= 2
    hist = np.zeros(int(np.iinfo(img.dtype).max) + 1, dtype=np.int64) if small_int else None
    sheets = {}
    cell_rows, plane_rows = [], []
    pooled_planes = {}                      # plane -> [sum(mean * voxels), voxels]

    for pop in pops:
        mask = pop["mask"]
        boxes = ndimage.find_objects(mask)
        pop_planes = []
        plane_vals = [[] for _ in range(nz)]
        pop_cells = []
        for cell in pop["ids"]:
            box = boxes[cell - 1] if cell - 1 < len(boxes) else None
            if box is None:
                continue
            padded = tuple(slice(max(s.start - BG_MARGIN, 0), min(s.stop + BG_MARGIN, dim))
                           for s, dim in zip(box, mask.shape))
            near_spot = binary_dilation(spots[padded], structure=structure, iterations=BG_MARGIN) \
                if BG_MARGIN > 0 else spots[padded]
            crop = tuple(slice(b.start - p.start, b.stop - p.start) for b, p in zip(box, padded))
            usable = (mask[box] == cell) & ~near_spot[crop]
            sub = img[box]
            vals = sub[usable]
            row = {"pop": pop["name"], "cell": cell, "z_center": (box[0].start + box[0].stop - 1) / 2,
                   "voxels": int(vals.size), "mean": np.nan, "median": np.nan, "var": np.nan}
            if vals.size >= BG_MIN_VOXELS:
                row["mean"], row["var"], _ = _tstats(vals)
                row["median"] = float(np.median(vals))
                if hist is not None:
                    hist += np.bincount(vals, minlength=hist.size)
                for zi in range(usable.shape[0]):
                    v = sub[zi][usable[zi]]
                    if v.size >= BG_MIN_VOXELS:
                        z = box[0].start + zi
                        pop_planes.append({"pop": pop["name"], "cell": cell, "plane": z, "voxels": int(v.size),
                                           "mean": _tmean(v)})
                        plane_vals[z].append(v)
            pop_cells.append(row)
        cell_rows.extend(pop_cells)
        plane_rows.extend(pop_planes)
        planes = pd.DataFrame([{"plane": z, "cells": len(vs), "voxels": int(sum(v.size for v in vs)),
                                "mean": _tmean(np.concatenate(vs))}
                               for z, vs in enumerate(plane_vals) if vs])
        sheets[f"cells_{pop['name']}"[:31]] = pd.DataFrame(pop_cells)
        sheets[f"cell_x_plane_{pop['name']}"[:31]] = pd.DataFrame(pop_planes)
        sheets[f"planes_{pop['name']}"[:31]] = planes
        for r in planes.itertuples():
            acc = pooled_planes.setdefault(int(r.plane), [0.0, 0])
            acc[0] += r.mean * r.voxels
            acc[1] += r.voxels

    result = {"probe": probe_name, "channel": str(channel), "B": np.nan, "n_cells": 0, "cell_means": [],
              "spread": np.nan, "slope": np.nan, "depth_change": np.nan, "planes": [], "profile": [],
              "hist": None, "rho": np.nan, "depth_applied": False, "depth_p": np.nan, "depth_effect": np.nan,
              "a_cell": {}, "se_cell": {}, "f_arr": np.zeros(nz), "unexplained": 0.0,
              "cell_table": [[r["pop"], int(r["cell"]), r["z_center"], r["voxels"], r["mean"], r["median"], r["var"]]
                             for r in cell_rows]}
    cells_all = pd.DataFrame(cell_rows)
    valid = cells_all.dropna(subset=["mean"]).copy() if len(cells_all) else cells_all
    if len(valid) == 0:
        return result
    plane_table = pd.DataFrame(plane_rows)

    # depth profile, then the level of every cell with the profile taken out
    fit = fit_depth_profile(plane_table, nz)
    f = fit["f"]
    valid["a"] = valid["mean"]
    if fit["applied"]:
        key_p = plane_table["pop"].astype(str) + "#" + plane_table["cell"].astype(str)
        shift = (plane_table["voxels"] * f[plane_table["plane"].to_numpy(int)]).groupby(key_p).sum() \
            / plane_table["voxels"].groupby(key_p).sum()
        key_v = valid["pop"].astype(str) + "#" + valid["cell"].astype(str)
        valid["a"] = valid["mean"] - key_v.map(shift).fillna(0.0).to_numpy()
    a = valid["a"].to_numpy(float)
    B = float(np.median(a))

    # per cell level: shrinkage towards B for the cells with few voxels
    vox = valid["voxels"].to_numpy(float)
    sigma2 = float((vox * valid["var"].to_numpy(float)).sum() / vox.sum())
    se2 = sigma2 / vox
    tau2 = max(0.0, float(np.var(a)) - float(se2.mean())) if len(a) > 2 else 0.0
    w = tau2 / (tau2 + se2) if tau2 > 0 else np.zeros(len(a))
    # what the model (cell level + depth profile) does not explain: scatter of the cell-plane means beyond sampling noise
    unexplained = 0.0
    if len(plane_table):
        key_p = plane_table["pop"].astype(str) + "#" + plane_table["cell"].astype(str)
        key_v = valid["pop"].astype(str) + "#" + valid["cell"].astype(str)
        a_of = pd.Series(a, index=key_v.to_numpy())
        resid = plane_table["mean"].to_numpy(float) - key_p.map(a_of).to_numpy(float) - f[plane_table["plane"].to_numpy(int)]
        ok = np.isfinite(resid)
        if ok.sum() > 3:
            noise = float(np.mean(sigma2 / plane_table["voxels"].to_numpy(float)[ok]))
            unexplained = float(np.sqrt(max(0.0, np.var(resid[ok]) - noise)))
    valid["a_star"] = w * a + (1 - w) * B
    valid["se_star"] = np.sqrt(w * se2)
    result.update(B=B, n_cells=len(a), cell_means=a.tolist(), spread=float(np.percentile(a, 95) - np.percentile(a, 5)),
                  depth_applied=bool(fit["applied"]), depth_p=fit["p"], depth_effect=fit["effect"],
                  f_arr=f, tau=float(np.sqrt(tau2)), unexplained=unexplained,
                  a_cell={(r.pop, int(r.cell)): float(r.a_star) for r in valid.itertuples()},
                  se_cell={(r.pop, int(r.cell)): float(r.se_star) for r in valid.itertuples()})
    if hist is not None:
        total = hist.sum()
        top = 9
        result["hist"] = [100 * hist[v] / total for v in range(top)] + [100 * hist[top:].sum() / total]
    if len(a) >= 5:
        from scipy.stats import spearmanr
        result["rho"] = float(spearmanr(valid["z_center"], a)[0])
    if pooled_planes:
        zs = np.array(sorted(pooled_planes))
        pm = np.array([pooled_planes[z][0] / pooled_planes[z][1] for z in zs])
        pv = np.array([pooled_planes[z][1] for z in zs])
        result["planes"] = [(int(z), float(m), int(v)) for z, m, v in zip(zs, pm, pv)]
        result["profile"] = [(int(z), float(B + f[z])) for z in zs]
        sheets["profile"] = pd.DataFrame({"plane": zs, "f": f[zs], "B_of_plane": B + f[zs]})
    sheets["cells_model"] = valid.drop(columns=["median"]).reset_index(drop=True)
    sheets["image"] = pd.DataFrame([{"probe": probe_name, "channel": channel, "B": B, "cells": len(a),
                                     "spread_p95_p5": result["spread"], "depth_profile_applied": fit["applied"],
                                     "depth_p_value": fit["p"], "depth_effect_peak_to_peak": fit["effect"],
                                     "between_cells_sd_tau": result["tau"], "unexplained_sd": unexplained,
                                     "margin_voxels": BG_MARGIN, "trim_percent": BG_TRIM}])
    out = f"{path}background_s{channel}_{file_name}.xlsx"
    save_excel(out, sheets=sheets, critical=False)
    return result


def ring_background(img, labeled, boxes):
    """
    Local background of every spot (Morisaki and Stasevich method): mean of the image in a ring around
    the spot, RING_WIDTH pixels wide, starting RING_GAP pixels from the spot. The ring is drawn in each
    plane the spot occupies (distance in the plane, 2D), other spots are left out.
    NaN when the ring has fewer than RING_MIN_VOXELS voxels (the image background is used instead).
    """
    reach = RING_GAP + RING_WIDTH
    out = np.full(len(boxes), np.nan)
    for i, box in enumerate(boxes):
        if box is None:
            continue
        pad = (box[0],) + tuple(slice(max(s.start - reach, 0), min(s.stop + reach, dim))
                                for s, dim in zip(box[1:], labeled.shape[1:]))
        lab = labeled[pad]
        me = lab == i + 1
        # huge z sampling: planes without the spot are infinitely far, so only the spot's planes count
        dist = distance_transform_edt(~me, sampling=(1e6, 1, 1))
        ring = (dist > RING_GAP) & (dist <= reach) & (lab == 0)
        if ring.sum() >= RING_MIN_VOXELS:
            out[i] = img[pad][ring].mean()
    return out


def spot_backgrounds(study, labeled, num, parent_of, ring):
    """
    Background of every spot (b_spot) and its standard error (se_spot, per cell mode only).
      - Morisaki and Stasevich: its ring (image background when the ring is too small)
      - Per image: B of the image + depth profile averaged over the planes of the spot (if significant)
      - Per cell:  level of the spot's cell (first population that owns the spot) + the same profile
    A spot outside any cell, or in a cell without enough voxels, gets the level of the image.
    """
    if study is None:
        return np.full(num, np.nan), np.full(num, np.nan)
    if bg_ring:
        return np.where(np.isfinite(ring), ring, study["B"]), np.full(num, np.nan)
    level = np.full(num, study["B"])
    se = np.full(num, np.nan)
    if bg_per_cell:
        for s, parents in parent_of.items():
            for pop_name, cell in parents:
                if (pop_name, cell) in study["a_cell"]:
                    level[s - 1] = study["a_cell"][(pop_name, cell)]
                    se[s - 1] = study["se_cell"][(pop_name, cell)]
                    break
    if study["depth_applied"]:
        fg = labeled > 0
        lab, zs = labeled[fg], np.nonzero(fg)[0]
        size = np.bincount(lab, minlength=num + 1)[1:]
        level = level + np.bincount(lab, weights=study["f_arr"][zs], minlength=num + 1)[1:] / size
    return level, se


def finalize_background(probe):
    """
    Once the kept spots are known: typical signal, error rate of the background estimate, and the record read
    by the GUI (plot panel and summary at the end of the session). The error rate is an indication only:
      - Per image: half of the variation of the background between cells (p95 - p5 of the cell levels), and
        half of the depth profile when it was NOT applied, as a % of the corrected signal (spot mean - B)
      - Per cell: standard error of the cell levels used combined with the scatter that the model (cell level +
        depth profile) does not explain, as a % of the corrected signal
      - Morisaki and Stasevich: no error rate (one ring per spot)
    """
    study = probe["study"]
    if study is None:
        return
    kept = np.array(sorted(probe["kept"]), dtype=int)
    B = study["B"]
    typical = float(np.median(probe["mean"][kept - 1])) if kept.size else np.nan
    signal = typical - B
    n_fallback = int(np.sum(~np.isfinite(probe["ring"][kept - 1]))) if (kept.size and bg_ring) else 0
    err_cells = err_depth = error = np.nan
    if np.isfinite(signal) and signal > 0 and not bg_ring:
        if bg_per_cell:
            se = probe["se_spot"][kept - 1]
            se = se[np.isfinite(se)]
            err_cells = 100 * float(np.hypot(np.median(se), study["unexplained"])) / signal if se.size else np.nan
            error = err_cells
        else:
            err_cells = 100 * (study["spread"] / 2) / signal
            err_depth = 0.0 if study["depth_applied"] else \
                (100 * (study["depth_effect"] / 2) / signal if np.isfinite(study["depth_effect"]) else np.nan)
            error = float(np.nanmax([err_cells, err_depth]))
    ring = probe["ring"][kept - 1] if kept.size else np.array([])
    ring = ring[np.isfinite(ring)]
    probe["bg_record"] = {
        "file": file_name, "probe": probe["name"], "channel": probe["channel"], "B": B,
        "n_cells": study["n_cells"], "cell_means": study["cell_means"], "spread": study["spread"],
        "slope": study["slope"], "depth_change": study["depth_effect"], "planes": study["planes"],
        "profile": study["profile"], "depth_applied": study["depth_applied"], "depth_p": study["depth_p"],
        "depth_effect": study["depth_effect"], "hist": study["hist"], "typical_spot_mean": typical, "signal": signal,
        "error_pct": error, "err_cells_pct": err_cells, "err_depth_pct": err_depth,
        "ring_median": float(np.median(ring)) if ring.size else np.nan,
        "corrected": bool(bg_correction), "method": bg_method, "ring_fallback": n_fallback,
        "n_spots": int(kept.size), "cell_table": study.get("cell_table", [])}
    print("background:" + json.dumps(_native(probe["bg_record"])))       # read by the GUI


def is_intronic(probe):
    return str(probe.get("smfish_type", "")).strip().lower().startswith("intron")


def max_spots_of(probe):
    """Spots kept per cell: 2 for an intronic probe, no limit for an exonic one (earlier presets: 'max_spots/cell')."""
    kind = str(probe.get("smfish_type", "")).strip().lower()
    if kind.startswith("intron"):
        return INTRONIC_MAX_SPOTS
    if kind.startswith("exon"):
        return None
    legacy = str(probe.get("max_spots/cell", "")).strip()
    return None if legacy == "" else int(float(legacy))


def run_spotiflow(n_probe, probe):
    """
    Runs Spotiflow (child script, environment 'spotiflow') on the channel of this probe and returns the CSV of the
    points (z, y, x, prob, intens). Nothing is computed again when a CSV made with the same model and threshold exists.
    """
    channel = str(probe["channel"])
    folder = f"{path}spotiflow_results/"
    csv_file = f"{folder}{file_name}_c{channel}.csv"
    settings = {"model": str(probe.get("model_path", "")), "prob_thresh": str(probe.get("spotiflow_prob_thresh", "")).strip().replace(",", "."),
                "channel": int(channel)}
    try:
        with open(csv_file + ".json", encoding="utf-8") as fh:
            same = json.load(fh) == settings
    except (OSError, ValueError):
        same = False
    if same and os.path.isfile(csv_file):
        print(f"Spotiflow points found ({os.path.basename(csv_file)}); not computed again.")
        return csv_file
    print(f"Objects detection with Spotiflow ({probe['objects_name']})")
    run_in_env("spotiflow", "spotiflow_detection.py", file_name, path, channels["detect"], n_probe, expected=csv_file)
    print("Done")
    return csv_file


def process_probe(n_probe, probe):
    channel = str(probe["channel"])
    probe_name = probe["objects_name"]
    detected_file = f"{path}detected{channel}_{file_name}.tif"
    detection_ran = False
    method = probe.get("detection", DET_MODEL)

    csv_file = None
    if method == DET_SPOTIFLOW:
        csv_file = run_spotiflow(n_probe, probe)
        method = DET_COORDS                                # from here the points are handled as a coordinates table
    if method == DET_COORDS:
        csv_file = csv_file or find_coordinates_file(channel)
        pts, extra = read_coordinates(csv_file, all_channels.shape[:1] + all_channels.shape[2:])
        info = optics_of(channel)
        if info["sigma_xy_vox"] is None:
            sxy, sz = 1.2, 0.6
            print(f"PSF unknown (missing: {info['missing']}): apertures use default widths {sxy} / {sz} voxels.")
        else:
            sxy, sz = info["sigma_xy_vox"], info["sigma_z_vox"]
        k = float(str(probe.get("aperture_sigmas", APERTURE_SIGMAS)).replace(",", ".") or APERTURE_SIGMAS)
        print(f"Objects from {os.path.basename(csv_file)}")
        labeled, num, dropped, rows = labels_from_coordinates(pts, all_channels.shape[:1] + all_channels.shape[2:], sxy, sz, k)
        if dropped:
            print(f"{dropped} point(s) outside the image were ignored.")
        if num == 0:
            raise Exception(f"No object in the coordinates of channel {channel} ({probe_name}).")
        detection_ran = True
        low = {str(c).strip().lower(): c for c in extra}
        prob_col = next((low[c] for c in ("prob", "probability", "proba") if c in low), None)
        int_col = next((low[c] for c in ("intens", "intensity") if c in low), None)
        detected = np.ones(num + 1)                        # probability of each spot (index = label); 1 if the table has none
        probe_extra = {}
        if prob_col is not None:
            detected[1:] = np.asarray(extra[prob_col], float)[rows]
            probe_extra["spotiflow_prob"] = detected.copy()
        if int_col is not None:
            vals = np.full(num + 1, np.nan)
            vals[1:] = np.asarray(extra[int_col], float)[rows]
            probe_extra["spotiflow_intensity"] = vals
    else:
        if detect[channel] == "y":
            print(f"Objects detection number {n_probe + 1}")
            if probe.get("model_source") == SRC_WEKA:
                run_in_env("spots_analysis", "segmentation_weka.py", file_name, path, "objects",
                           dict(probe, fiji_path=params.get("fiji_path", "")), expected=detected_file)
            else:
                run_in_env("chinmospots", "spot_segmentation.py", file_name, path, channels["detect"], n_probe,
                           expected=detected_file)
            print("Done")
            detection_ran = True
        print("Creating new images for analysis")
        detected = tif.imread(detected_file)
        labeled, num = ndimage.label(detected > SPOT_THRESHOLD)     # connected components
        if num == 0:
            raise Exception(f"No object detected in channel {channel} ({probe_name}).")
    tif_meta.write_like(f"{path}chinmo_threshold{channel}_{file_name}-lbl.tif", labeled, base_tif, axes="ZYX")

    channel_img = all_channels[:, int(channel)]
    try:
        study = background_study(channel_img, labeled, probe_name, channel)
    except Exception:
        if bg_correction:
            raise           # a correction was requested: do not go on without a background
        import traceback
        print("Background study failed (the analysis continues, no correction requested):")
        print(traceback.format_exc())
        study = None
    if bg_correction and (study is None or not np.isfinite(study["B"])):
        raise ValueError(f"Background correction requested but the background of {probe_name} "
                         "could not be estimated (no cell with enough background voxels).")

    # spot -> cell attribution, for every population
    spot_proba = {}
    for pop in pops:
        # file with only the spot voxels located in cells (to check it visually)
        tif_meta.write_like(f"{path}merge_threshold_s{channel}c{pop['channel']}_{file_name}.tif",
                            labeled * (pop["mask"] > 0), base_tif, axes="ZYX")
        spot_proba[pop["name"]] = attribute_spots(labeled, pop["mask"], detected, pop["ids"])

    parent_of = {}      # spot -> [(population, cell), ...]
    for pop_name, cells in spot_proba.items():
        for cell, spots in cells.items():
            for s in spots:
                parent_of.setdefault(s, []).append((pop_name, cell))

    # Z extent of every spot (bounding boxes)
    boxes = ndimage.find_objects(labeled)
    z_min = np.array([b[0].start for b in boxes], dtype=float)
    z_max = np.array([b[0].stop - 1 for b in boxes], dtype=float)
    ring = ring_background(channel_img, labeled, boxes) if study is not None else None
    b_spot, se_spot = spot_backgrounds(study, labeled, num, parent_of, ring)

    # intensity measurements
    measure_file = f"{path}{file_name}-{channel}intensity-measurements.xlsx"
    fresh = not (channel in found["measured"] and not detection_ran)
    if not fresh:
        print("Previously measured intensities were found. Skipping it.")
        IM = pd.read_excel(measure_file)
        if not np.array_equal(IM["Label"].to_numpy(), np.arange(1, num + 1)):
            raise ValueError(f"{measure_file} does not match the detection. Delete it and run again.")
    else:
        print("Gathering information on every point")
        IM = measure_spots(labeled, num, channel)

    # Columns that let the viewer recompute BgSub / absolute count / normalised values of every spot (including the
    # ones validated by hand) without the image: local background, background-corrected values, Z extent, parent cells.
    # An existing file that lacks them, or whose values differ from this analysis (other background settings), is updated.
    background = np.asarray(b_spot, dtype=float) if bg_correction else np.zeros(num)
    derived = {
        "Background": background,                      # full precision: the viewer rounds like this script does
        "BgSub_Sum": IM["Sum"].to_numpy(float) - IM["NumberOfVoxels"].to_numpy(float) * background,
        "BgSub_Mean": IM["Mean"].to_numpy(float) - background,
        "ZMin": z_min, "ZMax": z_max,
        "ParentCells": [";".join(f"{pn}:{c}" for pn, c in parent_of.get(i, [])) for i in range(1, num + 1)]}
    changed = fresh
    for name, values in derived.items():
        if name not in IM.columns:
            changed = True
        elif name == "ParentCells":
            changed |= bool((IM[name].fillna("").astype(str).to_numpy() != np.array(values, dtype=object)).any())
        else:
            changed |= not np.allclose(IM[name].to_numpy(float), np.asarray(values, dtype=float), equal_nan=True,
                                       rtol=1e-9, atol=1e-6)
        IM[name] = values
    if changed:
        if not fresh:
            print("Updating the intensity measurements file (background columns)")
        save_excel(measure_file, IM)

    data = {"name": probe_name, "channel": channel, "num": num, "spot_proba": spot_proba, "img": channel_img,
            "com": np.column_stack([IM["CenterOfMass.Z"], IM["CenterOfMass.Y"], IM["CenterOfMass.X"]]).astype(float),
            "parent_of": parent_of, "z_min": z_min, "z_max": z_max,
            "mean": IM["Mean"].to_numpy(float), "sum": IM["Sum"].to_numpy(float),
            "max": IM["Max"].to_numpy(float), "volume": IM["Volume"].to_numpy(float),
            "z": IM["CenterOfMass.Z"].to_numpy(float),
            "max_spots": max_spots_of(probe), "intronic": is_intronic(probe),
            "kept": set(), "study": study, "ring": ring, "nvox": IM["NumberOfVoxels"].to_numpy(float),
            "B": study["B"] if study is not None else np.nan, "b_spot": b_spot, "se_spot": se_spot,
            "means": str(probe.get("get_means", "False")) == "True",
            "extra_cols": probe_extra if method == DET_COORDS else {}, "abs_I": np.nan}
    # intensities used by the comparison with a reference population (relative comparison):
    # background-corrected when a background correction is on, raw otherwise
    if bg_correction:
        data["mean_n"] = data["mean"] - data["b_spot"]
        data["sum_n"] = data["sum"] - data["nvox"] * data["b_spot"]
    else:
        data["mean_n"], data["sum_n"] = data["mean"], data["sum"]

    if do_norm:
        # spots that serve as reference for the normalisation
        target = np.zeros(num, dtype=bool)
        for s, parents in parent_of.items():
            target[s - 1] = matches_norm_target(parents)
        data["is_ref"] = target if norm_against == NORM_ONLY else ~target
    return data


def best_points(spot_parameters, brightness=None):
    """
    Spots sorted by distance to the ideal (fraction = 1, probability = 1). Equal distances (always the case for
    objects given as coordinates, which have no probability yet) are ranked brightest first, then by label.
    """
    dist = {s: np.sqrt((1 - f) ** 2 + (1 - p) ** 2) for s, (f, p) in spot_parameters.items()}
    return sorted(spot_parameters, key=lambda s: (dist[s], 0.0 if brightness is None else -brightness[s - 1], s))


def normalise(probe, spot):
    """
    (Normalized mean, normalized sum) of a spot: its value divided by the average value of the
    reference spots (never the spot itself). In 3D mode, only reference spots whose center of
    mass lies in the Z range of the spot; the range grows by 0.5 on each side until at least
    one reference is found. Returns NaN if there is no reference at all.
    """
    i = spot - 1
    ref = probe["is_ref"].copy()
    ref[i] = False
    if norm_3d:
        z = probe["z"]
        with np.errstate(invalid="ignore"):
            gap = np.maximum(np.maximum(probe["z_min"][i] - z, z - probe["z_max"][i]), 0.0)
        gap = np.where(ref & ~np.isnan(z), gap, np.inf)
        nearest = gap.min()
        if not np.isfinite(nearest):
            return np.nan, np.nan
        chosen = gap <= np.ceil(nearest * 2) / 2
    else:
        chosen = ref
    if not chosen.any():
        return np.nan, np.nan
    ref_mean, ref_sum = probe["mean_n"][chosen].mean(), probe["sum_n"][chosen].mean()
    return (round(probe["mean_n"][i] / ref_mean, 2) if ref_mean > 0 else np.nan,
            round(probe["sum_n"][i] / ref_sum, 2) if ref_sum > 0 else np.nan)


def calibrate(probe):
    """
    Intensity of ONE molecule, measured in this image from the isolated molecules.
      - candidates: objects attributed to a cell that were NOT kept as transcription sites (the best
        'Max spots per cell' of every cell are the sites); so 'Max spots per cell' must be set
      - measured exactly like the sites: BgSub_Sum (same region, same background)
      - size check: sigma_xy of a 3D Gaussian fit compared with the PSF; an object is left out only if it is
        CONFIDENTLY larger / smaller than SIZE_MAX / SIZE_MIN PSF sigmas (a dim object has an uncertain size
        and is kept). Nothing is removed from the results, this only selects the reference molecules.
      - value = median of the retained objects; its error by bootstrap; stability curve: median when the
        faintest objects are progressively left out (a plateau means a value that does not depend on the
        detection threshold)
    """
    # every object located in a cell is a candidate; the size test below puts aside the objects that are clearly
    # larger than one molecule (clusters, transcription sites). Nothing is removed from the results.
    cand = np.array(sorted(probe["parent_of"]), dtype=int)
    if cand.size < CALIB_MIN_OBJECTS:
        raise ValueError(f"Absolute quantification ({probe['name']}): only {cand.size} objects found in cells "
                         f"(at least {CALIB_MIN_OBJECTS} needed to estimate the intensity of one molecule).")
    idx = cand - 1
    value = probe["sum"][idx] - probe["nvox"][idx] * probe["b_spot"][idx]
    info = optics_of(probe["channel"])
    status = np.array(["used"] * len(idx), dtype=object)
    sig = np.full(len(idx), np.nan)
    sig_se = np.full(len(idx), np.nan)
    if info["sigma_xy_vox"] is not None:
        sxy, sz = info["sigma_xy_vox"], info["sigma_z_vox"]
        rng = np.random.default_rng(0)
        checked = set(rng.choice(len(idx), size=min(len(idx), 3000), replace=False).tolist())
        for j, i in enumerate(idx):
            if j not in checked:
                status[j] = "used (size not checked)"
                continue
            f = optics.fit_spot(probe["img"], probe["com"][i], probe["b_spot"][i], (sxy, sz))
            sig[j], sig_se[j] = f["sigma_xy"], f["sigma_xy_se"]
            if f["ok"] and np.isfinite(f["sigma_xy_se"]):
                r, r_se = f["sigma_xy"] / sxy, f["sigma_xy_se"] / sxy
                if r - 2 * r_se > SIZE_MAX:
                    status[j] = "too big"
                elif r + 2 * r_se < SIZE_MIN:
                    status[j] = "too small"
            else:
                status[j] = "used (size undetermined)"
    else:
        status[:] = "used (size not checked: PSF unknown)"
    used = np.array([str(s).startswith("used") for s in status])
    values = value[used]
    if values.size < CALIB_MIN_OBJECTS:
        raise ValueError(f"Absolute quantification ({probe['name']}): only {values.size} isolated objects left after "
                         "the size check.")
    median = float(np.median(values))
    if not median > 0:
        raise ValueError(f"Absolute quantification ({probe['name']}): the isolated molecules have a median "
                         f"corrected intensity of {median:.2f} (not positive): check the background correction.")
    rng = np.random.default_rng(1)
    boot = np.median(rng.choice(values, size=(1000, values.size), replace=True), axis=1)
    se = float(boot.std())
    mode = np.nan
    if values.size >= 20:
        from scipy.stats import gaussian_kde
        grid = np.linspace(np.percentile(values, 1), np.percentile(values, 99), 400)
        mode = float(grid[np.argmax(gaussian_kde(values)(grid))])
    stability = []
    for q in range(0, 55, 5):
        keep = values >= np.percentile(values, q)
        stability.append((q, float(values[keep].min()), float(np.median(values[keep])), int(keep.sum())))
    counts, edges = np.histogram(values, bins=40)

    # average image of one molecule (background removed), 7 planes x 15 x 15 around each used object
    half = (3, 7, 7)
    acc = np.zeros([2 * h + 1 for h in half])
    n_acc = 0
    for j in np.nonzero(used)[0]:
        i = idx[j]
        c = np.round(probe["com"][i]).astype(int)
        sl = tuple(slice(ci - h, ci + h + 1) for ci, h in zip(c, half))
        if min(s.start for s in sl) < 0 or any(s.stop > d for s, d in zip(sl, probe["img"].shape)):
            continue
        acc += probe["img"][sl] - probe["b_spot"][i]
        n_acc += 1
    tag = f"s{probe['channel']}_{file_name}"
    if n_acc:
        tif.imwrite(f"{path}calibration_{tag}_mean_spot.tif", (acc / n_acc).astype(np.float32))
    table = pd.DataFrame({"Label": cand, "BgSub_Sum": value, "sigma_xy_fit_voxels": sig,
                          "sigma_xy_fit_se": sig_se, "status": status})
    save_excel(f"{path}calibration_{tag}.xlsx", table, critical=False)

    record = {"file": file_name, "probe": probe["name"], "channel": probe["channel"], "unit": abs_unit,
              "intensity": median, "se": se, "se_pct": 100 * se / median, "cv": float(values.std() / values.mean()),
              "mode": mode, "n_candidates": int(len(idx)), "n_used": int(values.size),
              "n_too_big": int((status == "too big").sum()), "n_too_small": int((status == "too small").sum()),
              "n_undetermined": int(sum(str(s).startswith("used (") for s in status)),
              "size_window_psf_sigmas": [SIZE_MIN, SIZE_MAX], "mean_spot_objects": n_acc,
              "psf": {k: info["widths"][k] for k in ("sigma_xy_nm", "sigma_z_nm", "fwhm_xy_nm", "fwhm_z_nm")}
              if info["widths"] else None,
              "background_method": bg_method, "stability": stability,
              "hist": {"edges": edges.tolist(), "counts": counts.tolist()}}
    with open(f"{path}calibration_{tag}.json", "w", encoding="utf-8") as fh:
        json.dump(_native(record), fh, indent=2)
    probe["calibration"] = record
    probe["abs_I"] = median
    print("calibration:" + json.dumps(_native(record)))       # read by the GUI


probes = [process_probe(n, p) for n, p in enumerate(channels["detect"])]


# ==============================================================================
# DATA TABLE: one row per spot (at least one row per cell)
# ==============================================================================
print("Putting information together")

# 1. spots kept for every cell (best ones first), then the background check of each image
kept_by = {}
for pop in pops:
    for cell in pop["ids"]:
        for probe in probes:
            ranking = best_points(probe["spot_proba"][pop["name"]][cell], probe["sum"])
            spots_kept = ranking if probe["max_spots"] is None else ranking[:probe["max_spots"]]
            kept_by[(pop["name"], cell, probe["name"])] = spots_kept
            probe["kept"].update(spots_kept)
for probe in probes:
    finalize_background(probe)
    if abs_calib and probe["intronic"]:
        print(f"{probe['name']}: intronic probe, no isolated molecules: no absolute quantification for this probe.")
    elif abs_calib:
        calibrate(probe)

# 2. columns: background correction (BgSub) first, then the absolute count, then the relative
# comparison (Normalized); raw values are always kept
def column_name(probe_name, field):
    if field.endswith("_count"):
        return f"{probe_name}_{field}"
    return f"{probe_name}_{field}" + ("" if field == "Volume" else "_intensity")


def fields_of(probe):
    """Columns of one Objects entry. The mean columns exist only if 'get objects intensities means' is ticked."""
    fields = []
    if probe["means"]:
        fields.append("Mean")
        if bg_correction:
            fields.append("BgSub_Mean")
        if do_norm:
            fields.append("Normalized_Mean")
    fields.append("Sum")
    if bg_correction:
        fields.append("BgSub_Sum")
    if do_abs and not probe["intronic"]:
        fields.append(f"{abs_unit}_count")
    if do_norm:
        fields.append("Normalized_Sum")
    return fields + ["Max", "Volume"]



def coordinates_column(pop):
    """Name of the column with the centre of the cells: 'ZYX_cell_coordinates' (prefixed by the name of the
    population when several populations ask for it)."""
    several = sum(1 for p in pops if p["coords"]) > 1
    return f"{pop['name']}_ZYX_cell_coordinates" if several else "ZYX_cell_coordinates"


def cell_centres(pop):
    """Centre of mass of every cell (pixels, sub-pixel), as the text 'z, y, x' with a decimal point."""
    mask = pop["mask"]
    ids = pop["ids"]
    centres = ndimage.center_of_mass(mask > 0, mask, ids)
    text = {}
    for cell, centre in zip(ids, centres):
        centre = tuple(centre)
        if len(centre) == 2:                                  # single plane: z = 0
            centre = (0.0,) + centre
        text[cell] = ", ".join(f"{float(v):.1f}" for v in centre)
    return text


cores = {}
centres = {}
for pop in pops:
    cores[f"{pop['name']}_labels"] = []
    if pop["coords"]:
        centres[pop["name"]] = cell_centres(pop)
        cores[coordinates_column(pop)] = []
for marker_name in types:
    cores[f"{marker_name}_typing"] = []
for prot_name in prot_fluo:
    cores[f"{prot_name}_fluorescence"] = []
for probe in probes:
    cores[f"{probe['name']}_number/cell"] = []
    cores[f"{probe['name']}_labels"] = []
    for f in fields_of(probe):
        cores[column_name(probe["name"], f)] = []
    for extra_name in probe["extra_cols"]:
        cores[f"{probe['name']}_{extra_name}"] = []
    if bg_correction:
        cores[f"{probe['name']}_bg_value"] = []

for pop in pops:
    for cell in pop["ids"]:
        kept = {probe["name"]: kept_by[(pop["name"], cell, probe["name"])] for probe in probes}
        n_rows = max([1] + [len(k) for k in kept.values()])

        for row in range(n_rows):
            first = row == 0
            for other in pops:
                cores[f"{other['name']}_labels"].append(cell if (first and other is pop) else "")
                if other["coords"]:
                    cores[coordinates_column(other)].append(centres[other["name"]][cell] if (first and other is pop) else "")
            for marker_name in types:
                cores[f"{marker_name}_typing"].append(
                    types[marker_name][pop["name"]].get(cell, "") if first and pop["name"] in types[marker_name] else "")
            for prot_name in prot_fluo:
                cores[f"{prot_name}_fluorescence"].append(prot_fluo[prot_name][pop["name"]][cell] if first else "")

            for probe in probes:
                spots = kept[probe["name"]]
                name = probe["name"]
                cores[f"{name}_number/cell"].append(len(spots) if first else "")
                has_spot = row < len(spots)
                values = {f: np.nan for f in fields_of(probe)}
                if has_spot:
                    spot = spots[row]
                    i = spot - 1
                    values.update({"Sum": round(probe["sum"][i], 2), "Max": round(probe["max"][i], 2),
                                   "Volume": round(probe["volume"][i], 2)})
                    if probe["means"]:
                        values["Mean"] = round(probe["mean"][i], 2)
                    if bg_correction:
                        if probe["means"]:
                            values["BgSub_Mean"] = round(probe["mean"][i] - probe["b_spot"][i], 2)
                        values["BgSub_Sum"] = round(probe["sum"][i] - probe["nvox"][i] * probe["b_spot"][i], 2)
                    if do_abs and not probe["intronic"]:
                        values[f"{abs_unit}_count"] = round(values["BgSub_Sum"] / probe["abs_I"], 2)
                    if do_norm:
                        nm, ns = normalise(probe, spot)
                        values["Normalized_Sum"] = ns
                        if probe["means"]:
                            values["Normalized_Mean"] = nm
                cores[f"{name}_labels"].append(spots[row] if has_spot else "")
                for f in fields_of(probe):
                    cores[column_name(name, f)].append(values[f])
                for extra_name, arr in probe["extra_cols"].items():
                    cores[f"{name}_{extra_name}"].append(round(float(arr[spots[row]]), 4) if has_spot else np.nan)
                if bg_correction:
                    cores[f"{name}_bg_value"].append(round(probe["b_spot"][i], 3) if has_spot else np.nan)

cores = pd.DataFrame(cores)
save_excel(f"{path}data_{file_name}.xlsx", cores)


# ==============================================================================
# COMPOSITE (Z, C, Y, X): cells | halos of group-2 cells | rejected spots, kept spots
# ==============================================================================
print("Creation of composite")

max_label = max([int(p["mask"].max()) for p in pops] + [p["num"] for p in probes])
if max_label <= np.iinfo(np.uint16).max:
    composite_dtype = np.uint16
else:
    composite_dtype = np.float32      # exact for integers up to 16.7 million; uint32 is refused by ImageJ tiffs
    print(f"More than 65535 labels ({max_label}): composite saved in float32.")

img = [pop["mask"].astype(composite_dtype) for pop in pops]


def add_halos(target, mask, cell_labels):
    """Draws the halo of each cell inside its bounding box only."""
    boxes = ndimage.find_objects(mask)
    height, width = mask.shape[1:]
    for label in cell_labels:
        box = boxes[label - 1] if label - 1 < len(boxes) else None
        if box is None:
            continue
        zs, ys, xs = box
        ys = slice(max(ys.start - HALO_ITERATIONS, 0), min(ys.stop + HALO_ITERATIONS, height))
        xs = slice(max(xs.start - HALO_ITERATIONS, 0), min(xs.stop + HALO_ITERATIONS, width))
        cell = mask[zs, ys, xs] == label
        halo = binary_dilation(cell, structure=struct_3d, iterations=HALO_ITERATIONS) & ~cell
        target[zs, ys, xs][halo] = HALO_VALUE


for type_group in channels["Type"]:
    halo_channel = np.zeros(pops[0]["mask"].shape, dtype=composite_dtype)
    if not type_group["associated_cells_channels"]:
        print(f"You might not have selected a cell population for marker {type_group['prot_name']}.")
    for cells_channel in type_group["associated_cells_channels"]:
        pop = pop_by_channel[str(cells_channel)]
        group2_cells = [c for c, t in types[type_group["prot_name"]][pop["name"]].items() if t == type_group["group2"]]
        add_halos(halo_channel, pop["mask"], group2_cells)
    img.append(halo_channel)

for probe in probes:
    inside = None       # spot voxels located in the cells of any population
    for pop in pops:
        merged = tif.imread(f"{path}merge_threshold_s{probe['channel']}c{pop['channel']}_{file_name}.tif")
        inside = merged if inside is None else np.maximum(inside, merged)
    lookup = np.zeros(probe["num"] + 1, dtype=bool)
    lookup[np.array(sorted(probe["kept"]), dtype=int)] = True
    is_kept = lookup[inside]
    img.append(np.where(~is_kept & (inside > 0), inside, 0).astype(composite_dtype))   # rejected spots
    img.append(np.where(is_kept, inside, 0).astype(composite_dtype))                   # kept spots

composite = np.stack(img, axis=1)       # (Z, C, Y, X)
tif_meta.write_like(f"{path}composite_{file_name}.tif", composite, base_tif, axes="ZCYX")


# ==============================================================================
# RECORD OF WHAT WAS DONE (to interpret the data table later)
# ==============================================================================
record = {
    "file": file_name,
    "date": datetime.datetime.now().isoformat(timespec="seconds"),
    "probe_channels": {p["name"]: p["channel"] for p in probes},
    "background_correction": {
        "method": bg_method,
        "margin_voxels": BG_MARGIN, "trim_percent": BG_TRIM, "depth_permutations": BG_DEPTH_PERMUTATIONS,
        "depth_alpha": BG_DEPTH_ALPHA, "depth_min_effect": BG_DEPTH_MIN_EFFECT,
        "ring_gap_pixels": RING_GAP if bg_ring else None, "ring_width_pixels": RING_WIDTH if bg_ring else None,
        "per_probe": {p["name"]: {k: p["bg_record"][k] for k in
                                  ("B", "n_cells", "spread", "depth_applied", "depth_p", "depth_effect",
                                   "typical_spot_mean", "error_pct", "err_cells_pct", "err_depth_pct")}
                      for p in probes if p.get("bg_record")}},
    "absolute_quantification": {
        "method": abs_mode, "unit": abs_unit if do_abs else None,
        "intensity_of_one_molecule": {p["name"]: p["abs_I"] for p in probes if not p["intronic"]} if do_abs else None,
        "formula": "BgSub_Sum / intensity_of_one_molecule" if do_abs else None,
        "calibration": {p["name"]: {k: v for k, v in p["calibration"].items() if k not in ("hist", "stability")}
                        for p in probes if p.get("calibration")} or None},
    "optics": {p["name"]: {"acquisition": {k: v for k, v in optics_of(p["channel"])["acq"].items()},
                           "pixel_nm": optics_of(p["channel"])["pixel_nm"], "step_nm": optics_of(p["channel"])["step_nm"],
                           "psf": optics_of(p["channel"])["widths"],
                           "sigma_voxels": [optics_of(p["channel"])["sigma_xy_vox"], optics_of(p["channel"])["sigma_z_vox"]]}
               for p in probes},
    "relative_comparison": {
        "method": "relative to a population" if do_norm else "none",
        "norm_against": norm_against, "norm_3d": norm_3d, "population": norm_pop, "cell_type": norm_type,
        "computed_on": "background-corrected intensities" if bg_correction else "raw intensities"},
    "detection": {p["name"]: {"method": channels["detect"][i].get("detection", DET_MODEL),
                              "model": channels["detect"][i].get("model_path"),
                              "smfish_type": SMFISH_INTRONIC if p["intronic"] else SMFISH_EXONIC,
                              "spotiflow_prob_thresh": channels["detect"][i].get("spotiflow_prob_thresh")
                              if channels["detect"][i].get("detection", DET_MODEL) == DET_SPOTIFLOW else None,
                              "aperture_sigmas": channels["detect"][i].get("aperture_sigmas", APERTURE_SIGMAS)
                              if channels["detect"][i].get("detection", DET_MODEL) in (DET_COORDS, DET_SPOTIFLOW) else None}
                  for i, p in enumerate(probes)},
    "spots": {"probability_threshold": SPOT_THRESHOLD, "min_fraction_in_cell": MIN_CELL_FRACTION,
              "max_spots_per_cell": {p["name"]: p["max_spots"] for p in probes}},
    "cell_types": {g["prot_name"]: {"group1": g["group1"], "group2": g["group2"],
                                    "populations": [pop_by_channel[str(c)]["name"] for c in g["associated_cells_channels"]
                                                    if str(c) in pop_by_channel]}
                   for g in channels["Type"]},
    "halo": {"iterations": HALO_ITERATIONS, "value": HALO_VALUE, "in_plane_only": True,
             "note": "composite: one halo channel per cell type marker (after the cell channels), drawn around the "
                     "cells of group2; the viewer redraws it when the type of a cell is changed"},
    "pixel_size_um": _voxel.get("pixel"), "z_step_um": _voxel.get("depth")}
with open(f"{path}analysis_parameters_{file_name}.json", "w", encoding="utf-8") as fh:
    json.dump(_native(record), fh, indent=2)
print("Analysis finished")

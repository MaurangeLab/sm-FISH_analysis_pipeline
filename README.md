# [PIPELINE NAME]

**Single-cell analysis of smFISH in 3D confocal stacks — from a Zeiss image to one table per cell, with tools to check, correct and explore the results.**

<p align="center">
  <img src="docs/overview.png" alt="Overview of the pipeline" width="900">
</p>

[PIPELINE NAME] takes 3D confocal stacks (Zeiss `.czi` or `.tif`), segments the cells, detects the smFISH spots, measures them, corrects them for the local background, converts them into relative or absolute quantities, classifies the cells with a protein marker, and writes everything in tables where **each row is a spot and each block of rows is a cell**.

It is made of:

- an **analysis pipeline** (`Newmain.py`), which can run without any interface;
- a **desktop application** (`GUI4-globnorm.py`) with four tabs: *Analysis*, *Viewer*, *Data Explorer* and *Spotiflow training*;
- a few **child scripts** that run in their own conda environments, so that tools with incompatible requirements (Cellpose 2, 3 and 4, TensorFlow/EpySeg, PyTorch/Spotiflow) live together.

> Status: used in the lab, under development. There is no version number, installer or automatic test suite yet. See [Known limits](#known-limits).

---

## Contents

1. [What it does](#what-it-does)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [User guide](#user-guide)
5. [Inputs and outputs](#inputs-and-outputs)
6. [Methods](#methods)
7. [Running without the interface](#running-without-the-interface)
8. [Architecture](#architecture)
9. [Known limits](#known-limits)
10. [Citation, licence and credits](#citation-licence-and-credits)

---

## What it does

| Step | What happens | Tools |
|---|---|---|
| **Conversion** | A `.czi` is converted into an ImageJ `.tif` (Z, C, Y, X) that keeps the pixel size, the z step and the whole Zen acquisition metadata. | `czifile`, `aicspylibczi` |
| **Cell segmentation** | 3D masks of the cells, then optional shrinking and minimum size. | Cellpose 2, 3 or 4; Weka (Fiji) |
| **Cell types** | The fluorescence of a protein marker splits the cells into two groups (Gaussian mixture). | scikit-learn |
| **Spot / object detection** | Detection of the smFISH spots (or of larger objects) in 3D. | EpySeg, Spotiflow, Weka (Fiji), or a file of coordinates |
| **Measurements** | Intensities and volume of every spot, local background, background-subtracted values. | — |
| **Quantification** | Relative normalisation to reference spots, and/or absolute count of molecules. | — |
| **Per-cell table** | One table with the cells, their types, their spots and every measurement. | Excel |
| **Optional exports** | 3D coordinates of the cells, one crop (tif) per cell, a composite image with the masks, halos and spots. | — |
| **Check and correct** | Look at the result on the image, validate or reject spots, move a spot to another cell, change a cell type, and rebuild the table. | *Viewer* |
| **Explore** | Filters, distributions, proportions, copy of means by sample. | *Data Explorer* |
| **Train** | Refine the pretrained 3D smFISH Spotiflow model on your own annotated crops. | *Spotiflow training* |

---

## Installation

### Requirements

- **conda** (Anaconda or Miniconda), on Windows, macOS or Linux.
- A recent Python is **not** needed on its own: the setup script creates the environments.
- A GPU is optional. Cellpose 3/4 and Spotiflow use it when PyTorch can see one. TensorFlow (EpySeg) does not use the GPU natively on Windows; it runs on the CPU unless installed under WSL2.
- **Fiji** with the *Trainable Weka Segmentation* plugin, only if you want to use Weka models.

### Create the environments

From the folder that holds the scripts:

```bash
python setup_environments.py
```

The script only uses the Python standard library, finds your conda, accepts the conda terms of service if needed, and creates what is missing. Options:

| Option | Effect |
|---|---|
| `--check` | Only reports which environments exist and which packages are missing. |
| `--only NAME [NAME ...]` | Creates only these environments. |
| `--force` | Recreates the environments. |
| `--device auto\|cpu\|cuda` | PyTorch build for Cellpose 3/4 and Spotiflow. `auto` takes the GPU build if `nvidia-smi` is found, otherwise the CPU one. |
| `--yes` | Does not ask for confirmation. |

| Environment | Python | Used for |
|---|---|---|
| `guienv` | 3.11 | The application (PyQt6, pandas, matplotlib, tifffile…). |
| `spots_analysis` | — | The analysis itself (`Newmain.py`), czi conversion, Weka post-processing. |
| `segment` | 3.10 | Cellpose **2** (2.2.3): models trained with Cellpose 2. |
| `cellpose3` | 3.10 | Cellpose **3**. |
| `cellpose4` | 3.10 | Cellpose **4** (Cellpose-SAM). |
| `chinmospots` | 3.10 | EpySeg (TensorFlow): detection of objects with an EpySeg model. |
| `spotiflow` | — | Spotiflow: detection and training. |

At the end the script prints how to start the application.

### Start the application

```bash
conda activate guienv
python GUI4-globnorm.py
```

Keep all the scripts in the same folder: the application finds the environments and the child scripts from there.

---

## Quick start

1. Open the **Analysis** tab and drop one or several images (`.czi` or `.tif`) in the files panel. Each image is analysed in its own folder.
2. For each channel, choose a **role** (*Cells*, *Cell type marker*, *Objects*) and fill its parameters. A model is chosen in the **Models** page (see below).
3. Press **Run**. The log shows the progress; the plots (background, distributions) appear next to it.
4. Open the **Viewer** tab, load the analysis folder, check the spots and the cells, correct what needs it, and press **Compile changes**.
5. Open the **Data Explorer**, load the data tables, filter, plot and copy the results.

> A small example dataset is planned: `[ADD LINK OR FOLDER]`.

---

## User guide

### Analysis tab

**Channel roles**

| Role | What it is | Main parameters |
|---|---|---|
| **Cells** | The channel used to segment the cells. | Name of the population, model, shrink factor, minimum size, *Get cells 3D coordinates*, *Export cell crops*. |
| **Cell type marker** | A protein channel that splits the cells in two groups. | Protein name, names of group 1 and 2, which group is marked, cells it applies to. |
| **Objects** | A smFISH channel (spots or larger objects). | Name, type of probe, detection method, background and quantification options. |

Parameters can be saved and loaded as **presets**.

**Models page.** Models are listed by source; drop a model (file or folder) in its section.

| Source | Used for | Notes |
|---|---|---|
| **Cellpose** | Cells | Each model has a version (2, 3 or 4) that decides which environment runs it. Models made before Cellpose 3 are version 2 by default. |
| **EpySeg** | Objects | Detection with an EpySeg model. |
| **Spotiflow** | Objects | A model folder, or the name of a pretrained model such as `smfish_3d`. Optional probability threshold. |
| **Weka (Fiji)** | Cells and objects | A `.model` file saved from Fiji's Trainable Weka Segmentation. Give the location of Fiji (the window checks the launcher and the plugin). Each model has a mode (2D plane by plane, or 3D) and the number of the class that is the object. |
| **Coordinates file** | Objects | A table of coordinates (z, y, x) instead of a detector. |

**Optics.** Spotiflow apertures and the PSF use the acquisition metadata of the image: numerical aperture, wavelengths, pinhole, refractive index, pixel size and z step. They are read from the image. If they cannot be found the analysis stops and tells you what is missing (*optical parameters not found*): fill them in **Advanced › Optics**, or run the analysis on the original Zeiss export. All the tif files the pipeline writes keep this metadata.

**Per-cell crops.** Tick *Export cell crops* in the cell parameters. A small window sets the margin (pixels or µm; µm needs a known pixel size), one 3D stack per cell or one 2D image per slice, the channels of the base file, the extra planes before and after (1 by default), and whether the image borders are completed with zeros. Files are written to `<cells name>_crops/` as `<image>_cell<n>.tif` (or `<image>_cell<n>_z<k>.tif`). Pixel size, z step and acquisition metadata are kept.

### Viewer tab

The viewer shows the composite image of an analysis folder and its data table.

- **Navigation:** wheel to zoom, drag to move, plane slider, per-channel contrast and opacity, *Fit*, *1:1*, *Save view*.
- **Zoom cell** (key **Z**): zooms by an adjustable factor (4× by default) on the selected cell or spot, or the centre of the image if nothing is selected; never goes past the image edge.
- **Cell mode:** information on a cell, its type for each marker, its spots with their data columns, and a *Belongs to cell* control for each spot.
- **Spot mode:** click a spot to see its data columns, validate or reject it, change the cell it belongs to.
- **Changes** are saved at once in a journal outside your analysis folders (`~/.pipeline_viewer/`), so nothing is lost if you close the application.
- **Compile changes** applies them: it writes the data table and rebuilds the composite (halos, spot channels). It also **recomputes** the background-subtracted values, the absolute counts, the **normalised values** (the mean of the reference spots is computed again with the current cell types and spots, and every normalised value is redone, including those of spots you did not touch) and the **spot counts** of every cell. A backup of the data table is kept in the application folder.
- Drag and drop a folder to load it. A *Loading data…* message is shown while it opens.

### Data Explorer tab

Loads several data tables (one per image) and compares them.

- Filters on any column, on the source file (only this file, or all except), and on cell-level or spot-level values.
- Counts and proportions use **one value per cell** for cell-level columns and one per spot otherwise, so cells with several spots are not counted several times.
- Distributions and proportion plots, with the file name written on the figure.
- *Copy means by sample* (a sample is a source file) to paste into a spreadsheet or a statistics program.

### Spotiflow training tab

Refines the pretrained 3D smFISH Spotiflow model on your own spots. It works by **session**.

1. **Choose a session folder.** `train/`, `val/` and `models/` are created in it.
2. **Open an image** (`.czi` or `.tif`) and choose the smFISH channel.
3. **Crop:** drag a rectangle on the image, choose the planes, and add it to `train/` or to `val/`. Use different crops for the two sets.
4. **Annotate:** left click adds a spot in the current plane, right click removes the nearest one, the wheel changes plane, Ctrl + wheel zooms, the middle button moves the image. Spots of the neighbouring planes are shown in yellow. Every click is saved at once as `<crop>.csv` (columns `z, y, x`) next to `<crop>.tif`.
5. **Train:** give a model name and a number of epochs (100 by default) and press *Train model*. It starts from the pretrained `smfish_3d` model.
6. **Result:** the model is saved in `models/<name>/`, added to the Spotiflow models of the Models page, and the crops are shown with the spots found by the new model (orange rings).

Spotiflow already augments the data during training, so an extra augmentation of the annotated crops is not needed. Fewer than a hundred well-chosen spots can already give a good model when starting from the pretrained one.

---

## Inputs and outputs

### Inputs

- `.czi` (Zeiss) or `.tif` (ImageJ), 3D with several channels, ordered (Z, C, Y, X).
- Models (Cellpose, EpySeg, Spotiflow, Weka) chosen in the Models page.
- For the *Coordinates file* method: a table with the columns `z, y, x`.

### Outputs

Each image is analysed in its own folder. The main files are:

| File | Content |
|---|---|
| `data_<image>.xlsx` | **The main table** (see below). |
| `<image>-<channel>intensity-measurements.xlsx` | Raw measurements of every detected spot, valid or not: intensities, volume, centre of mass, **background**, background-subtracted values, Z extent, parent cells. |
| `composite_<image>.tif` | Hyperstack for the Viewer: cell masks, one halo channel per cell-type marker, and for each probe the rejected and the kept spots. |
| `analysis_parameters_<image>.json` | The parameters of the analysis, read back by the Viewer. |
| `background_*.xlsx`, `calibration_*.xlsx` | Background study and calibration tables. The background table has the columns `population, cell, z_center, voxels, mean, median, var`. |
| `<cells name>_crops/` | Per-cell crops (optional). |
| `spotiflow_results/` | Spotiflow detections (`z, y, x, prob, intens`) and the model and threshold used. |
| `masks*`, `shrinked*`, `detected*`, … | Intermediate images; they are reused when nothing changed. |

### The data table

**One row per spot.** Values that belong to a cell are written **only on the first row of the cell's block**; the other rows of the block are empty. The main columns are:

| Column | Meaning |
|---|---|
| `<population>_labels` | Cell number. |
| `ZYX_cell_coordinates` | Centre of mass of the cell in pixels, written `z, y, x` (optional). |
| `<marker>_typing` | Type of the cell (group 1 or 2) for this marker. |
| `<protein>_fluorescence` | Fluorescence of the marker in the cell. |
| `<probe>_labels` | Spot number. |
| `<probe>_number/cell` | Number of spots of the cell (first row of the block). |
| `<probe>_Mean_intensity`, `_Sum_intensity`, `_Max_intensity`, `_Volume` | Raw measurements of the spot. |
| `<probe>_BgSub_Mean_intensity`, `_BgSub_Sum_intensity`, `<probe>_bg_value` | Background-subtracted values and the background used. |
| `<probe>_Normalized_Mean_intensity`, `_Normalized_Sum_intensity` | Relative values (if a normalisation was chosen). |
| `<probe>_<unit>_count` | Absolute count (if the intensity of one molecule is given). |

---

## Methods

**Background.** For every spot a local background is estimated around it. A background study over the cells of the image gives a per-plane trend, using a trimmed mean (1 %) and the median across cells; the table of the study can be saved from the background plot. Background-subtracted values are `Sum − voxels × background` and `Mean − background`.

**Absolute count.** The background-subtracted sum of a spot is divided by the intensity of one molecule.

**Relative normalisation.** The reference spots are those that belong to the cells of a chosen type (and, if you wish, population), or all the others. The normalised value of a spot is its background-subtracted value divided by the mean of the reference spots, **excluding the spot itself**. In 3D mode, only the reference spots at the nearest depth are used. The mean is computed per sample (per image).

**Cell types.** The fluorescence of a marker in each cell is separated into two groups by a Gaussian mixture; you name the groups and say which one is marked.

**Cell–spot assignment.** A spot belongs to a cell when enough of it lies inside the mask; spots that overlap several cells have several parent cells.

**Optics.** The PSF and the Spotiflow apertures come from the numerical aperture, the wavelengths, the pinhole, the refractive index and the pixel size and z step of the image.

> Add here the exact formulas, thresholds and references you want to cite in a publication.

---

## Running without the interface

`Newmain.py` can be run on its own, in the `spots_analysis` environment:

```bash
python Newmain.py . '<parameters as JSON>' <analysis folder>/
```

The folder must hold the image (`<image>.tif`, or the `.czi` to convert). The JSON holds the list of channels with their roles and parameters, the optional background, normalisation and absolute-quantification settings, and the Python executables of the environments (`"envs"`). The simplest way to get a valid JSON is to set the parameters in the application: the file `analysis_parameters_<image>.json` written in the analysis folder records them.

---

## Architecture

```
GUI4-globnorm.py              The application (tabs: Analysis, Viewer, Data Explorer, Spotiflow training)
Newmain.py                    The analysis pipeline (can run alone)
setup_environments.py         Creates and checks the conda environments
optics.py                     Reads the acquisition metadata; PSF and apertures
tif_meta.py                   Keeps pixel size, z step and Zen metadata in every tif written; czi conversion
segmentation_cellpose-Epyseg.py   Cell segmentation with Cellpose 2/3/4, shrinking, minimum size
segmentation_weka.py          Weka (Fiji) segmentation of cells or detection of objects
fiji_tools.py                 Finds Fiji, checks the Weka plugin, runs it without interface
spot_segmentation.py          Object detection with an EpySeg model
spotiflow_detection.py        Spotiflow detection
train_spotiflow.py            Training of a Spotiflow model (started by the training tab)
```

The application runs in `guienv`. It starts `Newmain.py` as a separate process; `Newmain.py` starts each child script with the Python of the right environment, so a Cellpose 3 model never meets TensorFlow. Scripts exchange **files** and text on the standard output; progress bars are shown on one line in the log. The Viewer journal lives in `~/.pipeline_viewer/`, outside the analysis folders.

---

## Known limits

- **Multi-probe composite:** the Viewer rebuilds the spot channels of the first probe only.
- **Spots validated by hand** are recomputed from the measurements file. An analysis made with an older version lacks the background columns and must be run again once; the Viewer tells you.
- **Crops:** masking the other cells in a crop is not implemented.
- **Weka:** applied by Fiji without interface; the mode 3D has had little testing.
- **EpySeg for cells** is not available yet.
- **Not implemented yet:** time-lapse, nuclei (DAPI), threshold-free detection.
- No automated test suite and no installer yet.

---

## Citation, licence and credits

**Citation.** If you use this software, please cite `[AUTHORS, TITLE, YEAR, LINK / DOI]`. A `CITATION.cff` file can be added to the repository so that GitHub shows a *Cite this repository* button.

**Licence.** `[CHOOSE A LICENCE AND ADD A LICENSE FILE]`

**Contact.** `[NAME, E-MAIL]`

**Built on** (please also cite them):

- **Cellpose** — Stringer et al., *Nature Methods* 2021; Pachitariu & Stringer, *Nature Methods* 2022; Stringer & Pachitariu, Cellpose3, 2025; Cellpose 4 (Cellpose-SAM), 2025.
- **Spotiflow** — Dominguez Mantes et al., *Nature Methods* 2025.
- **EpySeg** — Aigouy et al., *Development* 2020.
- **Fiji** — Schindelin et al., *Nature Methods* 2012; **Trainable Weka Segmentation** — Arganda-Carreras et al., *Bioinformatics* 2017.
- scikit-learn, scikit-image, SciPy, NumPy, pandas, tifffile, PyQt6, matplotlib.

*(Check the exact references and years before publishing.)*

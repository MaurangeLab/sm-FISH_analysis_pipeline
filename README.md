
# sm-FISH_analysis_pipeline
## Introduction

**This pipeline is an easy to use tool to analyse 3D stacks obtained from immunostaining combined with sm-FISH experiments.**

<img width="932" height="569" alt="Capture d&#39;écran 2026-11-23 153345" src="https://github.com/user-attachments/assets/b2302d25-2da6-48c8-a253-18bb1f2e6c3d" />

This pipeline is able to segment cells (using mainly Cellpose), determine their types based on a cell type marker, segment smFISH spots (Spotiflow, Epyseg), and perform measurements on these cells and spots. For each analyzed stack, it returns a folder containing numerous sta

To try it with an example stack and pre-trained models, see Tutorial folder.

## Installation

- Download [Anaconda](https://www.anaconda.com/download/success?reg=skipped&path=distribution)
- Open Anaconda navigator (search it in the research bar of the pc)
- Open Spyder from Navigator
- Drag and drop setup_environments.py from this repository in Spyder, then run it and wait until it is finished (roughly 20min)
-> The pipeline is ready to use

## How to use it ?
### How to use the pipeline ?

- Drag and drop GUI.py in Spyder.
  
- In the menu bar (File, Edit, Search...), click "Console", then "New console in environment", then "Conda : guienv". Run the GUI (Graphical User Interface).
  
- Drag and drop your .czi or .tif images in the files to analyze section and let the intuitive interface guide you : Leaving your mouse on just about any clickable object of the interface will make a speech bubble appear to explain what it is and how to use it.

### How to get your own AI models ?

Segmentation and spot detection by AI is the core of this pipeline, therefore, you might have to train you own AI models. 

For cell segmentation, you can use segmentation models from Cellpose 2, 3 or 4 (as well as Weka, which is not tested yet). Using Cellpose is very intuitive and the documentation about it is very complete. Anyway, [here](https://www.youtube.com/watch?v=5qANHWoubZU) is a tutorial of how to train a model from Cellpose 2, even though it might not be exactly the same process for Cellpose 3 and 4.


To train an adapted smFISH spots detection model with Epyseg, please refer to the following article and GitHub : 

Aigouy et al., 2020, Development. ; https://github.com/baigouy/EPySeg

To train an adapted smFISH spots detection model with Spotiflow, the graphical interface integrates a tool to make the training easy. Here is some documentation about Spotiflow :

https://www.nature.com/articles/s41592-025-02662-x ; https://weigertlab.org/spotiflow/

Once you trained them, put them in the right "Model" section of the GUI. Cellpose models should be single files with no extension, Epyseg ones should be .h5 files and Spotiflow models are folders containing some .yaml and .pt files as well a folder.

### How to indicate the analysis you want to perform on each channel ?

After putting your images in the files to analyze section, you need to tell the pipeline what you want to do with those images. To do so, indicate the kind of analysis you want to perform on each channel.

The "Cells" analysis will segment the cells using the model you chose. You can precise limit size, shrinking parameter (to distinguish them if needed), as well as computation of coordinates based on their centers of masses. You can also indicate crop settings to produce a 2D/3D crop for each cell.

The "Objects" analysis will segment the biological objects (mostly smFISH spots) using the model you chose. As Epyseg and Spotiflow models are based on probability, you can indicate a probability threshold below which the object is not considered. If you use smFISH, you can precise the kind of probe you use : intronic or exonic probe. Choosing intronic probe will rank every spot based their probability to be a real spot as well as volume in the presumed parent cell and the keep up to the best two (two alleles, two transcription sites at most). If you use a Spotiflow model, the PSF of each spot is determined from the metadata contained in your image and the pixels considered as sufficiently close to the sub-pixel center of the resulting ellipsoid is kept inside the spot.
After segmentation, measurements are performed on each spot (integrated intensity, volume based on the metadata, coordinates), although Spotiflow automatically returns a calculated intensity value.
However, you might need to normalize these intensities (against the intensity of a single mRNA for example), to obtain absolute (number of RNA in a transcription site) or relative (comparison between two cells types) values. You will find information on how to normalize your data below this section.

The "Cell type marker" analysis is dedicated to identify and distinguish the cell types that are present inside a population of cells. It will measured the integrated intensity of a cell type marker in each cell of the indicated cell population. To distinguish them, it uses the Gaussian Mixture Library, which uses gaussian mixture models to separate the two gaussians present in the distribution of the intensities measured before, as follows. It then attributes the cell types based on the probability of a cell to be in one gaussian or in the other.
<img width="856" height="402" alt="Capture d&#39;écran 2026-11-25 113025" src="https://github.com/user-attachments/assets/3be48d08-7d8f-4453-95ba-8f02ed080193" />

The "Protein of interest" analysis measures the integrated intensity of a molecule inside each cell. It can be used to measure protein amount.

## What to expect from the analysis ?

This pipeline produces several files, named after the following convention :
file info + base file name + .tif/.xlsx 
With that in mind, the files produced and the information they contain, in production order, are the following :

name : base file name (ex: yw_40X_21-04.czi)

content : Original stack from the microscope, with no modifications. This one is not produced by the pipeline, but is the first file you need to give to the code to start the first analysis. 

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : base file name but tif file (ex: yw_40X_21-04.tif)

content : Duplicate of original microscope stack. This one is produced by the pipeline, and used to start analysis. It is put in a new folder which also has the nale of the original microscope stack. The name of this file will be refered to as "file name" and used to name every other file produced.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : masks + file name

content : raw cells segmentation result.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : shrinked + file name 

content : shrinked segmentation result, to avoid detecting spots from adjacent cells. Will be produced if if you did not ask for any modification of the raw cells segmentation result, to ensure keeping it raw.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : detected + file name 

content : Produced only if you used Epyseg. 3D probability map, where every pixel has a value between 0 and 1 to be part of a smFISH spot.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : chinmo_threshold_ + file name + -lbl

content : Now, every spot has a specific value ("label").

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : merge_threshold_ + file name

content : Fusion of the precedent file and shrinked file which allows to see points only in the cells. It is used to determine the volume of the spot that is inside the cell, comparing with the precedent file.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : file name + intensity-measurements.xlsx

content : .xlsx (excel) file containing every spot measurements made during the corresponding phase of the process (Label, Sum, Max, NumberOfVoxels, Volume, Centers Of Mass X, Y, and Z)

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : composite_ + file name 

content : A stack allowing you to apprehend the analysis results graphically. When opening it, you might have to "Make Composite" with imageJ, and then use Brightness and Contrast. To know more about how to use it, please go to the "Results" part of Tutorial.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : data_ + file name

content : Excel file every line is for a spot, and every block of lines is one cell. Contains information on each spot and each cell.


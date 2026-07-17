# sm-FISH_analysis_pipeline
This pipeline is meant to analyse images taken from immunostaining combined sm-FISH experiments. It will put in relation cell type, gene transcription, and gene expression data.
The spot detection model has been trained with Epyseg (Aigouy et Prud'Homme, 2020).

To install the pipeline on a new pc follow these steps :
- Download Anaconda at https://www.anaconda.com/download (Download now, skip registration)
- Open Anaconda navigator (search it in the research bar of the pc)
- Open Spyder from Navigator
- Drag and drop setup_env.py, then run it, wait until it finished preparing the right environments (~10min)
- Meanwhile, create a folder in Documents directory, named Repertoire (no accents, nothing just Repertoire)
- Create in Repertoire a folder named "Model" where you will put your models
-> The pipeline is ready to use

How to use the pipeline ?
- Drag and drop every python file from this GitHub in Spyder.
- In the tool bar, click "Console", then "New console in environment", then "Conda : spots_analysis". It launches a new console in spots_analysis environment.
- Adjust your parameters in Main-Epyseg : mode_all_files if there are several images to analyze, mode_new if the file(s) is (are) new (automatically puts seg and
detect on), seg if you want segmentation, detect if you want detection of the spots. Make sure the channels you indicate are well selected.
- Put the image(s) in the Repertoire folder
- Run Main-Epyseg.

This pipeline produces several files, named after the following convention :
file info + base file name + .tif/.xlsx 
With that in mind the files produced and the information they contain, in production order, are the following :

name : base file name (ex: yw_40X_21-04.czi)

content : Base image from the microscope, with no modifications. This one is not produced by the pipeline, but is the first file you need to give to the code to start analysis. It must contain at least those three channels : segmentation marker (Miranda), probe, and cell type protein (Asense). 

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : base file name but tif file (ex: yw_40X_21-04.tif)

content : Duplicate of original microscope image. This one is produced by the pipeline, and used to start analysis. It must contain at least those three channels : segmentation marker (Miranda), probe, and cell type protein (Asense). The name of this file will be refered to as "file name" and used to name every other file produced.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : masks_ + file name

content : raw segmentation result.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : shrinked_ + file name 

content : shrinked segmentation result, to avoid detecting spots from adjacent cells.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : detected_ + file name 

content : 3D probability map, where every pixel has a value between 0 and 1 to be part of a smFISH spot.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : merge_ + file name

content : Fusion between detected_ and shrinked_, which allows to see probability map only in detected cells.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : chinmo_threshold_ + file name + -lbl

content : File created after applying analysis of connected components on chinmo_threshold. Now, every point has a specific value ("label"). This file is created by yourself.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : merge_threshold_ + file name

content : Fusion of the precedent file and shrinked_ which allows to see points only in the cells. It is used to determine the volume of the spot that is inside the cell, comparing with the precedent file.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : file name + -intensity-measurements

content : .xlsx (excel) file containing every spot measurements made during the corresponding phase of the process (Label, Mean, Max, Min, NumberOfVoxels, Volume, Centers Of Mass X, Y, and Z)

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : composite_ + file name 

content : May be the most useful file. It is a 4 channels image allowing you to apprehend the analysis results graphically. In channels order, you can see the detected cells, types (green halo for type 2), detected but non kept spots (spots that are detected in the wrong cell), and kept spots.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : data_ + file name

content : Excel file containing every cell, their type, spots, spot mean intensity, volume, number, and protei expression. Last row are means of every column.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : Spot_numbers + file name

content : representative stats (percentages, means) on those data.




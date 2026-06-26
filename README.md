# sm-FISH_analysis_pipeline
This pipeline is meant to analyse images taken from immunostaining combined sm-FISH experiments. It will put in relation cell type, gene transcription, and gene expression data.
The spot detection model has been trained with Epyseg (Aigouy et Prud'Homme, 2020).

To use these codes, you should use Spyder from anaconda, and you need the right environments. Here is how you can do :
- In anaconda navigator, open anaconda prompt.
- Create the first environment, "spots_analysis" with "conda create --name spots_analysis python==3.10"
- Activate the environment : conda activate spots_analysis
- Add kernel, which will allow your python console to work : "pip install spyder-kernels==3.14"
- Add tifffile : "pip install tifffile", do so with openpyxl, matplotlib and pandas
- Add specific version of numpy : "pip install numpy==1.26.4"
This environment is finished. Quit it by "conda deactivate"

Do the same thing with the segment environment. It needs to run on python 3.13. 
It also needs spyder-kernels 3.14, cellpose 2.2.3 specifically, matplotlib, numpy 2.4.6, and tifffile.

Do the same thing with the chinmospots environment. It needs to run on python 3.10.
It also needs epyseg, fishdist, matplotlib, numpy 1.26.3, pandas, and tifffile.

This pipeline produces several files, named after the following convention :
file info + base file name + .tif 
With that in mind the files produced and the information they contain, in production order, are the following :

name : base file name-1 (ex: yw_40X_21-04-1)
content : Duplicate of original smFISH image. This one is not produced by the pipeline, but is the first file you need to give to the code to start analysis. It must contain 4 channels (in order): DAPI, segmentation marker (Miranda), probe, and cell type protein (Asense). The name of this file will be refered to as "file name" and used to name every other file produced.

name : masks_ + file name
content : raw segmentation result.

name : shrinked_ + file name 
content : shrinked segmentation result, to avoid detecting spots from adjacent cells.

name : asense_ + file name 
content : Significant asense fluorescence, after thresholding. It is used to assess the type based on if a cell exhibits significant fluorescence or not.

name : detected_ + file name 
content : 3D probability map, where every pixel has a value between 0 and 1 to be part of a smFISH spot.

name : merge_ + file name 
content : Fusion between detected_ and shrinked_, which allows to see probability map only in detected cells.

name : chinmo_threshold_ + file name
content : detected_ file made binary after thresholding. "Chinmo" is because I built this pipeline working on the chinmo gene

name : chinmo_threshold_ + file name + -lbl
content : File created after applying analysis of connected components on chinmo_threshold. Now, every point has a specific value ("label"). This file is created by yourself.

name : merge_threshold_ + file name
content : Fusion of the precedent file and shrinked_ which allows to see points only in the cells. It is used to determine the volume of the spot that is inside the cell, comparing with the precedent file.

name : file name + -1-intensity-measurements
content : CSV (excel) file containing every spot measurements made during the corresponding phase of the process (Label, Mean, StdDev, Max, Min, Median, Mode, NumberOfVoxels, Volume, Centers Of Mass X, Y, and Z)

name : composite_ + file name 
content : May be the most useful file. It is a 4 channels image allowing you to apprehend the analysis results graphically. In channels order, you can see the detected cells, types (green halo for type 2), detected but non kept spots (spots that are detected in the wrong cell), and kept spots.

name : data_ + file name
content : Excel file containing every cell, their type, spots, spot mean intensity, volume, number, and protei expression. Last row are means of every column.

name : Spot_numbers + file name
content : representative stats (percentages, means) on those data.




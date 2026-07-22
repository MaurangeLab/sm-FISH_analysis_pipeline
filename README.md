# sm-FISH_analysis_pipeline
This pipeline is an easy-to-use mean to analyse 3D stacks taken from immunostaining combined sm-FISH experiments. It can put in relation cell type, gene transcription, and gene expression data. It uses AI to recognize cells and sm-FISH spots, then estimates type of a cell based on the assumption that your two groups show differences in type marker fluorescence.
The sm-FISH spots detection model has been trained with Epyseg (Aigouy et Prud'Homme, 2020).
The cell segmentation model has been trained from a nuclei model in Cellpose 2.

To install the pipeline on a new pc, follow these steps :
- Download Anaconda at https://www.anaconda.com/download (Download now, skip registration)
- Open Anaconda navigator (search it in the research bar of the pc)
- Open Spyder from Navigator
- Create a directory in Documents where you will put every python file from this GitHub. Let's say you called it "Pipeline".
- Drag and drop setup_env.py from Pipeline to Spyder, then run it, wait until it finished preparing the right environments (~10min).
- Meanwhile, create a folder in Documents directory, named Repertoire (no accents, nothing just Repertoire).
- Create in Repertoire a folder named "Model" where you will put your AI models, that segment cells and detect spots.
-> The pipeline is ready to use

How to use the pipeline ?
- Drag and drop Main-Epyseg from Pipeline to Spyder.
- In the menu bar (File, Edit, Search...), click "Console", then "New console in environment", then "Conda : spots_analysis". It launches a new console in spots_analysis environment, that setup_env created before. It contains every library needed for Main to turn.
- Adjust your parameters in Main-Epyseg : indicate the name of your two populations of cells, one of which is marked by immunofluorescence ("group1", "group2"). The group2 population will be the one you will see indicated by a halo in the final stack ("composite_", see below), that's why it should contain the name of your population of interest. Indicate which of those population is marked by immunofluorescence ("marked").
- Put the stacks(s) in the Repertoire folder (.tif or .czi), it will create a new folder for each stack, named after them and containing the results of analysis.
- You might also want to analyse again some stacks you analysed before, to change settings for example. In this case, put the full folder where the analysis results of this stack are stored.
- Make sure your path and indicated channels are right (see below).
- Make sure you put your pc sleep mode parameter to a sufficient amount of time (one analysis takes 1h-1h30). If it goes in sleep mode, analysis might be stopped.
- Run Main-Epyseg.

How to indicate your path properly ?
- If your Repertoire folder is as advised in your Documents directory, then your path is "/Users/yourname/Documents/Repertoire/". It might change if you put it somewhere else and name it differently : Let's say you put it in your desktop and you called it "Analyse", then your path is "/Users/yourname/Desktop/Analyse/".

How to indicate your channels properly ?
- This pipeline needs at least three channels : one on which it will perform cell segmentation (with Miranda protein for example), one corresponding to sm-FISH spots, and one to detect cell types (Asense, GFP...). It's easy to identify their number in your stack : press Maj + Z and imageJ channels tools appear. In imageJ, if you have 4 channels, their number will go from 1 to 4. In python, they will go from 0 to 3, 0 being the first channel, corresponding to 1 in imageJ, and 3 the last channel corresponding to 4 in imageJ. Therefore, to properly indicate their number, substract one to the number indicated in imageJ : if Miranda channel is the first one (1 in imageJ), it will be 0 in python. If your sm-FISH channel is the third in imageJ, it will be 2 in python, etc...
- You can also get the mean fluorescence from a protein of interest in every cell. To do that, precise you want to get it with the "chinmo_yn" parameter (in Main-Epyseg), then indicate the channel of your protein of interest in the "chinmoprot_channel" parameter.
- If the fourth channel is for another protein you do not want to quantify, indicate "n" in "chinmo_yn" and put the channel of the protein in question in "chinmoprot_channel". The pipeline will do nothing of this channel.

This pipeline produces several files, named after the following convention :
file info + base file name + .tif/.xlsx 
With that in mind the files produced and the information they contain, in production order, are the following :

name : base file name (ex: yw_40X_21-04.czi)

content : Base stack from the microscope, with no modifications. This one is not produced by the pipeline, but is the first file you need to give to the code to start analysis. It must contain at least those three channels : segmentation marker (Miranda), probe, and cell type protein (Asense). 

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : base file name but tif file (ex: yw_40X_21-04.tif)

content : Duplicate of original microscope stack. This one is produced by the pipeline, and used to start analysis. It must contain at least those three channels : segmentation marker (Miranda), probe, and cell type protein (Asense). The name of this file will be refered to as "file name" and used to name every other file produced.

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

content : May be the most useful file. It is a 4 channels stack allowing you to apprehend the analysis results graphically. In channels order, you can see the detected cells, types (green halo for type 2), detected but non kept spots (spots that are detected in the wrong cell), and kept spots.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : data_ + file name

content : Excel file containing every cell, their type, spots, spot mean intensity, volume, number, and protei expression. Last row are means of every column.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

name : Spot_numbers + file name

content : representative stats (percentages, means) on those data.




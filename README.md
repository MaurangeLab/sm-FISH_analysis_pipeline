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

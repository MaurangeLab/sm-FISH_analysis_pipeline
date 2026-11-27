# Analysis tutorial

## Analysis
In this section, you will be able to try the pipeline with a stack that we tested previously.

First, follow the steps in the "installation" part of the introduction readme.

To start trying the pipeline, go to https://drive.google.com/drive/folders/1ba1tU4iCUwcuiVIrBzaxO-MjkPu-qOHU?usp=sharing and get the "Miranda2" cellpose model, and one of the two spots segmentation models : linknet-vgg16-sigmoid-0.h5 (Epyseg model) or the "New" folder which is a Spotiflow model. Given that the two of these are equivalent in terms of accuracy, I would suggest using the Spotiflow model as it is taking a couple minutes compared to 20min for the Epyseg model. Then, get the test stack, "test_stack.tif". 

Follow the steps in the "How to use it ?" part of the introduction readme :
- The first channel ("0") 


It means that every part of the code (that are described more precisely at the end of the introduction readme) has gone well. The "Gaussian recognition reliability : 100%" means that, trying with 200 different random seed, we found the same gaussians every time. However it does not mean that every cell type has been perfectly estimated.

Here, the stack is significantly smaller (cropped in 3D) than the one we got from the microscope, so a lot of information is missing. That's why the two gaussians are not that separated in this graph, and type detection is not at its best. But as you can see at the end of the introduction readme, the real density function (which is from the whole stack) distinguishes the two groups much better. 
The yellow line indicates the center of the first gaussian, which is considered as being the low fluorescence group, and red line is the center of the gaussian for high fluorescence group.
- Finally, "Done" should show one last time. The analysis is finished !

## Results 

Now, you might want to see the results of the analysis. To see them, open imageJ, drag and drop "composite_test_stack.tif", use "Make_composite" and adjust Brightness and Contrast on the second channel if you dont see green halos. Now, you should see this :

<img width="525" height="644" alt="Capture d&#39;écran 2026-07-22 164316" src="https://github.com/user-attachments/assets/d5beb287-097d-4b73-9450-44d57684f121" />


If you put your mouse on a cell while being on the first channel, you should see the number ("value") of the cell right below the tools bar in imageJ, as follows :


<img width="753" height="127" alt="Capture d&#39;écran 2026-07-22 164503" src="https://github.com/user-attachments/assets/d0e19454-9d3f-4f8c-83c7-36fffcefae6c" />


Putting your mouse on the green halo of a cell while being in the second channel will show you just as before the probability of this cell to be a part of the interest group. This probability is determined by Gaussian Mixture Library.

In the cell number 6 at z = 1, you should see a little purple point. This one is part of the third channel and has not been kept, either because its probability to be a point according to the model was not high enough, or because an important part of its volume was detected outside of the cell, which means the point does probably not belong to the cell. You can still see its number in imageJ by being in the third channel and putting your mouse on it.

In the same cell at z = 5, you should see a white point. This one belongs to the fourth channel and was recognize to probably belong to the cell. You can see its number the same way as for the other channels.

If, after an analysis, you see errors in the type of one or several cells, or if one or several spots are not the ones you would have given to one or several cell, you can simply modify it by using Data_reconstruction.py. You will find further explanation in the introduction readme.



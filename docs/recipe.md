# GUI Test recipe

There is currently no GUI testing framework used on this project, so I made a
sequence of actions to execute to test the application and identify regressions.

> Note: Whenever `PROJECT_LOCATION` appears, it refers to Spot Detector local repository
> on your computer.

## 0: Build the application

[Rebuild the application](./rebuild_the_app.md) to apply the latest changes.
If the application was never built before, make sure to correctly install the
project first (No instruction available yet).

## 1: Project Creation

For testing purposes, some reference files will need to be accessed. In the
project, they are located under `tests/reference_data`. We will refer to this
location as `$REF_DATA` here.

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|   1  | Open the application | A welcome window appears. |
|   2  | Change the name of the project then click on `Create` | The main window appears. |
|   3  | In the menu, click on `File > Set Reference Image` and select `$REF_DATA/images/processed/C0.0.tiff` | The chosen image appears in the preview panel of the main window. |
|   4  | In the menu, click on `File > Compute k-means`. In the `number of labels` field, input `30` then click on `Start`. | After 30 seconds to a minute, 30 new labels should appear on the left of the main window. |
|   5  | Assign 5 labels to category `1` and 5 others to category 2. In the menu, click on `File > Open Detection Settings`. | the detection settings window appears, with two elements in the list of the leftmost panel. |
|   6  | Double-click on the first item of the list of label categories. Change the name of the category in the center panel. | The item in the label category list should change name too. |
|   7  | Repeat the previous step on the second item of the list. | The same result is expected on the second item. |
|   8  | Click on different fields in the middle panel. | Information relevent to the clicked field is displayed in the right-most panel. |
|   9  | Click on apply on the bottom right of the window. | The Detection settings window closes. |
|  10  | In the menu, click on `File > Save As`. Choose a name for the file and save it. | The file appears at the chosen location. |
|  11  | Quit the application. | The application exits gracefully. |
|  12  | Reopen the application. | The name and location of the new project appear in the recent projects list. |
|  13  | In the menu, click on `File > Detection Settings` | The settings set previously should still be there. |

## 2: Project Reloading and Image Processing

### Checking loading settings from file

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|   1  | Open the application. On the welcome window, click on `Open existing project`. | A file selection dialog appears. |
|   2  | Select `$REF_DATA/projects/ref_project_01.spot`. | A dialog asking to apply the current labels or create new ones appears. |
|   3  | Click on `Yes, apply.`. | The main window appears with a reference image. After 10 to 30 seconds, the labels will be applied. |
|   4  | In the menu, click on `File > Open Detection Settings` and check for the following values : | See [table](#expected-field-values). |
|   5  | Click on `Cancel`. | |

#### Expected field values
<details>
<summary> Expand </summary>

| Field                 | Sub Field | Value   |
| :-----------------    | --------- | ------- |
| Color Name            |           | Orange  |
| Minimum distance      |           | 0.01 px |
| Filter by Area        | Enabled   | True    |
|                       | Minimum   | 1.0     |
|                       | Maximum   | 99.99   |
| Filter by Convexity   | Enabled   | False   |
|                       | Minimum   |         |
|                       | Maximum   |         |
| Filter by Circularity | Enabled   | False   |
|                       | Minimum   |         |
|                       | Maximum   |         |
</details>


### Checking image processing

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|   6  | In the menu, click on `File > Open Processing Dialog`. | The processing dialog appears. |
|   7  | In the `File Selection` column, click on `Add Directory` and select `$REF_DATA/images/unprocessed/`. | A directory containing 11 files should appear in the `File Selection` column. |
|   8  | In the `File Selection` column, click on `Check Files`. | No error message should appear. |

#### In the Preprocessing settings column

##### Dust filter section

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|   9  | Enable `Apply filter` and `Report filter path`. | |
|  10  | For `Filter path`, select `$REF_DATA/images/dustFilter_30sExp_2xDNR.tiff`. |  |
|  11  | Click `Check files for compatibility`. | No error message should appear. |

##### Automatic Cropping section

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|  12  | Enable `Auto-cropping` and `Save cropped images`. |  |
|  13  | For `Save path`, select a temporary directory of your choice. |  |
|  14  | Enable both `minimum radius` and `maximum radius` and set them to 90% and 110%. |  |
|  15  | Select all the entries in the `File Selection` column then click on `Test cropping on selection` | No error message should appear. |
|  16  | Check the images displayed in the output dialog. | The ROI must match the edge of the Petri dish. |

##### Image quality checks

> ***Work In Progress***

### In the Output location column

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|  17  | For `Output folder`, enter a temporary directory of your choice. |  |
|  18  | Enable `Resume interrupted processing on this file`. | > ***Work In Progress*** |

### Evaluating Processing results

| Step | Actions | Expected Result |
| :--: | ------- | --------------- |
|  19  | Enter `Start Processing`. | The processing is completed without any error. |
|  20  | Compare the output result with the reference result provided. | The counts should be the same. |
|      |  | The hash value in the name of the generated output directory should be the same as the reference. |
|      |  | The logs should not contain any Error message. |
|  21  | Evaluate the generated processed images. | The ROI must match the edge of the Petri dish. |
|  22  |  |  |

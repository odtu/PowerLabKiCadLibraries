# METU Power Lab KiCad Libraries

---
KiCad Advenced Footprint, Symbol & 3D Libraries

---
### How to import to KiCad?

#### Step 1:

Download the repository with [here](https://github.com/odtu/PowerLabKiCadLibraries/archive/refs/heads/main.zip) and unzip it.

#### Step 2:

Open KiCad and open the preferences tab as shown in the image below.

![image](/assets/step2.png)

#### Step 3:

In the opened tab, the "Packages and Updates" section opens. Then, the "Library nickname prefix" section is deleted and left blank. The process is completed by clicking OK.

![image](/assets/step3.png)

#### Step 4:

Return to the KiCad home page and click on "Plugin and Content Manager".

![image](/assets/step4.png)

#### Step 5:

Then click on "Install from File".

![image](/assets/step5.png)

#### Step 6:

In the file selection window that opens, we find the repo that we downloaded and unzipped in the first step and select the file named "PowerLabKiCadLibraries.zip" and click open.

![image](/assets/step6.png)

#### Step 7:

After waiting a bit, our library will appear in the "Installed" tab. Now we can close it.

![image](/assets/step7.png)

#### Step 8:

When you return to the home page, click on "Preferences" and then "Configure Paths".

![image](/assets/step8.png)

#### Step 9:

As the last stage, file paths named " METUPOWERLAB_3D " ,  " METUPOWERLAB_FOOTPRINTS " ,  " METUPOWERLAB_SYMBOLS " should be created. First, press the "+" icon at the bottom left corner. Then copy and paste the names provided above (which can also be seen in the picture below). After creating the names, click on the empty "path" boxes near them. When you click, a "gray file symbol" will appear from where we will select our paths. After clicking the file symbol, a file explorer window will open. The created file paths are found in "C:\Users\user\Documents\KiCad\9.0\3rdparty" as in the image below. (The file paths should not be exactly the same. Find the similar file paths on your computer where the Kicad folders are located.) And the process is completed.+

![Ekran görüntüsü 2025-05-18 195941](https://github.com/user-attachments/assets/d992c191-a354-4046-9254-68afb7f58b72)

![image](/assets/step9.png)

---

### How to import library updates to KiCad?

Our library is quite dynamic and unfortunately there is no way for us to automatically import this movement to your computer, but you can do this at intervals with short steps.

![image](/assets/update.png)

#### Step 1:

After opening our library in Plugin and Content Manager on KiCad, the new version is downloaded by clicking Download.

#### Step 2:

Afterwards, the old version is removed by clicking Uninstall and Apply Pending Changes respectively.

#### Step 3:

Finally, the new downloaded version is imported by clicking Install from File, just like the first installation.

---

Please contact [Ekrem](https://github.com/ekremturanfirat) if you have any problems.

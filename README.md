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

As the last stage, file paths named "METUPOWERLAB_3D, METUPOWERLAB_FOOTPRINTS, METUPOWERLAB_SYMBOLS" are created. The created file paths are found in our folders added from KiCad/3rdparty in the Documents folder as in the image and the process is completed.

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
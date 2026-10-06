## What does this PR add or change?

<!-- Library/libraries, part numbers, and anything reviewers should know. -->

## Checklist

I followed `HowToCreateNewDesign/DesignRules.md`:

- [ ] Ran `python tools/check_library.py <changed files>` locally and fixed every ERROR (warnings reviewed)
- [ ] File/folder names are `METUPowerLab_Xxxxx_Yyyy`; `.kicad_mod` names have no spaces and are not `Untitled`
- [ ] Reference is a bare prefix (`R C L D Q U J Y F FB SW TP`) with no number; ICs use `U`
- [ ] Datasheet, Description, Manufacturer, Manufacturer Number and the distributor numbers that exist are filled in; field names reuse the existing spelling
- [ ] `ki_keywords` lowercase; Footprint pre-linked or `ki_fp_filters` set
- [ ] Footprint, Datasheet, Description hidden; pins on the 1.27 mm grid
- [ ] 3D models use `${METUPOWERLAB_3D}/...` and the `.step` file is included under `3dmodels/powerlab.3dshapes/`
- [ ] `(attr smd|through_hole)` matches the pads; pads have `(solder_mask_margin 0.1)`; no courtyard/keepout unless RF/magnetic sensitive area
- [ ] The libraries open in KiCad 10
- [ ] I did **not** modify `PowerLabKiCadLibraries*.zip` or `metadata.json` (maintainers update these at release time)

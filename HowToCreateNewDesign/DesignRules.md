# METU Power Lab KiCad Libraries

---

KiCad Advenced Footprint, Symbol & 3D Libraries

---

### How to create new design?

The biggest reason for creating these libraries as Power Lab is to design PCBs from a single library source, that is, a single design style. For this reason, you need to follow some rules when creating a new library.

- File names must be in the following format. Please use uppercase and lowercase letters.
    - METUPowerLab_Xxxxx_Yyyyyy_Zzzzz
    
- Designs based on a single component are not made. For example, a Chip Resistor library is created and designs with different values ​​are added to it. Separate libraries are not created for each component.

- When entering the properties of the components, the Manufacturer, Manufacturer Number and Supplier Number properties - specific to Digi-Key, Mouser, Farnell, Özdisan - should also be entered.
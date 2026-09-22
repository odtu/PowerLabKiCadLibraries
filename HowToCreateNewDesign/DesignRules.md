# METU Power Lab KiCad Libraries

---

KiCad Advenced Footprint, Symbol & 3D Libraries

---

### How to create new design?

The biggest reason for creating these libraries as Power Lab is to design PCBs from a single library source, that is, a single design style. For this reason, you need to follow some rules when creating a new library.

- File names must be in the following format. Please use uppercase and lowercase letters.
    - METUPowerLab_Xxxxx_Yyyyyy_Zzzzz
    - The prefix is always exactly `METUPowerLab` (capital M, P, L — never `METUPowerLaB`, `METUPowerlab`, etc.), so every `.kicad_sym` and `.pretty` folder sorts and matches consistently.

- Designs based on a single component are not made. For example, a Chip Resistor library is created and designs with different values ​​are added to it. Separate libraries are not created for each component.

- When entering the properties of the components, the Manufacturer, Manufacturer Number and Supplier Number properties - specific to Digi-Key, Mouser, Farnell, Özdisan - should also be entered for every distributor that actually stocks the part. Don't skip one out of laziness — but if a distributor genuinely doesn't carry that part, leaving its field blank is correct, not incomplete.

### Custom field naming

- A field name must be entered **exactly the same way every time** it is reused across parts and libraries. Before adding a new custom field, search the existing libraries for a field that already covers the same spec (e.g. `RDSon`, `Operating Temperature`, `Switching Frequency`) and reuse its exact spelling and capitalization instead of creating a near-duplicate.
- No leading, trailing, or doubled spaces in a field name (`"Package "` and `"Package"` are treated as two different fields by KiCad and silently split your data).
- No typos in field names — a misspelled field (`Voltage Raitng`, `Swtiching Frequency`, `Number of Psitions`) does not get caught by a symbol filter or BOM script; it just creates an orphan field nobody sees.
- Do not introduce a plural/singular variant of an existing field (`Manufacturer` is correct; do not add `Manufacturers`).
- When a spec is genuinely the same across component families (e.g. on-resistance of a MOSFET or GaN FET), use one shared field name (`RDSon`) rather than a per-part variant (`Rds On`, `Ron (typ) (mΩ)`). If the unit isn't obvious from the value, put it in the value string (e.g. `"31 mOhm"`), not baked into the field name.

### Reference designators

- Use standard, single-purpose KiCad reference prefixes only: `R` resistors, `C` capacitors, `L` inductors, `D` diodes, `Q` transistors/MOSFETs/GaN FETs, `U` ICs (regulators, PMICs, logic, memories, microcontrollers, isolators, etc.), `J` connectors, `Y` crystals/oscillators, `F` fuses, `FB` ferrite beads, `SW` switches, `TP` test points.
- Never invent a category-specific prefix such as `IC` — all integrated circuits use `U`, regardless of sub-category.
- Never hardcode a designator number into the Reference field (e.g. `U6`). The Reference property must always be just the bare prefix (`U`) so KiCad's annotator can number it per-schematic; a baked-in number causes duplicate/incorrect references the moment the part is placed more than once.

### Datasheet

- The `Datasheet` field must never be left blank. Every part must link directly to its manufacturer datasheet or product page (PDF preferred). A blank Datasheet field blocks anyone from verifying the part without hunting for it manually.

### Description

- Keep `Description` short and templated per component family, e.g. `"<value/spec> <Component Type> <Package>"` such as `"Ceramic SMD Cap 0603"` or `"3.3V LDO"`. Consistent phrasing lets Description be used for search/filtering, not just as free text.

### Keywords (`ki_keywords`)

- Lowercase, space-separated synonyms a designer might search for (e.g. `resistor res r`). No trailing spaces, no capitalized fragments.

### Footprint linkage

- If every part in the symbol shares one footprint, pre-link it in the `Footprint` field as `LibraryNickname:FootprintName`.
- If the part is offered in multiple packages (chip resistors, ceramic caps, etc.), leave `Footprint` blank and instead constrain the choice with `ki_fp_filters`, so the footprint is picked at placement time — don't leave it blank *and* leave `ki_fp_filters` empty, since that gives no guidance at all.

### Footprint files

- `.kicad_mod` file names inside a `.pretty` folder should use underscores instead of spaces (`0603_Large_NS.kicad_mod`, not `0603 Large NS.kicad_mod`) for consistency with the rest of the naming convention and to avoid issues with tools that don't expect spaces in file paths. Never leave a footprint with KiCad's default name (`Untitled.kicad_mod`) — rename it to describe the part before committing.
- The `(attr ...)` flag must match the pads actually used: `through_hole` for a footprint whose signal pads are `thru_hole`, `smd` for one whose signal pads are `smd`. Mechanical/alignment holes declared `np_thru_hole` don't count — an SMD connector with two unplated mounting holes is still `(attr smd)`. Getting this wrong doesn't just look wrong in the footprint chooser — it puts the part in the wrong pick-and-place / assembly output.
- Every `(model ...)` path must use the `${METUPOWERLAB_3D}` environment variable (the one set up in the main README), pointing at `${METUPOWERLAB_3D}/Category/Subcategory/filename.step`. Never hardcode an absolute path from one machine (`D:/...`, `C:/Users/...`) — it only works for whoever created the footprint and breaks the 3D view for everyone else who follows the README setup.

### Footprint pad & drawing rules

These are the geometric conventions found consistently across the existing library — match them on every new footprint:

- **Solder mask margin**: every pad gets `(solder_mask_margin 0.1)` (0.1 mm mask overlap/expansion beyond the copper pad). This is used on 100% of existing pads — don't leave it off.
- **Silkscreen outline width**: the body outline (`fp_line`/`fp_rect` on `F.SilkS`) is drawn at `(width 0.1)`. This is the standard across the whole library — don't use 0.2, 0.15, 0.12, etc. for the outline. (Small decorative elements — a pin-1 dot, a polarity mark — are a separate concern and may use a different width to stay visible at their size; that's fine, it's the *body outline* width that must be 0.1.)
- **Reference text** (silkscreen): `(size 1 1)` with `(thickness 0.1)`.
- **Value text** (usually hidden, on F.Fab): `(size 1 1)` with `(thickness 0.15)`.
- **Courtyard (`F.CrtYd`)**: not required on every footprint. The silkscreen outline plus the 3D model are enough for clearance checking day-to-day — only add a courtyard when a specific part actually needs it (e.g. an unusually tight placement, an unusual mechanical envelope, or the silkscreen doesn't fully represent the part's overlap). When it is added, draw it at `(width 0.05)`.
- **SMD pad shape**: default to `rect` for every SMD pad. This is the shape used on 910 of the library's ~940 SMD pads. Only use `roundrect` (with a `roundrect_rratio`) when there's a specific reason to — e.g. a fine-pitch QFN/power package where IPC-7351 rounding or pin-1 differentiation is actually needed. If a footprint doesn't call for that, don't reach for `roundrect` by default; plain `rect` is the house style.
- **THT/mechanical pad shapes**: `circle`/`thru_hole` for plated THT signal pads, `np_thru_hole` for non-plated mechanical mounting holes only — never use `np_thru_hole` for something that carries a signal.
- **Grid**: every pin's electrical connection point (the schematic symbol's `(at X Y ...)`, not the pin `length`) must land on the 1.27 mm (50 mil) grid, so wires snap to it cleanly. This is already true across the whole symbol library — keep it that way; pin `length` itself can vary freely to fit the body outline.

### Thermal / high-current pads (shield, ground, VIN, and other big pads)

Any pad whose job is primarily heat spreading or carrying high current — a shield/exposed pad, a ground or thermal tab (e.g. `SL`/`PGND`/`AGND` on a power stage), a `VIN`/`VOUT`/drain/source pad on a switching part, or any SMD pad noticeably larger than a standard signal lead — gets extra copper and thermal vias underneath it, not just a single `F.Cu` pad:

- **Mirror the pad onto the bottom layer.** Add a second SMD pad at the exact same `(at ...)` position and `size` as the top copper, on `B.Cu`/`B.Mask`/`B.Paste` instead of `F.Cu`/`F.Mask`/`F.Paste`. This gives the opposite side of the board copper to spread heat and current into, and a second surface for assembly to reflow onto or bond a heatsink to.
- **Give every piece the same pad number.** The `F.Cu` pad, the `B.Cu` pad, and every thermal via underneath must share the identical pad `"number"` (e.g. all `"7"`). KiCad assigns nets by matching a footprint pad's number to the symbol pin with that number — give the via array or the back-side copper a different number and it ends up on no net (or a stray one), which silently defeats the point of the thermal pad and can trip DRC. This is already the pattern used in `13-PowerWFQFN.kicad_mod` — follow it everywhere; don't hand the via array a spare unused number the way the older `8-PowerTDFN(5x6mm)` footprint did.
- **Thermal via geometry**: `thru_hole circle`, `(size 0.5)`, `(drill 0.3)`, `(layers "*.Cu" "*.Mask")`, `(remove_unused_layers no)` — matches the via size already in use across this library, and stays within any standard fab's capability. Lay the vias out on a grid at roughly **1.0 mm pitch**, kept back **at least 0.3 mm** from the pad's copper edge so a via never breaks out past the solder mask opening. If the pad is too narrow for a grid (under ~1.2 mm in one direction), fall back to a single centered row of vias at that same 1.0 mm pitch rather than skipping thermal vias altogether.
- **Fab note, not a footprint property**: vias placed inside a solder-paste-covered pad ("via-in-pad") should be called out as tented/plugged in the board's fab notes — otherwise paste wicks down the via barrel during reflow and starves the joint. That instruction lives in the manufacturing notes/stackup, not in the `.kicad_mod` file itself.

### Symbol drawing style

- **Body rectangle**: `(stroke (width 0))` (inherit the schematic's default line width) and fill type `background` for a normal opaque part (ICs, passives). Connectors, screw terminals, and shunt resistors use `(fill (type none))` instead, drawn as an open outline — keep using `none` only for that same kind of part (something you'd recognize as a physical connector/terminal, not a black-box component), not interchangeably.
- **Reference/Value text** on the symbol: `(size 1.27 1.27)`.
- **Hidden fields**: `Footprint`, `Datasheet`, and `Description` are always `(hide yes)` on the symbol — only `Reference` and `Value` are visible.
- **BOM/board flags**: every symbol unit is `(in_bom yes) (on_board yes) (exclude_from_sim no)` — don't turn any of these off without a specific reason.
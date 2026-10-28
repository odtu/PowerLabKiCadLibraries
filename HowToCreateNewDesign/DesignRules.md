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
- **Courtyard (`F.CrtYd`/`B.CrtYd`) and keepout / rule areas (`zone` with a `(keepout ...)` block)**: do **not** use these on normal components — resistors, capacitors, diodes, transistors, ICs, connectors, etc. get neither a courtyard nor a keepout zone. The silkscreen outline plus the 3D model are enough for placement and clearance checking; an extra courtyard or keepout on an ordinary part only produces DRC noise and blocks routing/pours that are actually fine.
    - **Exception 1 — parts with a real RF/magnetic sensitive area** defined in the datasheet: e.g. the antenna region of an ESP32 (or any module with a PCB/chip antenna), or the sensing area under a magnetic encoder/readhead (e.g. RLS `RLC2HD`). For these, add a keepout zone that copies the datasheet's no-copper / no-component region (tracks, vias, pads, copper pour, footprints `not_allowed` as the datasheet requires, on every copper layer it applies to), and a courtyard that marks the same area so other parts can't be placed into it.
    - **Exception 2 — inductors: keepout between the pads.** Every inductor footprint (`METUPowerLab_Inductors_*` libraries) whose two pads are **at least 0.6 mm apart** (edge to edge — room for one track at the lab default 0.2 mm track / 0.2 mm clearance) gets a keepout zone under the body, between the pads, so nothing gets routed or poured under the winding:
        - Rectangle from the inner edge of pad 1 to the inner edge of pad 2, spanning the pad height (no inset — it touches the pads' inner edges).
        - On `F.Cu` only, so inner-layer and bottom ground planes under the inductor stay intact.
        - `(tracks not_allowed) (vias not_allowed) (copperpour not_allowed)`, with `(pads allowed) (footprints allowed)` — the footprint's own pads don't trip it, and a part on the bottom side can still sit under the inductor.
        - `(name "Inductor Keepout")`, and no courtyard.
        - Copy the zone block from any footprint in `METUPowerLab_Inductors_SurfaceMounts.pretty` and change only the four corner points. An inductor whose pads are closer than 0.6 mm (no track can fit) gets no keepout.
    - When a courtyard is added under exception 1, draw it at `(width 0.05)`.
    - Don't add a keepout for any other general "good practice" reason (e.g. "no traces under a connector") — if a design needs that, the designer draws it on the board for that specific layout, not inside the library footprint.
- **SMD pad shape**: default to `rect` for every SMD pad. This is the shape used on 910 of the library's ~940 SMD pads. Only use `roundrect` (with a `roundrect_rratio`) when there's a specific reason to — e.g. a fine-pitch QFN/power package where IPC-7351 rounding or pin-1 differentiation is actually needed. If a footprint doesn't call for that, don't reach for `roundrect` by default; plain `rect` is the house style.
- **THT/mechanical pad shapes**: `circle`/`thru_hole` for plated THT signal pads, `np_thru_hole` for non-plated mechanical mounting holes only — never use `np_thru_hole` for something that carries a signal.
- **Grid**: every pin's electrical connection point (the schematic symbol's `(at X Y ...)`, not the pin `length`) must land on the 1.27 mm (50 mil) grid, so wires snap to it cleanly. This is already true across the whole symbol library — keep it that way; pin `length` itself can vary freely to fit the body outline.

### Thermal / high-current pads (shield, ground, VIN, and other big pads)

Any pad whose job is primarily heat spreading or carrying high current — a shield/exposed pad, a ground or thermal tab (e.g. `SL`/`PGND`/`AGND` on a power stage), a `VIN`/`VOUT`/drain/source pad on a switching part, or any SMD pad noticeably larger than a standard signal lead — gets extra copper and thermal vias underneath it, not just a single `F.Cu` pad:

- **Mirror the pad onto the bottom layer.** Add a second SMD pad at the exact same `(at ...)` position and `size` as the top copper, on `B.Cu`/`B.Mask`/`B.Paste` instead of `F.Cu`/`F.Mask`/`F.Paste`. This gives the opposite side of the board copper to spread heat and current into, and a second surface for assembly to reflow onto or bond a heatsink to.
- **Give every piece the same pad number.** The `F.Cu` pad, the `B.Cu` pad, and every thermal via underneath must share the identical pad `"number"` (e.g. all `"7"`). KiCad assigns nets by matching a footprint pad's number to the symbol pin with that number — give the via array or the back-side copper a different number and it ends up on no net (or a stray one), which silently defeats the point of the thermal pad and can trip DRC. This is already the pattern used in `13-PowerWFQFN.kicad_mod` — follow it everywhere; don't hand the via array a spare unused number the way the older `8-PowerTDFN(5x6mm)` footprint did.
- **Thermal via geometry**: `thru_hole circle`, `(size 0.5)`, `(drill 0.3)`, `(layers "*.Cu" "*.Mask")`, `(remove_unused_layers no)` — matches the via size already in use across this library, and stays within any standard fab's capability. Lay the vias out on a grid at roughly **1.0 mm pitch**, kept back **at least 0.3 mm** from the pad's copper edge so a via never breaks out past the solder mask opening. If the pad is too narrow for a grid (under ~1.2 mm in one direction), fall back to a single centered row of vias at that same 1.0 mm pitch rather than skipping thermal vias altogether.
- **Fab note, not a footprint property**: vias placed inside a solder-paste-covered pad ("via-in-pad") should be called out as tented/plugged in the board's fab notes — otherwise paste wicks down the via barrel during reflow and starves the joint. That instruction lives in the manufacturing notes/stackup, not in the `.kicad_mod` file itself.

### Multi-unit symbols for large ICs

- A microcontroller, DSP, FPGA or any IC with more than about 40 pins is drawn as a **multi-unit symbol**, one unit per function, never as one big block. A designer then places each unit next to the circuit it serves.
- Typical units: power and ground (supplies on top pointing up, grounds at the bottom pointing down), clock / reset / debug, analog (ADC, DAC, references), comparator / PGA inputs, and GPIO or peripheral banks. Follow the datasheet's pin groups.
- Don't give the units names (`unit_name`): KiCad appends the name to the reference, so a part reads `U4Power` instead of `U4A`. Keep the units in a fixed order instead: A power, then clock/reset/debug, analog, and the GPIO banks last.
- Units share the Reference and Value positions, so put both above the units and top-align the bodies. Otherwise the Value lands inside a taller unit.
- Every pin appears in exactly one unit. Smaller ICs (a gate driver, a regulator) stay one unit. `METUPowerLab_Microcontrollers_C2000:TMS320F280049PMS` is the reference example.

### Pin alternates for microcontrollers and other multiplexed pins

- Every pin that can take more than one function (an MCU or DSP GPIO, an analog pin shared with comparators or op-amps, a dual-use clock or debug pin) lists all of its other functions as **KiCad pin alternates**. In the file each one is an `(alternate "NAME" type line)` entry on the pin; in the symbol editor they are under Pin Properties → Alternate pin definitions. A designer then picks the function a pin is used for (`TIM1_CH1`, `FDCAN1_RX`, `ADC1_IN2`…) in the schematic, and the pin shows that name.
- The pin's own name stays the port or primary name (`PA8`, `GPIO0`, `A2/B6/C9`). The alternates add the rest. Don't repeat the pin's own name among them.
- Take the functions from the vendor's machine-readable pin data, not by hand from a PDF. For STM32 use ST's [STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data) (`mcu/<part>.xml`); for TI C2000 use the datasheet's Pin Attributes table. Give each alternate its direction (`input`, `output`, `bidirectional`, `open_collector`), with `bidirectional` where the data gives none.
- Examples: `METUPowerLab_Microcontrollers_STM32:STM32G491MET3` and `:STM32F103CBT7` (from ST's pin data), and `METUPowerLab_Microcontrollers_C2000:F280039CSPM` (from TI's Table 5-1).

### Symbol drawing style

- **Body rectangle**: `(stroke (width 0))` (inherit the schematic's default line width) and fill type `background` for a normal opaque part (ICs, passives). Connectors, screw terminals, and shunt resistors use `(fill (type none))` instead, drawn as an open outline — keep using `none` only for that same kind of part (something you'd recognize as a physical connector/terminal, not a black-box component), not interchangeably.
- **Reference/Value text** on the symbol: `(size 1.27 1.27)`.
- **Hidden fields**: `Footprint`, `Datasheet`, and `Description` are always `(hide yes)` on the symbol. `Reference` and `Value` are visible, plus the key ratings below. Every other field stays hidden.
- **Visible key ratings**: passives, discretes, power connectors and regulators show the one to three ratings you would otherwise open the datasheet for, so a part can be checked straight from the schematic. Don't show anything beyond this list (no package, temperature, distributor numbers…):

    | Library | Visible fields |
    |---|---|
    | Resistors (chip, shunt) | `Power`, `Tolerance` |
    | Capacitors | `Voltage Rating` |
    | Inductors | `Current Rating`, `Saturation Current` (name shown) |
    | Ferrite beads | `Impedance @ Frequency`, `Current Rating` |
    | MOSFETs, power blocks | `VDS`, `ID`, `RDSon` (name shown) |
    | GaN power stages | `Voltage Rating`, `Current Rating`, `RDSon` (name shown) |
    | Schottky diodes | `DC Reverse Voltage`, `Current Rating` |
    | TVS diodes | `Reverse Standoff Voltage`, `Clamping Voltage` (name shown) |
    | PTC fuses | `Current - Hold`, `Current - Trip` (name shown) |
    | LEDs | `Forward Voltage`, `Current Rating` |
    | Crystals | `Load Capacitance` (name shown; the Value already is the frequency) |
    | LDOs, voltage references | `Output Voltage`, `Current Rating` (name shown) |
    | Buck converters | `Voltage Input Rating`, `Current Rating` (name shown) |
    | Power connectors, screw terminals | `Current Rating` |

    - Text `(size 1 1)`, smaller than Reference/Value, so the ratings read as secondary information.
    - Stacked directly under the Value with the Value's x and justification: first line 1.778 mm below the Value, then one line every 1.524 mm. Where the Value sits above the body (shunts, crystals), stack them upward between the Value and the Reference instead.
    - `(show_name yes)` only where the value alone could be misread (two ratings with the same unit, or a bare `V`/`A` on an IC). Where the unit says it all (`1/10W`, `±1%`, `50V`, `13A`), show the value without the name.
    - Leave a field hidden when its value is empty or `-` (e.g. the power of a 0 Ω jumper).
    - Write the value with its unit, e.g. `1/10W`, `5V (Max)` or `2.1 mOhm`, not `1/10 Watt`, `5(Max)` or `2.1mOhm`.
    - `tools/check_library.py` knows these field names (`KEY_RATING_FIELDS`). If you add a new part type that needs one, add the field to that list and to this table.
- **BOM/board flags**: every symbol unit is `(in_bom yes) (on_board yes) (exclude_from_sim no)` — don't turn any of these off without a specific reason.
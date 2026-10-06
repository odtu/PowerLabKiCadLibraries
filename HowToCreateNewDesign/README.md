Please review DesignRules.md and follow the guidelines when designing the libraries. Once you're done, fork the repo and open a pull request. We will review your submission and merge it if everything looks good.

### Automatic checks on pull requests

Every pull request that touches `symbols/`, `footprints/`, `3dmodels/` or `tools/` runs the **Library checks** workflow (`.github/workflows/library-checks.yml`):

- **Library standards** – `tools/check_library.py` checks the symbol and footprint files you changed against DesignRules.md. Problems are shown as annotations on the "Files changed" tab. **ERRORs fail the check** and must be fixed; **WARNINGs** point at things reviewers will look at (some have legitimate exceptions, e.g. a courtyard on an RF/magnetic sensitive part).
- **Libraries load in KiCad 10** – every changed `.kicad_sym` and `.pretty` is opened with `kicad-cli` (symbols/footprints exported to SVG); a file KiCad cannot read fails the check.
- **PCM package files untouched** – `PowerLabKiCadLibraries*.zip` and `metadata.json` are rebuilt by the maintainers at release time, so a PR that modifies them fails (maintainers can add the `release` label to a release PR to allow it).

Run the standards check locally before opening a PR (Python 3, nothing to install):

```
python tools/check_library.py symbols/METUPowerLab_Xxxxx_Yyyy.kicad_sym footprints/METUPowerLab_Xxxxx_Yyyy.pretty
python tools/check_library.py --changed upstream/main # everything changed on your branch (remote = odtu repo)
python tools/check_library.py --all -q                # whole library, errors + summary only
python tools/check_library.py --list-rules            # every rule and its severity
```

The exit code is 1 when there is at least one ERROR.

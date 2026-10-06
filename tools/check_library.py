#!/usr/bin/env python3
"""METU Power Lab KiCad library standards checker.

Checks symbol libraries (.kicad_sym) and footprint libraries (.pretty /
.kicad_mod) against HowToCreateNewDesign/DesignRules.md.

Usage:
    python tools/check_library.py PATH [PATH ...]   # files / .pretty folders
    python tools/check_library.py --all              # whole library
    python tools/check_library.py --changed origin/main
    python tools/check_library.py --list-rules

Only the Python 3 standard library is used. Exit code is 1 if any ERROR was
found (unless --exit-zero), otherwise 0. When GITHUB_ACTIONS=true the findings
are printed as GitHub Actions annotations.
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOLS_DIR = os.path.join(REPO_ROOT, "symbols")
FOOTPRINTS_DIR = os.path.join(REPO_ROOT, "footprints")

LIB_PREFIX = "METUPowerLab_"
MODEL_VAR = "${METUPOWERLAB_3D}/"

ERROR = "error"
WARNING = "warning"

# rule id -> (severity, short description). Severity is ERROR only for rules
# that are unambiguous in DesignRules.md and already satisfied by the library.
RULES = OrderedDict([
    ("parse", (ERROR, "File must be a valid KiCad S-expression file of the expected kind")),
    ("lib-name", (ERROR, "Library file/folder name must be METUPowerLab_Xxxxx_Yyyy (exact prefix, letters/digits/'-' segments)")),
    ("lib-name-style", (WARNING, "Name segments should start with an uppercase letter (Xxxxx_Yyyy style)")),
    ("sym-reference", (ERROR, "Reference must be a bare allowed prefix (R C L D Q U J Y F FB SW TP; #PWR/#FLG for power symbols, NT for net ties)")),
    ("sym-datasheet", (ERROR, "Datasheet field must not be blank")),
    ("sym-manufacturer", (ERROR, "Manufacturer field must be present (not required for power symbols and (in_bom no) parts)")),
    ("sym-manufacturer-empty", (WARNING, "Manufacturer field should not be empty")),
    ("sym-manufacturer-number", (WARNING, "Manufacturer Number field should be present and filled")),
    ("sym-description", (WARNING, "Description field should be present and filled")),
    ("field-name-spaces", (ERROR, "Field names must not have leading, trailing or doubled spaces")),
    ("field-name-near-duplicate", (WARNING, "Field name looks like a near-duplicate (case/spacing/plural/typo) of another field name in the library")),
    ("sym-keywords", (WARNING, "ki_keywords should be present, lowercase, without leading/trailing/doubled spaces")),
    ("sym-footprint-linkage", (ERROR, "Footprint and ki_fp_filters must not both be empty")),
    ("sym-footprint-ref", (ERROR, "Footprint field pointing at a METUPowerLab library must reference an existing footprint")),
    ("sym-footprint-format", (WARNING, "Footprint field should be LibraryNickname:FootprintName")),
    ("sym-fp-filter", (WARNING, "ki_fp_filters entries for METUPowerLab libraries should match at least one footprint")),
    ("sym-hidden-fields", (ERROR, "Footprint, Datasheet and Description fields must be hidden")),
    ("sym-visible-fields", (WARNING, "Only Reference and Value should be visible")),
    ("sym-flags", (WARNING, "Symbols should be (in_bom yes) (on_board yes) (exclude_from_sim no)")),
    ("sym-text-size", (WARNING, "Reference/Value text should be (size 1.27 1.27)")),
    ("sym-body-style", (WARNING, "Body rectangles should use (stroke (width 0)) and fill background or none")),
    ("sym-pin-grid", (ERROR, "Pin connection points must be on the 1.27 mm grid")),
    ("fp-file-name", (ERROR, ".kicad_mod names must not contain spaces or be 'Untitled', and must live in a .pretty folder")),
    ("fp-name-mismatch", (WARNING, "Footprint name inside the file should match the file name")),
    ("fp-3d-model-path", (ERROR, "3D model paths must not be absolute or relative paths; use ${METUPOWERLAB_3D}/...")),
    ("fp-3d-model-var", (WARNING, "3D model paths should use ${METUPOWERLAB_3D}/ rather than another variable (e.g. ${KICAD10_3DMODEL_DIR})")),
    ("fp-3d-model-missing", (WARNING, "3D model file referenced by the footprint should exist in 3dmodels/powerlab.3dshapes")),
    ("fp-3d-model-none", (WARNING, "Component footprints should have a 3D model")),
    ("fp-attr", (ERROR, "(attr smd|through_hole) must match the signal pad types (np_thru_hole ignored)")),
    ("fp-pad-mask-margin", (WARNING, "Every pad should have (solder_mask_margin 0.1)")),
    ("fp-silk-width", (WARNING, "Silkscreen body outline (fp_line/fp_rect on SilkS) should be width 0.1")),
    ("fp-ref-text", (WARNING, "Reference text should be (size 1 1) (thickness 0.1)")),
    ("fp-value-text", (WARNING, "Value text should be (size 1 1) (thickness 0.15)")),
    ("fp-courtyard-keepout", (WARNING, "Courtyard / keepout only allowed for RF/magnetic sensitive areas")),
    ("fp-courtyard-width", (WARNING, "Courtyard lines (when allowed) should be width 0.05")),
    ("fp-smd-pad-shape", (WARNING, "SMD pads should default to rect (roundrect only with a specific reason)")),
    ("fp-thermal-via", (WARNING, "Thermal vias should be thru_hole circle, size 0.5, drill 0.3, layers *.Cu *.Mask, remove_unused_layers no")),
    ("fp-thermal-via-number", (WARNING, "Via-like thru_hole pads on an SMD footprint should share the number of the pad they cool")),
    ("fp-npth-signal", (WARNING, "np_thru_hole pads are for mechanical holes only (should have no pad number)")),
])

ALLOWED_REFERENCES = {"R", "C", "L", "D", "Q", "U", "J", "Y", "F", "FB", "SW", "TP"}
POWER_REFERENCES = {"#PWR", "#FLG"}
NET_TIE_REFERENCE = "NT"  # KiCad's net-tie prefix; tolerated only on net-tie symbols

GRID = 1.27
EPS = 1e-6


# --------------------------------------------------------------------------
# S-expression parser
# --------------------------------------------------------------------------

class SExprError(Exception):
    def __init__(self, message, line):
        Exception.__init__(self, message)
        self.message = message
        self.line = line


class SList(list):
    """A parenthesised list; `line` is the line of its opening parenthesis."""
    __slots__ = ("line",)


class QStr(str):
    """A quoted string atom (bare atoms are plain str)."""
    __slots__ = ()


_TOKEN_RE = re.compile(r'\s+|\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', re.S)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def _unescape(body):
    if "\\" not in body:
        return body
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_sexpr(text):
    """Parse one top-level S-expression. Returns an SList tree."""
    pos = 0
    line = 1
    n = len(text)
    stack = []
    root = None
    while pos < n:
        m = _TOKEN_RE.match(text, pos)
        if m is None:
            if text[pos] == '"':
                raise SExprError("unterminated quoted string", line)
            raise SExprError("unexpected character %r" % text[pos], line)
        tok = m.group(0)
        pos = m.end()
        c = tok[0]
        if c.isspace():
            line += tok.count("\n")
            continue
        if c == "(":
            node = SList()
            node.line = line
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise SExprError("more than one top-level expression", line)
            else:
                root = node
            stack.append(node)
        elif c == ")":
            if not stack:
                raise SExprError("unbalanced ')'", line)
            stack.pop()
        else:
            if c == '"':
                atom = QStr(_unescape(tok[1:-1]))
                line_inc = tok.count("\n")
            else:
                atom = tok
                line_inc = 0
            if not stack:
                raise SExprError("atom outside of any list", line)
            stack[-1].append(atom)
            line += line_inc
    if stack:
        raise SExprError("unclosed '(' opened at line %d" % stack[-1].line, line)
    if root is None:
        raise SExprError("empty file", line)
    return root


def head(node):
    if isinstance(node, SList) and node and isinstance(node[0], str) and not isinstance(node[0], QStr):
        return node[0]
    return None


def children(node, name):
    return [c for c in node[1:] if isinstance(c, SList) and head(c) == name]


def child(node, name):
    for c in node[1:]:
        if isinstance(c, SList) and head(c) == name:
            return c
    return None


def atoms(node):
    return [x for x in node[1:] if isinstance(x, str)]


def walk(node, name=None):
    """Depth-first iteration over all SList descendants (including node)."""
    stack = [node]
    while stack:
        cur = stack.pop()
        if name is None or head(cur) == name:
            yield cur
        for c in reversed(cur):
            if isinstance(c, SList):
                stack.append(c)


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def child_value(node, name, default=None):
    c = child(node, name) if node is not None else None
    if c is None or len(c) < 2 or not isinstance(c[1], str):
        return default
    return c[1]


def numbers(node):
    return [to_float(a) for a in atoms(node) if to_float(a) is not None] if node is not None else []


def feq(a, b):
    return a is not None and b is not None and abs(a - b) < 1e-6


# --------------------------------------------------------------------------
# Findings / reporting
# --------------------------------------------------------------------------

class Finding(object):
    __slots__ = ("severity", "rule", "path", "line", "message")

    def __init__(self, severity, rule, path, line, message):
        self.severity = severity
        self.rule = rule
        self.path = path
        self.line = line
        self.message = message


class Reporter(object):
    def __init__(self):
        self.findings = []

    def add(self, rule, path, line, message, severity=None):
        sev = severity or RULES[rule][0]
        self.findings.append(Finding(sev, rule, path, line or 1, message))

    def count(self, severity):
        return sum(1 for f in self.findings if f.severity == severity)


def _gh_escape_data(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _gh_escape_prop(s):
    return _gh_escape_data(s).replace(":", "%3A").replace(",", "%2C")


def rel(path):
    """Repo-relative path (what GitHub annotations expect); paths outside the
    repo are shown relative to the current directory when possible."""
    ap = os.path.abspath(path)
    for base in (REPO_ROOT, os.getcwd()):
        try:
            r = os.path.relpath(ap, base)
        except ValueError:  # different drive on Windows
            continue
        if not r.startswith(".."):
            return r.replace("\\", "/")
    return ap.replace("\\", "/")


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*\Z")


def check_lib_name(name, path, rep, kind):
    if not name.startswith(LIB_PREFIX):
        if name.lower().startswith(LIB_PREFIX.lower()) or name.lower().startswith("metupowerlab"):
            rep.add("lib-name", path, 1, "%s name '%s' must start with exactly 'METUPowerLab_' "
                    "(capital M, P, L)" % (kind, name))
        else:
            rep.add("lib-name", path, 1, "%s name '%s' must start with 'METUPowerLab_'" % (kind, name))
        return
    rest = name[len(LIB_PREFIX):]
    segments = rest.split("_")
    bad = [s for s in segments if not _SEGMENT_RE.match(s)]
    if bad:
        rep.add("lib-name", path, 1, "%s name '%s' must be METUPowerLab_Xxxxx_Yyyy: segments may only contain "
                "letters, digits and '-' (no spaces, empty or doubled '_'); offending: %s"
                % (kind, name, ", ".join("'%s'" % s for s in bad)))
        return
    lower = [s for s in segments if not s[0].isupper()]
    if lower:
        rep.add("lib-name-style", path, 1, "%s name '%s': segment(s) %s should start with an uppercase letter"
                % (kind, name, ", ".join("'%s'" % s for s in lower)))


def read_and_parse(path, rep, expected_heads):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except UnicodeDecodeError as exc:
        rep.add("parse", rel(path), 1, "file is not valid UTF-8 (%s)" % exc)
        return None
    except OSError as exc:
        rep.add("parse", rel(path), 1, "cannot read file (%s)" % exc)
        return None
    try:
        root = parse_sexpr(text)
    except SExprError as exc:
        rep.add("parse", rel(path), exc.line, "S-expression syntax error: %s" % exc.message)
        return None
    if head(root) not in expected_heads:
        rep.add("parse", rel(path), root.line, "expected a (%s ...) file, found (%s ...)"
                % (" / ".join(expected_heads), head(root)))
        return None
    return root


def library_root(path):
    """Root of the library checkout containing `path` (a file in symbols/ or a
    .pretty in footprints/); falls back to this repository."""
    parts = os.path.abspath(path).replace("\\", "/").split("/")
    for anchor in ("symbols", "footprints"):
        if anchor in parts[:-1]:
            i = len(parts) - 1 - parts[::-1].index(anchor)
            root = "/".join(parts[:i]) or "/"
            if os.path.isdir(os.path.join(root, "footprints")):
                return root
    return REPO_ROOT


_footprint_cache = {}


def footprints_in_lib(nickname, root=REPO_ROOT):
    """Footprint names available in <root>/footprints/<nickname>.pretty (None if missing)."""
    key = (root, nickname)
    if key not in _footprint_cache:
        d = os.path.join(root, "footprints", nickname + ".pretty")
        if os.path.isdir(d):
            _footprint_cache[key] = set(f[:-len(".kicad_mod")] for f in os.listdir(d)
                                        if f.endswith(".kicad_mod"))
        else:
            _footprint_cache[key] = None
    return _footprint_cache[key]


# --------------------------------------------------------------------------
# Field name index (library-wide) for near-duplicate detection
# --------------------------------------------------------------------------

def _norm_field(name):
    key = re.sub(r"[^0-9a-z]", "", name.lower())
    if len(key) > 3 and key.endswith("s") and not key.endswith("ss"):
        key = key[:-1]
    return key


def _is_typo_pair(a, b):
    """True for a single transposition, insertion or deletion of a letter
    (substitutions are skipped: 'Min Voltage' vs 'Max Voltage' is legit)."""
    la, lb = a.lower(), b.lower()
    if la == lb or min(len(la), len(lb)) < 6:
        return False
    if re.sub(r"\d", "", la) == re.sub(r"\d", "", lb):
        return False
    if len(la) == len(lb):
        diff = [i for i in range(len(la)) if la[i] != lb[i]]
        return (len(diff) == 2 and diff[1] == diff[0] + 1 and la[diff[0]] == lb[diff[1]]
                and la[diff[1]] == lb[diff[0]] and la[diff[0]].isalpha())
    if abs(len(la) - len(lb)) == 1:
        longer, shorter = (la, lb) if len(la) > len(lb) else (lb, la)
        for i in range(len(longer)):
            if longer[:i] + longer[i + 1:] == shorter:
                return longer[i].isalpha()
    return False


class FieldIndex(object):
    def __init__(self):
        self.counts = Counter()
        self._similar = None

    def add_tree(self, root):
        for sym in children(root, "symbol"):
            for prop in children(sym, "property"):
                if len(prop) > 1 and isinstance(prop[1], str) and not prop[1].startswith("ki_"):
                    self.counts[prop[1]] += 1

    def similar(self, name):
        if self._similar is None:
            self._similar = defaultdict(list)
            names = list(self.counts)
            by_norm = defaultdict(list)
            for n in names:
                by_norm[_norm_field(n)].append(n)
            for group in by_norm.values():
                for a in group:
                    for b in group:
                        if a != b:
                            self._similar[a].append((b, "differs only in case/spacing/punctuation/plural"))
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    if _norm_field(a) != _norm_field(b) and _is_typo_pair(a.strip(), b.strip()):
                        self._similar[a].append((b, "looks like a typo"))
                        self._similar[b].append((a, "looks like a typo"))
        return self._similar.get(name, [])


# --------------------------------------------------------------------------
# Symbol library checks
# --------------------------------------------------------------------------

def _prop_hidden(prop):
    if child_value(prop, "hide") == "yes":
        return True
    eff = child(prop, "effects")
    if eff is not None:
        if "hide" in atoms(eff) or child_value(eff, "hide") == "yes":
            return True
    return False


def _font_size(node):
    eff = child(node, "effects")
    font = child(eff, "font") if eff is not None else None
    size = numbers(child(font, "size")) if font is not None else []
    thick = numbers(child(font, "thickness")) if font is not None else []
    return size, (thick[0] if thick else None)


def _on_grid(v):
    q = v / GRID
    return abs(q - round(q)) < 1e-4


def check_symbol_file(path, rep, field_index, tree=None):
    rp = rel(path)
    stem = os.path.basename(path)[:-len(".kicad_sym")]
    check_lib_name(stem, rp, rep, "Symbol library")
    root = tree if tree is not None else read_and_parse(path, rep, ("kicad_symbol_lib",))
    if root is None:
        return 0

    lib_root = library_root(path)
    near_dups = OrderedDict()  # field name -> [line, [symbols], similar]
    symbols = children(root, "symbol")
    for sym in symbols:
        sname = sym[1] if len(sym) > 1 and isinstance(sym[1], str) else "?"
        where = "symbol '%s'" % sname
        props = OrderedDict()
        for prop in children(sym, "property"):
            if len(prop) < 3 or not isinstance(prop[1], str) or not isinstance(prop[2], str):
                rep.add("parse", rp, prop.line, "%s: malformed property" % where)
                continue
            props.setdefault(prop[1], prop)

            fname = prop[1]
            if fname != fname.strip() or "  " in fname:
                rep.add("field-name-spaces", rp, prop.line,
                        "%s: field name '%s' has leading/trailing/doubled spaces" % (where, fname))
            if not fname.startswith("ki_"):
                sims = field_index.similar(fname)
                if sims:
                    mine = field_index.counts.get(fname, 0)
                    relevant = [(o, why) for o, why in sims if field_index.counts.get(o, 0) >= mine]
                    if relevant:
                        entry = near_dups.setdefault(fname, [prop.line, [], relevant])
                        entry[1].append(sname)

        def val(name):
            p = props.get(name)
            return None if p is None else p[2]

        ref = val("Reference")
        is_power = child(sym, "power") is not None or (ref or "").startswith("#")
        not_purchased = is_power or child_value(sym, "in_bom", "yes") == "no"
        is_net_tie = "nettie" in re.sub(r"[^a-z]", "", (sname + stem).lower())

        # Reference
        if ref is None:
            rep.add("sym-reference", rp, sym.line, "%s: Reference field is missing" % where)
        else:
            rline = props["Reference"].line
            if is_power:
                if ref not in POWER_REFERENCES:
                    rep.add("sym-reference", rp, rline, "%s: power symbol Reference '%s' must be #PWR or #FLG"
                            % (where, ref))
            elif ref.upper() == "IC":
                rep.add("sym-reference", rp, rline, "%s: Reference 'IC' is not allowed, integrated circuits use 'U'"
                        % where)
            elif re.search(r"\d", ref):
                rep.add("sym-reference", rp, rline, "%s: Reference '%s' must be the bare prefix without a "
                        "designator number (e.g. '%s')" % (where, ref, re.sub(r"[\d?]+$", "", ref) or "U"))
            elif ref not in ALLOWED_REFERENCES and not (is_net_tie and ref == NET_TIE_REFERENCE):
                rep.add("sym-reference", rp, rline, "%s: Reference '%s' is not an allowed prefix (%s)"
                        % (where, ref, " ".join(sorted(ALLOWED_REFERENCES))))

        # Datasheet
        ds = val("Datasheet")
        if ds is None or ds.strip() in ("", "~"):
            rep.add("sym-datasheet", rp, props["Datasheet"].line if "Datasheet" in props else sym.line,
                    "%s: Datasheet field is blank; link the manufacturer datasheet or product page" % where)

        # Description
        desc = val("Description")
        if desc is None or not desc.strip():
            rep.add("sym-description", rp, props["Description"].line if "Description" in props else sym.line,
                    "%s: Description is empty" % where)

        if not not_purchased:
            man = val("Manufacturer")
            if man is None:
                rep.add("sym-manufacturer", rp, sym.line, "%s: Manufacturer field is missing" % where)
            elif not man.strip() or man.strip() in ("-", "~"):
                rep.add("sym-manufacturer-empty", rp, props["Manufacturer"].line,
                        "%s: Manufacturer field is empty" % where)
            mpn = val("Manufacturer Number")
            if mpn is None or not mpn.strip() or mpn.strip() in ("-", "~"):
                rep.add("sym-manufacturer-number", rp,
                        props["Manufacturer Number"].line if "Manufacturer Number" in props else sym.line,
                        "%s: Manufacturer Number field is %s" % (where, "missing" if mpn is None else "empty"))

        # Keywords
        kw = val("ki_keywords")
        if kw is None or not kw.strip():
            if not is_power:
                rep.add("sym-keywords", rp, sym.line, "%s: ki_keywords is empty" % where)
        else:
            problems = []
            if kw != kw.lower():
                problems.append("not lowercase")
            if kw != kw.strip():
                problems.append("leading/trailing spaces")
            if "  " in kw:
                problems.append("doubled spaces")
            if problems:
                rep.add("sym-keywords", rp, props["ki_keywords"].line,
                        "%s: ki_keywords '%s' (%s)" % (where, kw, ", ".join(problems)))

        # Footprint linkage
        fp = val("Footprint")
        filters = val("ki_fp_filters")
        if not is_power:
            if (fp is None or not fp.strip()) and (filters is None or not filters.strip()):
                rep.add("sym-footprint-linkage", rp, props["Footprint"].line if "Footprint" in props else sym.line,
                        "%s: Footprint is blank and ki_fp_filters is empty; pre-link a footprint or add filters"
                        % where)
        if fp and fp.strip():
            fpl = props["Footprint"].line
            if ":" not in fp:
                rep.add("sym-footprint-format", rp, fpl,
                        "%s: Footprint '%s' should be LibraryNickname:FootprintName" % (where, fp))
            else:
                nick, fname = fp.split(":", 1)
                if nick.startswith(LIB_PREFIX) or nick.lower().startswith("metupowerlab"):
                    avail = footprints_in_lib(nick, lib_root)
                    if avail is None:
                        rep.add("sym-footprint-ref", rp, fpl, "%s: Footprint '%s' refers to library '%s' which "
                                "does not exist in footprints/" % (where, fp, nick))
                    elif fname not in avail:
                        rep.add("sym-footprint-ref", rp, fpl, "%s: Footprint '%s' not found in footprints/%s.pretty"
                                % (where, fp, nick))
        if filters and filters.strip():
            for flt in filters.split():
                if ":" not in flt:
                    continue
                nick, pat = flt.split(":", 1)
                if not nick.startswith("METUPowerLab"):
                    continue
                avail = footprints_in_lib(nick, lib_root)
                if avail is None or not any(fnmatch.fnmatchcase(n, pat) for n in avail):
                    rep.add("sym-fp-filter", rp, props["ki_fp_filters"].line,
                            "%s: ki_fp_filters entry '%s' matches no footprint in footprints/" % (where, flt))

        # Hidden / visible fields
        for fname in ("Footprint", "Datasheet", "Description"):
            p = props.get(fname)
            if p is not None and not _prop_hidden(p):
                rep.add("sym-hidden-fields", rp, p.line, "%s: %s field must be hidden (hide yes)" % (where, fname))
        visible = [n for n, p in props.items()
                   if n not in ("Reference", "Value", "Footprint", "Datasheet", "Description")
                   and not n.startswith("ki_") and not _prop_hidden(p)]
        if visible:
            rep.add("sym-visible-fields", rp, props[visible[0]].line,
                    "%s: field(s) %s are visible; only Reference and Value should be shown"
                    % (where, ", ".join("'%s'" % v for v in visible)))
        if not is_power:
            for fname in ("Reference", "Value"):
                p = props.get(fname)
                if p is not None and _prop_hidden(p):
                    rep.add("sym-visible-fields", rp, p.line, "%s: %s should be visible" % (where, fname))

        # Flags
        if not is_power:
            bad = []
            for flag, want in (("in_bom", "yes"), ("on_board", "yes"), ("exclude_from_sim", "no")):
                got = child_value(sym, flag, want)
                if got != want:
                    bad.append("(%s %s)" % (flag, got))
            if bad:
                rep.add("sym-flags", rp, sym.line, "%s: %s; expected (in_bom yes) (on_board yes) "
                        "(exclude_from_sim no) unless there is a specific reason" % (where, " ".join(bad)))

        # Reference / Value text size
        for fname in ("Reference", "Value"):
            p = props.get(fname)
            if p is None:
                continue
            size, _ = _font_size(p)
            if len(size) < 2 or not (feq(size[0], 1.27) and feq(size[1], 1.27)):
                rep.add("sym-text-size", rp, p.line, "%s: %s text size %s, expected (size 1.27 1.27)"
                        % (where, fname, " ".join("%g" % s for s in size) or "missing"))

        # Body rectangles
        issues = []
        first_line = None
        for rect in walk(sym, "rectangle"):
            stroke = child(rect, "stroke")
            w = numbers(child(stroke, "width")) if stroke is not None else []
            fill_type = child_value(child(rect, "fill"), "type") if child(rect, "fill") is not None else None
            if w and not feq(w[0], 0):
                issues.append("stroke width %g" % w[0])
                first_line = first_line or rect.line
            if fill_type not in (None, "background", "none"):
                issues.append("fill %s" % fill_type)
                first_line = first_line or rect.line
        if issues:
            rep.add("sym-body-style", rp, first_line, "%s: body rectangle %s; expected (stroke (width 0)) and fill "
                    "background (or none for connectors/terminals/shunts)" % (where, ", ".join(sorted(set(issues)))))

        # Pin grid
        for pin in walk(sym, "pin"):
            at = child(pin, "at")
            xy = numbers(at)
            if len(xy) < 2:
                continue
            if not (_on_grid(xy[0]) and _on_grid(xy[1])):
                num = child(pin, "number")
                pnum = num[1] if num is not None and len(num) > 1 else "?"
                rep.add("sym-pin-grid", rp, pin.line, "%s: pin %s at (%g, %g) is not on the 1.27 mm grid"
                        % (where, pnum, xy[0], xy[1]))

    for fname, (line, syms, sims) in near_dups.items():
        others = "; ".join("'%s' (used %d times, %s)" % (o, field_index.counts.get(o, 0), why) for o, why in sims)
        shown = ", ".join("'%s'" % s for s in syms[:5]) + (" and %d more" % (len(syms) - 5) if len(syms) > 5 else "")
        rep.add("field-name-near-duplicate", rp, line,
                "field '%s' (in %s) looks like a near-duplicate of %s; reuse the existing spelling"
                % (fname, shown, others))
    return len(symbols)


# --------------------------------------------------------------------------
# Footprint checks
# --------------------------------------------------------------------------

SILK_LAYERS = ("F.SilkS", "B.SilkS")
CRTYD_LAYERS = ("F.CrtYd", "B.CrtYd")
GRAPHIC_HEADS = ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly", "fp_curve")


def _stroke_width(node):
    stroke = child(node, "stroke")
    w = numbers(child(stroke, "width")) if stroke is not None else []
    if not w:
        w = numbers(child(node, "width"))
    return w[0] if w else None


def _fmt_list(items, limit=8):
    items = list(items)
    s = ", ".join(items[:limit])
    if len(items) > limit:
        s += ", ... (%d total)" % len(items)
    return s


class Pad(object):
    def __init__(self, node):
        self.node = node
        self.line = node.line
        self.number = node[1] if len(node) > 1 and isinstance(node[1], str) else ""
        self.type = node[2] if len(node) > 2 and isinstance(node[2], str) else ""
        self.shape = node[3] if len(node) > 3 and isinstance(node[3], str) else ""
        self.size = numbers(child(node, "size"))
        d = numbers(child(node, "drill"))
        self.drill = d[0] if d else None
        layers = child(node, "layers")
        self.layers = atoms(layers) if layers is not None else []
        m = numbers(child(node, "solder_mask_margin"))
        self.mask_margin = m[0] if m else None
        self.remove_unused = child_value(node, "remove_unused_layers")

    def label(self):
        return "'%s'" % self.number if self.number else "(unnumbered)"


_checked_pretty = set()


def check_footprint_file(path, rep):
    rp = rel(path)
    fname = os.path.basename(path)
    stem = fname[:-len(".kicad_mod")]
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))

    if not parent.endswith(".pretty"):
        rep.add("fp-file-name", rp, 1, "footprint file is not inside a .pretty library folder")
    else:
        key = os.path.dirname(os.path.abspath(path))
        if key not in _checked_pretty:
            _checked_pretty.add(key)
            check_lib_name(parent[:-len(".pretty")], rel(key), rep, "Footprint library")
    if " " in fname:
        rep.add("fp-file-name", rp, 1, "file name '%s' contains spaces; use underscores" % fname)
    if stem.lower().startswith("untitled"):
        rep.add("fp-file-name", rp, 1, "footprint still has KiCad's default name '%s'; rename it to describe the part"
                % fname)

    root = read_and_parse(path, rep, ("footprint", "module"))
    if root is None:
        return
    name = root[1] if len(root) > 1 and isinstance(root[1], str) else ""
    if name.split(":", 1)[-1] != stem:
        rep.add("fp-name-mismatch", rp, root.line, "footprint name '%s' differs from file name '%s'" % (name, stem))

    attr = child(root, "attr")
    attr_tokens = atoms(attr) if attr is not None else []
    attr_type = "smd" if "smd" in attr_tokens else ("through_hole" if "through_hole" in attr_tokens else None)
    board_only = "board_only" in attr_tokens

    # 3D models
    models = children(root, "model")
    for model in models:
        mpath = model[1] if len(model) > 1 and isinstance(model[1], str) else ""
        if not mpath.startswith(MODEL_VAR):
            if mpath.startswith("${") or mpath.startswith("$("):
                rep.add("fp-3d-model-var", rp, model.line, "3D model path '%s' should use ${METUPOWERLAB_3D}/"
                        "Category/Subcategory/file.step (copy the model into 3dmodels/powerlab.3dshapes)" % mpath)
            else:
                kind = "hardcoded absolute" if re.match(r"([A-Za-z]:|/|\\)", mpath) else "relative"
                rep.add("fp-3d-model-path", rp, model.line, "3D model path '%s' is a %s path that only works on "
                        "one machine; use ${METUPOWERLAB_3D}/Category/Subcategory/file.step" % (mpath, kind))
        else:
            target = os.path.join(library_root(path), "3dmodels", "powerlab.3dshapes",
                                  *mpath[len(MODEL_VAR):].split("/"))
            if not os.path.isfile(target):
                rep.add("fp-3d-model-missing", rp, model.line, "3D model '%s' not found at %s"
                        % (mpath, rel(target)))
    pads = [Pad(p) for p in children(root, "pad")]
    if not models and pads and not board_only:
        rep.add("fp-3d-model-none", rp, root.line, "footprint has no (model ...) 3D model")

    # attr vs pad types
    smd_pads = [p for p in pads if p.type == "smd"]
    th_pads = [p for p in pads if p.type == "thru_hole"]
    smd_numbers = set(p.number for p in smd_pads if p.number)
    thermal_vias = [p for p in th_pads if p.number and p.number in smd_numbers]
    th_signal = [p for p in th_pads if p not in thermal_vias]
    expected = None
    if smd_pads and not th_signal:
        expected = ("smd",)
    elif th_signal and not smd_pads:
        expected = ("through_hole",)
    elif smd_pads and th_signal:
        expected = ("smd", "through_hole")
    if expected and attr_type not in expected:
        rep.add("fp-attr", rp, attr.line if attr is not None else root.line,
                "(attr %s) does not match the pads: %d smd and %d thru_hole signal pad(s) -> expected (attr %s)"
                % (" ".join(attr_tokens) or "missing", len(smd_pads), len(th_signal), " or ".join(expected)))

    # solder mask margin
    bad_mask = [p for p in pads if not feq(p.mask_margin, 0.1)]
    if bad_mask:
        rep.add("fp-pad-mask-margin", rp, bad_mask[0].line, "%d pad(s) without (solder_mask_margin 0.1): %s"
                % (len(bad_mask), _fmt_list("%s=%s" % (p.label(), "missing" if p.mask_margin is None
                                                       else "%g" % p.mask_margin) for p in bad_mask)))

    # SMD pad shape
    non_rect = [p for p in smd_pads if p.shape != "rect"]
    if non_rect:
        shapes = Counter(p.shape for p in non_rect)
        rep.add("fp-smd-pad-shape", rp, non_rect[0].line, "%d SMD pad(s) are not rect (%s); use rect unless "
                "there is a specific reason" % (len(non_rect), ", ".join("%s x%d" % kv for kv in shapes.items())))

    # thermal vias
    bad_vias = []
    for p in thermal_vias:
        probs = []
        if p.shape != "circle":
            probs.append("shape %s" % p.shape)
        if len(p.size) < 2 or not (feq(p.size[0], 0.5) and feq(p.size[1], 0.5)):
            probs.append("size %s" % " ".join("%g" % s for s in p.size))
        if not feq(p.drill, 0.3):
            probs.append("drill %s" % ("missing" if p.drill is None else "%g" % p.drill))
        if set(p.layers) != {"*.Cu", "*.Mask"}:
            probs.append("layers %s" % " ".join(p.layers))
        if p.remove_unused != "no":
            probs.append("remove_unused_layers %s" % (p.remove_unused or "missing"))
        if probs:
            bad_vias.append((p, probs))
    if bad_vias:
        summary = Counter(pr for _, probs in bad_vias for pr in probs)
        rep.add("fp-thermal-via", rp, bad_vias[0][0].line, "%d thermal via(s) deviate from thru_hole circle size 0.5 "
                "drill 0.3 layers *.Cu *.Mask remove_unused_layers no: %s"
                % (len(bad_vias), ", ".join("%s (x%d)" % kv for kv in summary.items())))
    if smd_pads:
        orphan = [p for p in th_signal if p.drill is not None and p.drill <= 0.4 + EPS
                  and p.size and max(p.size) <= 0.8 + EPS]
        if orphan:
            rep.add("fp-thermal-via-number", rp, orphan[0].line, "%d via-like thru_hole pad(s) with number(s) %s do "
                    "not match any SMD pad; give thermal vias the number of the pad they sit under"
                    % (len(orphan), _fmt_list(sorted(set(p.label() for p in orphan)))))

    # np_thru_hole used for signals
    npth_numbered = [p for p in pads if p.type == "np_thru_hole" and p.number]
    if npth_numbered:
        rep.add("fp-npth-signal", rp, npth_numbered[0].line, "np_thru_hole pad(s) %s have a pad number; NPTH is for "
                "unplated mechanical holes only" % _fmt_list(p.label() for p in npth_numbered))

    # graphics: silk width, courtyard
    silk_bad = Counter()
    silk_line = None
    crtyd = []
    for node in root[1:]:
        h = head(node)
        if h not in GRAPHIC_HEADS:
            continue
        layer = child_value(node, "layer")
        w = _stroke_width(node)
        if layer in SILK_LAYERS and h in ("fp_line", "fp_rect") and not feq(w, 0.1):
            silk_bad["%s width %s" % (h, "missing" if w is None else "%g" % w)] += 1
            silk_line = silk_line or node.line
        if layer in CRTYD_LAYERS:
            crtyd.append((node, w))
    if silk_bad:
        rep.add("fp-silk-width", rp, silk_line, "silkscreen outline should be width 0.1, found: %s"
                % ", ".join("%s (x%d)" % kv for kv in silk_bad.items()))

    keepouts = [z for z in children(root, "zone") if any(True for _ in walk(z, "keepout"))]
    if crtyd or keepouts:
        parts = []
        if crtyd:
            parts.append("%d courtyard shape(s)" % len(crtyd))
        if keepouts:
            parts.append("%d keepout zone(s)" % len(keepouts))
        first = min([n.line for n, _ in crtyd] + [z.line for z in keepouts])
        rep.add("fp-courtyard-keepout", rp, first, "footprint has %s; courtyard/keepout is only allowed for "
                "RF/magnetic sensitive areas defined in the datasheet" % " and ".join(parts))
    bad_cy = [(n, w) for n, w in crtyd if not feq(w, 0.05)]
    if bad_cy:
        rep.add("fp-courtyard-width", rp, bad_cy[0][0].line, "%d courtyard shape(s) not width 0.05 (%s)"
                % (len(bad_cy), ", ".join(sorted(set("missing" if w is None else "%g" % w for _, w in bad_cy)))))

    # Reference / Value text
    texts = []
    for prop in children(root, "property"):
        if len(prop) > 1 and prop[1] in ("Reference", "Value"):
            texts.append((prop[1], prop))
    for t in children(root, "fp_text"):
        if len(t) > 2 and t[1] in ("reference", "value"):
            texts.append((t[1].capitalize(), t))
        elif len(t) > 2 and t[1] == "user" and t[2] == "${REFERENCE}" and child_value(t, "layer") in SILK_LAYERS:
            texts.append(("Reference", t))
    if not pads and board_only:
        texts = []  # graphics/logos: no reference designator conventions
    for kind, node in texts:
        size, thick = _font_size(node)
        want_t = 0.1 if kind == "Reference" else 0.15
        if len(size) < 2 or not (feq(size[0], 1) and feq(size[1], 1)) or not feq(thick, want_t):
            rule = "fp-ref-text" if kind == "Reference" else "fp-value-text"
            rep.add(rule, rp, node.line, "%s text is size %s thickness %s; expected (size 1 1) (thickness %g)"
                    % (kind, " ".join("%g" % s for s in size) or "missing",
                       "missing" if thick is None else "%g" % thick, want_t))


def check_pretty_dir(path, rep):
    key = os.path.abspath(path)
    if key not in _checked_pretty:
        _checked_pretty.add(key)
        check_lib_name(os.path.basename(key)[:-len(".pretty")], rel(path), rep, "Footprint library")
    files = sorted(f for f in os.listdir(path) if f.endswith(".kicad_mod"))
    for f in files:
        check_footprint_file(os.path.join(path, f), rep)
    return len(files)


# --------------------------------------------------------------------------
# Target selection
# --------------------------------------------------------------------------

def all_targets():
    syms = sorted(os.path.join(SYMBOLS_DIR, f) for f in os.listdir(SYMBOLS_DIR) if f.endswith(".kicad_sym"))
    pretties = sorted(os.path.join(FOOTPRINTS_DIR, d) for d in os.listdir(FOOTPRINTS_DIR)
                      if d.endswith(".pretty") and os.path.isdir(os.path.join(FOOTPRINTS_DIR, d)))
    return syms, pretties, []


def changed_targets(base):
    cmd = ["git", "-C", REPO_ROOT, "diff", "-z", "--name-only", "--diff-filter=AMR", base + "...HEAD", "--"]
    try:
        out = subprocess.check_output(cmd)
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.stderr.write("error: could not run %s: %s\n" % (" ".join(cmd), exc))
        sys.exit(2)
    names = [n.decode("utf-8", "surrogateescape") for n in out.split(b"\0") if n]
    syms, mods, pretties = [], [], []
    for n in names:
        full = os.path.join(REPO_ROOT, *n.split("/"))
        if n.endswith(".kicad_sym") and os.path.isfile(full):
            syms.append(full)
        elif n.endswith(".kicad_mod") and os.path.isfile(full):
            mods.append(full)
    return sorted(syms), pretties, sorted(mods)


def classify_paths(paths):
    syms, pretties, mods = [], [], []
    for p in paths:
        p = os.path.normpath(p)
        if os.path.isdir(p):
            if p.endswith(".pretty"):
                pretties.append(p)
            else:
                for dirpath, dirnames, filenames in os.walk(p):
                    for d in sorted(dirnames):
                        if d.endswith(".pretty"):
                            pretties.append(os.path.join(dirpath, d))
                    dirnames[:] = [d for d in dirnames if not d.endswith(".pretty") and not d.startswith(".")]
                    syms.extend(os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(".kicad_sym"))
        elif os.path.isfile(p) and p.endswith(".kicad_sym"):
            syms.append(p)
        elif os.path.isfile(p) and p.endswith(".kicad_mod"):
            mods.append(p)
        else:
            sys.stderr.write("error: '%s' is not a .kicad_sym file, .kicad_mod file or directory\n" % p)
            sys.exit(2)
    return syms, pretties, mods


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Check METU Power Lab KiCad libraries against DesignRules.md")
    ap.add_argument("paths", nargs="*", help=".kicad_sym files, .kicad_mod files, .pretty folders or directories")
    ap.add_argument("--all", action="store_true", help="check the whole library (symbols/ and footprints/)")
    ap.add_argument("--changed", metavar="BASE_REF", help="check files added/modified/renamed vs BASE_REF...HEAD")
    ap.add_argument("-q", "--quiet", action="store_true", help="do not print individual warnings")
    ap.add_argument("--exit-zero", action="store_true", help="always exit 0 (report only)")
    ap.add_argument("--list-rules", action="store_true", help="list the rules and their severity, then exit")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    if args.list_rules:
        for rid, (sev, desc) in RULES.items():
            print("%-26s %-8s %s" % (rid, sev.upper(), desc))
        return 0

    if sum(bool(x) for x in (args.paths, args.all, args.changed)) != 1:
        ap.error("give either paths, --all or --changed BASE_REF")

    if args.all:
        syms, pretties, mods = all_targets()
    elif args.changed:
        syms, pretties, mods = changed_targets(args.changed)
    else:
        syms, pretties, mods = classify_paths(args.paths)

    rep = Reporter()
    if not (syms or pretties or mods):
        print("No symbol or footprint library files to check.")
        return 0

    # Library-wide field-name index: every repo symbol library plus the targets.
    trees = {}
    field_index = FieldIndex()
    index_files = set(os.path.abspath(p) for p in syms)
    if os.path.isdir(SYMBOLS_DIR):
        index_files.update(os.path.join(SYMBOLS_DIR, f) for f in os.listdir(SYMBOLS_DIR) if f.endswith(".kicad_sym"))
    target_set = set(os.path.abspath(p) for p in syms)
    for f in sorted(index_files):
        sink = rep if f in target_set else Reporter()
        tree = read_and_parse(f, sink, ("kicad_symbol_lib",))
        if tree is not None:
            field_index.add_tree(tree)
        if f in target_set:
            trees[f] = tree

    n_symbols = 0
    for s in syms:
        a = os.path.abspath(s)
        if trees.get(a) is not None:
            n_symbols += check_symbol_file(s, rep, field_index, tree=trees[a])
        else:
            check_lib_name(os.path.basename(s)[:-len(".kicad_sym")], rel(s), rep, "Symbol library")
    n_fp = 0
    for p in pretties:
        n_fp += check_pretty_dir(p, rep)
    for m in mods:
        check_footprint_file(m, rep)
        n_fp += 1

    report(rep, args, len(syms), n_symbols, n_fp)
    if rep.count(ERROR) and not args.exit_zero:
        return 1
    return 0


def report(rep, args, n_sym_files, n_symbols, n_fp):
    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    findings = sorted(rep.findings, key=lambda f: (f.path, f.line, f.severity != ERROR, f.rule))
    for f in findings:
        if args.quiet and f.severity != ERROR:
            continue
        if gha:
            print("::%s file=%s,line=%d,title=%s::%s" % (f.severity, _gh_escape_prop(f.path), f.line,
                                                         _gh_escape_prop("[%s]" % f.rule),
                                                         _gh_escape_data(f.message)))
        else:
            print("%-7s %s:%d: [%s] %s" % (f.severity.upper(), f.path, f.line, f.rule, f.message))

    per_rule = defaultdict(Counter)
    for f in rep.findings:
        per_rule[f.rule][f.severity] += 1
    n_err, n_warn = rep.count(ERROR), rep.count(WARNING)

    lines = ["", "Summary: checked %d symbol librar%s (%d symbols) and %d footprint(s)"
             % (n_sym_files, "y" if n_sym_files == 1 else "ies", n_symbols, n_fp)]
    for rid in RULES:
        if rid in per_rule:
            c = per_rule[rid]
            lines.append("  %-26s %4d error(s) %4d warning(s)" % (rid, c[ERROR], c[WARNING]))
    lines.append("Total: %d error(s), %d warning(s)" % (n_err, n_warn))
    if n_err:
        lines.append("Errors must be fixed before merging; see HowToCreateNewDesign/DesignRules.md.")
    print("\n".join(lines))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if gha and summary_path:
        md = ["## Library standards check", "",
              "Checked %d symbol libraries (%d symbols) and %d footprints: **%d error(s)**, %d warning(s)."
              % (n_sym_files, n_symbols, n_fp, n_err, n_warn), ""]
        if per_rule:
            md += ["| Rule | Errors | Warnings | Description |", "|---|---:|---:|---|"]
            for rid, (sev, desc) in RULES.items():
                if rid in per_rule:
                    md.append("| `%s` | %d | %d | %s |" % (rid, per_rule[rid][ERROR], per_rule[rid][WARNING], desc))
        md.append("")
        md.append("Rules: `HowToCreateNewDesign/DesignRules.md`. Run locally with "
                  "`python tools/check_library.py <files>`.")
        try:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(md) + "\n")
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())

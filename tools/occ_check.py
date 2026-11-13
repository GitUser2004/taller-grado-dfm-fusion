"""External topological check of a STEP file with the OpenCASCADE kernel.

Fusion's API has no "Check body", so this is the intermediate tool for the
topological-validity rule: Fusion exports STEP -> this script validates it.

Usage:  python tools/occ_check.py part.step     (needs: pip install cadquery-ocp)
Prints JSON: overall validity, per-face/edge problems, shape statistics.
"""

import json
import sys

from OCP.BRep import BRep_Tool
from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError
from OCP.IFSelect import IFSelect_RetDone
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds, ShapeAnalysis_ShapeTolerance
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp


def count(shape, kind):
    exp, n = TopExp_Explorer(shape, kind), 0
    while exp.More():
        n += 1
        exp.Next()
    return n


def sub_shapes(shape, kind):
    exp = TopExp_Explorer(shape, kind)
    while exp.More():
        yield exp.Current()
        exp.Next()


def statuses(analyzer, sub):
    # The per-status list (NCollection_List<BRepCheck_Status>) is not wrapped by OCP,
    # so each sub-shape is validated with its own analyzer instead.
    return [] if BRepCheck_Analyzer(sub).IsValid() else ['invalid']


def check(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(path) != IFSelect_RetDone:
        return {'file': path, 'read_ok': False}
    reader.TransferRoots()
    shape = reader.OneShape()

    analyzer = BRepCheck_Analyzer(shape)
    problems = []
    for kind, label in ((TopAbs_FACE, 'face'), (TopAbs_EDGE, 'edge'), (TopAbs_VERTEX, 'vertex')):
        for i, sub in enumerate(sub_shapes(shape, kind)):
            st = statuses(analyzer, sub)
            if st:
                problems.append({'type': label, 'index': i, 'status': st})

    free = ShapeAnalysis_FreeBounds(shape)  # open boundaries = holes in the skin
    tol = ShapeAnalysis_ShapeTolerance()
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    tiny_edges = sum(1 for e in sub_shapes(shape, TopAbs_EDGE)
                     if not BRep_Tool.Degenerated_s(TopoDS.Edge(e)) and _edge_len(e) < 1e-3)  # < 0.001 mm
    return {
        'file': path, 'read_ok': True,
        'valid': bool(analyzer.IsValid()),
        'solids': count(shape, TopAbs_SOLID), 'shells': count(shape, TopAbs_SHELL),
        'faces': count(shape, TopAbs_FACE), 'edges': count(shape, TopAbs_EDGE),
        'free_closed_wires': count(free.GetClosedWires(), TopAbs_EDGE),
        'free_open_wires': count(free.GetOpenWires(), TopAbs_EDGE),
        'tiny_edges(<0.001mm)': tiny_edges,
        'max_tolerance_mm': round(tol.Tolerance(shape, 1), 6),
        'volume_mm3': round(props.Mass(), 3),
        'problems': problems,
    }


def _edge_len(edge):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(edge, p)
    return p.Mass()


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1]), indent=2))

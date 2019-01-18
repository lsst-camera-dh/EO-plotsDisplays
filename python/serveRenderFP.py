from __future__ import print_function
from renderFocalPlane import renderFocalPlane
from bokeh.plotting import curdoc
from bokeh.io import export_png
from bokeh.layouts import row, layout

import argparse

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import base64
import pandas

"""
Driver for renderFocalPlane.py - defines interactors and requests the display to be produced
"""

parser = argparse.ArgumentParser(
    description='Create heatmap of Camera EO test data quantities.')

parser.add_argument('-t', '--test', default="gain", help="test quantity to display")
parser.add_argument('-r', '--run', default="6374D", help="run number")
parser.add_argument('--hook', default=None, help="name of user hook module to load")
parser.add_argument('-p', '--png', default=None, help="file spec for output png of heatmap")
parser.add_argument('-e', '--emulate', default=None, help="file spec for emulation config")
parser.add_argument('-m', '--mode', default="full_FP", help="heatmap viewing mode")
parser.add_argument('-d', '--db', default="Prod", help="eT database")

p_args = parser.parse_args()

rFP = renderFocalPlane(db=p_args.db)

if p_args.emulate is not None:
    raft_list, run_list = rFP.parse_emulation_config(p_args.emulate)
    # set a default emulation config

# don't set single mode yet!

rFP.set_mode(p_args.mode)

if p_args.hook is not None:
    mod = __import__(p_args.hook)
    rFP.user_hook = mod.hook

# start up with a nominal run number and test name

ini_run = p_args.run
ini_test = p_args.test

if p_args.run is not None:
    ini_run = p_args.run
if p_args.test is not None:
    ini_test = p_args.test

m_lay = rFP.render(run=ini_run, testq=ini_test)

if p_args.png is not None:
    export_png(rFP.map_layout, p_args.png)

rFP.layout = layout(rFP.interactors, rFP.map_layout)

curdoc().add_root(rFP.layout)
curdoc().title = "Focal Plane Heat Map"

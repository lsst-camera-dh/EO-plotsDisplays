from __future__ import print_function
from renderFocalPlane import renderFocalPlane
from bokeh.models import TapTool, CustomJS, ColumnDataSource, CDSView, BooleanFilter, GroupFilter,Label
from bokeh.plotting import figure, output_file, show, save, curdoc
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.widgets import TextInput, Dropdown, Slider, Button
from bokeh.io import export_png
from exploreRaft import exploreRaft
import sys
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
parser.add_argument('-r', '--run', default=None, help="run number")
parser.add_argument('--hook', default=None, help="name of user hook module to load")
parser.add_argument('-p', '--png', default=None, help="file spec for output png of heatmap")
parser.add_argument('-e', '--emulate', default=None, help="file spec for emulation config")
parser.add_argument('-m', '--mode', default="full_FP", help="heatmap viewing mode")
parser.add_argument('-d', '--db', default="Prod", help="eT database")

p_args = parser.parse_args()

rFP = renderFocalPlane(db=p_args.db)

eR = rFP.eR

raft_list = [["LCA-11021_RTM-003_ETU2", "R10"], ["LCA-11021_RTM-005", "R22"]]
#    raft_list = [["LCA-11021_RTM-003_ETU2", "R10"]]
run_list = [5731, 6259]
rFP.set_emulation(raft_list, run_list)

# don't set single mode yet!

rFP.set_mode(p_args.mode)

if p_args.hook is not None:
     mod = __import__(p_args.hook)
     rFP.user_hook = mod.hook

def tap_input(attr, old, new):
    """
    Handle the click in the heatmap. Does nothing if in full Focal Plane mode
    :param attr:
    :param old: previous value of rFP.source
    :param new: new value of rFP.source
    :return: nothing
    """
    # The index of the selected glyph is : new['1d']['indices'][0]
    raft_name = rFP.source.data['raft_name'][new['1d']['indices'][0]]
    raft_slot = rFP.source.data['raft_slot'][new['1d']['indices'][0]]
    ccd_name = rFP.source.data['ccd_name'][new['1d']['indices'][0]]
    ccd_slot = rFP.source.data['ccd_slot'][new['1d']['indices'][0]]

    rFP.single_raft_name = [[raft_name, raft_slot]]
    if rFP.emulate is True:
        _, rFP.single_raft_run = rFP.get_emulated_raft_info(rFP.single_raft_name[0][0])
    else:
        rFP.single_raft_run = rFP.get_current_run

    if rFP.single_raft_mode is True:

        raft_menu = [(pair[1],pair[0]) for pair in raft_list]
        drop_raft = Dropdown(label="Select Raft",button_type="warning", menu=raft_menu)
        rFP.drop_raft = drop_raft
        drop_raft.on_change('value',update_dropdown_raft)
        interactors = layout(row(text_input, drop_test,drop_raft, drop_modes), row(button, button_file))
        l_new = rFP.render(run=rFP.single_raft_run, testq=rFP.get_current_test())
        m_new = layout(interactors, l_new)
        m.children = m_new.children

    if rFP.single_ccd_mode is True:
        rFP.single_ccd_name =  [[ccd_name, ccd_slot, "Dummy REB"]]

        raftContents = eR.raftContents(raftName=rFP.single_raft_name[0][0])
        ccd_menu = [(tup[1]+': '+tup[0],tup[0]) for tup in raftContents]
        drop_ccd = Dropdown(label="Select CCD from " + rFP.single_raft_name[0][0][-7:], button_type="warning", menu=ccd_menu)
        rFP.drop_ccd = drop_ccd
        rFP.slot_mapping = {tup[0]:tup[1] for tup in raftContents}
        drop_ccd.on_change('value', update_dropdown_ccd)
        interactors = layout(row(text_input, drop_test,drop_ccd, drop_modes), row(button, button_file))
        l_new = rFP.render(run=rFP.single_raft_run, testq=rFP.get_current_test())
        m_new = layout(interactors, l_new)
        m.children = m_new.children


        #l_new = rFP.render(run=rFP.single_raft_run, testq=rFP.get_current_test())
        #m_new = layout(interactors, l_new)
        #m.children = m_new.children

def select_input(attr, old, new):
    """
    Handle the selections in the heatmap  or histogram.  Does nothing if
    not in full Focal Plane mode
    :param attr:
    :param old: previous value of rFP.source
    :param new: new value of rFP.source
    :return: nothing
    """

    if rFP.full_FP_mode is True:
    # The indices of the selected glyph is : new['1d']['indices']
        min = rFP.histsource.data['left'][new['1d']['indices'][0]]
        max = rFP.histsource.data['right'][new['1d']['indices'][-1]]
        booleans = [True if val >= min and val<=max else False for val in rFP.source.data['test_q']]
        view = CDSView(source=rFP.source, filters=[BooleanFilter(booleans)])
        l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test(),view=view)
        m_new = layout(interactors, l_new)
        m.children = m_new.children



rFP.tap_cb = tap_input
rFP.select_cb = select_input

# start up with a nominal run number and test name

ini_run =5731
ini_test = "gain"

if p_args.run is not None:
    ini_run = p_args.run
if p_args.test is not None:
    ini_test = p_args.test


l = rFP.render(run=ini_run, testq=ini_test)

# drop down menu of test names, taking the menu from rFP.menu_test
drop_test = Dropdown(label="Select test", button_type="warning", menu=rFP.menu_test)

# set up the dropdown menu for modes, along with available modes list
menu_modes = [("Full Focal Plane", "Full Focal Plane"), ("FP single raft", "FP single raft"),
              ("FP single CCD", "FP single CCD"), ("Solo Raft", "Solo Raft")]

drop_modes = Dropdown(label="Mode: " + menu_modes[rFP.current_mode][0], button_type="success",
                      menu=menu_modes)

# set up run number text box - disable it in emulate mode
text_input = TextInput(value=str(rFP.get_current_run()), title="Select Run")
if rFP.emulate is True:
    text_input.title="Select Run Disabled"

# define buttons to toggle emulation mode, and to fetch a config txt file
button = Button(label="Emulate Mode", button_type="success")
button_file = Button(label="Upload Emulation Config", button_type="success")

interactors = layout(row(text_input, drop_test, drop_modes), row(button, button_file))

m = layout(interactors, l)

if p_args.png is not None:
    export_png(l,p_args.png)

def update_dropdown_test(sattr, old, new):
    new_test = drop_test.value

    l_new = rFP.render(run=rFP.get_current_run(), testq=new_test)
    m_new = layout(interactors, l_new)
    m.children = m_new.children

def update_dropdown_ccd(sattr, old, new):
    ccd_name = rFP.drop_ccd.value
    ccd_slot = rFP.slot_mapping[ccd_name]
    rFP.single_ccd_name =  [[ccd_name, ccd_slot, "Dummy REB"]]
    interactors = layout(row(text_input, drop_test,rFP.drop_ccd, drop_modes), row(button, button_file))
    l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
    m_new = layout(interactors, l_new)
    m.children = m_new.children

def update_dropdown_raft(sattr, old, new):
    #Update from raft_list for now - need to add case where we have all rafts.
    raft_name = rFP.drop_raft.value
    raft_slot_mapping = {pair[0]:pair[1] for pair in raft_list}
    raft_slot = raft_slot_mapping[raft_name]
    rFP.single_raft_name = [[raft_name, raft_slot]]
    interactors = layout(row(text_input, drop_test,rFP.drop_raft, drop_modes), row(button, button_file))
    l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
    m_new = layout(interactors, l_new)
    m.children = m_new.children

drop_test.on_change('value', update_dropdown_test)

def update_dropdown_modes(sattr, old, new):
    new_mode = drop_modes.value

    rFP.single_raft_mode = False
    rFP.single_ccd_mode = False
    rFP.solo_raft_mode = False
    rFP.full_FP_mode = False

    if new_mode == "Full Focal Plane":
        rFP.full_FP_mode = True
        rFP.emulate = True  # no real run data yet!
        interactors = layout(row(text_input, drop_test,drop_modes), row(button, button_file))
        l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
        m_new = layout(interactors, l_new)
        m.children = m_new.children

    elif new_mode == "FP single raft":
        try:
            rFP.single_raft_mode = True
            raft_menu = [(pair[1],pair[0]) for pair in raft_list]
            drop_raft = Dropdown(label="Select Raft",button_type="warning", menu=raft_menu)
            rFP.drop_raft = drop_raft
            drop_raft.on_change('value',update_dropdown_raft)
            interactors = layout(row(text_input, drop_test,drop_raft, drop_modes), row(button, button_file))
            l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
            m_new = layout(interactors, l_new)
            m.children = m_new.children
        except IndexError:
            print('Click on a raft in the heat map.')

    elif new_mode == "FP single CCD":
        try:
            rFP.single_ccd_mode = True
            #if rFP.single_raft_name == []:
            #    rFP.single_raft_name = [raft_list[1]]
            raftContents = eR.raftContents(raftName=rFP.single_raft_name[0][0])
            ccd_menu = [(tup[1]+': '+tup[0],tup[0]) for tup in raftContents]
            print(ccd_menu)
            drop_ccd = Dropdown(label="Select CCD from " + rFP.single_raft_name[0][0][-7:], button_type="warning", menu=ccd_menu)
            rFP.drop_ccd = drop_ccd
            rFP.slot_mapping = {tup[0]:tup[1] for tup in raftContents}
            drop_ccd.on_change('value', update_dropdown_ccd)
            interactors = layout(row(text_input, drop_test,drop_ccd, drop_modes), row(button, button_file))
            l_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
            m_new = layout(interactors, l_new)
            m.children = m_new.children
        except IndexError:
            print('Click on a CCD in the heat map.')
            #box = Label(x=70, y=70, x_units='screen', y_units='screen',
            #     text='Click on CCD.', render_mode='css',
            #     border_line_color='black', border_line_alpha=1.0,
            #     background_fill_color='white', background_fill_alpha=1.0)
            #nteractors = layout(row(text_input, drop_test, drop_modes), row(button, button_file))
            #_new = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test(),box=box)
            #m_new = layout(interactors, l_new)
            #m.children = m_new.children
    # in solo mode, ensure run selecton is re-enabled
    elif new_mode == "Solo Raft":
        rFP.solo_raft_mode = True
        rFP.emulate = False
        button.label = "Run Mode"
        text_input.title= "Select Run"

    drop_modes.label = "Mode: " + new_mode

drop_modes.on_change('value', update_dropdown_modes)


def update_text_input(sattr, old, new):
    if rFP.emulate is False:
        text_input.title = "Select Run"
        new_run = text_input.value

        l_new_run = rFP.render(run=new_run, testq=rFP.get_current_test())
        m_new_run = layout(interactors, l_new_run)
        m.children = m_new_run.children
    else:
        text_input.title = "Select Run Disabled"


text_input.on_change('value', update_text_input)

def update_button():
    current_mode = rFP.emulate_raft_list
    new_mode = not current_mode

    rFP.emulate_raft_list = new_mode
    if new_mode is True:
        button.label = "Emulate Mode"
        l_new_run = rFP.render(run=rFP.get_current_run(), testq=rFP.get_current_test())
        m_new_run = layout(interactors, l_new_run)
        m.children = m_new_run.children

    else:
        button.label = 'Run Mode'

button.on_click(update_button)

# readining in the emulation config file depends on two callbacks - one triggering reading the file into the
# ColumnDataSource, coupled with looking for a change on the ColumnDataSource
file_source = ColumnDataSource({'file_contents':[], 'file_name':[]})

def file_callback(attr,old,new):
    filename = file_source.data['file_name']
    df = pandas.read_csv(filename[0], header=0, skipinitialspace=True)
    raft_frame = df.set_index('raft', drop=False)

    raft_col = raft_frame["raft"]
    raft_list = []
    run_list = []

    for raft in raft_col:

        slot = raft_frame.loc[raft, "slot"]
        run = raft_frame.loc[raft, "run"]
        raft_list.append([raft, slot])
        run_list.append(run)

    rFP.set_emulation(raft_list, run_list)

    l_new_run = rFP.render(run=rFP.current_run, testq=rFP.get_current_test())
    m_new_run = layout(interactors, l_new_run)
    m.children = m_new_run.children


file_source.on_change('data', file_callback)

button_file.callback = CustomJS(args=dict(file_source=file_source), code = """
function read_file(filename) {
    var reader = new FileReader();
    reader.onload = load_handler;
    reader.onerror = error_handler;
    // readAsDataURL represents the file's data as a base64 encoded string
    reader.readAsDataURL(filename);
}

function load_handler(event) {
    var b64string = event.target.result;
    file_source.data = {'file_contents' : [b64string], 'file_name':[input.files[0].name]};
    file_source.change.emit();
}

function error_handler(evt) {
    if(evt.target.error.name == "NotReadableError") {
        alert("Can't read file!");
    }
}

var input = document.createElement('input');
input.setAttribute('type', 'file');
input.onchange = function(){
    if (window.FileReader) {
        read_file(input.files[0]);
    } else {
        alert('FileReader is not supported in this browser');
    }
}
input.click();
""")


curdoc().add_root(m)
curdoc().title = "Focal Plane Heat Map"

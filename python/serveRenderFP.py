from __future__ import print_function
from renderFocalPlane import renderFocalPlane
from bokeh.models import TapTool, CustomJS, ColumnDataSource
from bokeh.plotting import figure, output_file, show, save, curdoc
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.widgets import TextInput, Dropdown, Slider, Button
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import base64
import pandas


rFP = renderFocalPlane()

raft_list = [["LCA-11021_RTM-003_ETU2", "R10"], ["LCA-11021_RTM-005", "R22"]]
#    raft_list = [["LCA-11021_RTM-003_ETU2", "R10"]]
run_list = [6259, 5731]
rFP.set_emulation(raft_list, run_list)

def get_bias(run):
    print ("called user hook with run ", str(run))
    fake_list = [i*1. for i in range(1,145) ]
    return fake_list

rFP.user_hook = get_bias

def tap_input(attr, old, new):
    # The index of the selected glyph is : new['1d']['indices'][0]
    if rFP.single_raft_mode is True:
        raft_name = rFP.source.data['raft_name'][new['1d']['indices'][0]]
        raft_slot = rFP.source.data['raft_slot'][new['1d']['indices'][0]]
        rFP.single_raft_name =  [[raft_name, raft_slot]]

        l_new = rFP.render(run=rFP.get_current_run(), testq='gain')
        m_new = layout(interactors, l_new)
        m.children = m_new.children


rFP.tap_cb = tap_input

l = rFP.render(run=5731, testq="gain")

drop_test = Dropdown(label="Select test", button_type="warning", menu=rFP.menu_test)

menu_modes = [("Full Focal Plane", "Full Focal Plane"), ("FP single raft", "FP single raft"),
              ("FP single CCD", "FP single CCD"), ("Solo Raft", "Solo Raft"),
              ("Solo CCD", "Solo CCD")]
drop_modes = Dropdown(label="Mode: Full Focal Plane", button_type="success", menu=menu_modes)

#slider = Slider(start=0, end=10, value=10, step=.1, title="Stuff")
text_input = TextInput(value=str(rFP.get_current_run()), title="Select Run")

button = Button(label="Emulate Mode", button_type="success")
button_file = Button(label="Upload Emulation Config", button_type="success")

interactors = layout(row(text_input, drop_test, drop_modes,button, button_file))

m = layout(interactors, l)


def update_dropdown_test(sattr, old, new):
    new_test = drop_test.value

    l_new = rFP.render(run=rFP.get_current_run(), testq=new_test)
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
        l_new = rFP.render(run=rFP.get_current_run(), testq='gain')
        m_new = layout(interactors, l_new)
        m.children = m_new.children

    elif new_mode == "FP single raft":
        rFP.single_raft_mode = True
    elif new_mode == "FP single CCD":
        rFP.single_ccd_mode = True
    elif new_mode == "Solo Raft":
        rFP.solo_raft_mode = True
        rFP.emulate_raft_list = False

    drop_modes.label = "Mode: " + new_mode

drop_modes.on_change('value', update_dropdown_modes)


def update_text_input(sattr, old, new):
    if rFP.emulate_raft_list is False:
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
    else:
        button.label = 'Run Mode'

button.on_click(update_button)


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
        print("raft, slot, run = ", raft, slot, run)
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

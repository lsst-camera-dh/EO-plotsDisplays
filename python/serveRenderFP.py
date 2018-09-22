from __future__ import print_function
from renderFocalPlane import renderFocalPlane
from bokeh.models import TapTool, CustomJS
from bokeh.plotting import figure, output_file, show, save, curdoc
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.widgets import TextInput, Dropdown, Slider, Button


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

interactors = layout(row(text_input, drop_test, drop_modes))

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

curdoc().add_root(m)
curdoc().title = "Focal Plane Heat Map"

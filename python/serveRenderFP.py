from __future__ import print_function
from renderFocalPlane import renderFocalPlane
from bokeh.models import ColumnDataSource, DataRange1d, Plot, LinearAxis, Grid, LogColorMapper
from bokeh.plotting import figure, output_file, show, save, curdoc
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.widgets import TextInput, Dropdown, Slider, Button


rFP = renderFocalPlane()

raft_list = [["LCA-11021_RTM-003_ETU2", "R10"], ["LCA-11021_RTM-005", "R22"]]
#    raft_list = [["LCA-11021_RTM-003_ETU2", "R10"]]
run_list = [6259, 5731]
rFP.set_emulation(raft_list, run_list)
rFP.set_single_raft(choice=True)

l = rFP.render(run=5731, testq="gain")

menu = [('Gain', 'gain'), ('Gain Error', 'gain_error'), ('PSF', 'psf_sigma'),
        ("Read Noise", 'read_noise'), ('System Noise', 'system_noise'),
        ('Total Noise', 'total_noise'), ('Bright Pixels', 'bright_pixels'),
        ('Bright Columns', 'bright_columns'), ('Dark Pixels', 'dark_pixels'),
        ('Dark Columns', 'dark_columns'), ("Traps", 'num_traps'),
        ('CTI Low Serial', 'cti_low_serial'), ('CTI High Serial', 'cti_high_serial'),
        ('CTI Low Parallel', 'cti_low_parallel'), ('CTI High Parallel', 'cti_high_parallel'),
        ('Dark Current 95CL', 'dark_current_95CL'),
        ('PTC gain', 'ptc_gain'), ('Pixel mean', 'pixel_mean'), ('Full Well', 'full_well'),
        ('Nonlinearity', 'max_frac_dev')]

drop = Dropdown(label="Select test", button_type="warning", menu=menu)

#slider = Slider(start=0, end=10, value=10, step=.1, title="Stuff")
text_input = TextInput(value=str(rFP.get_current_run()), title="Select Run")

button = Button(label="Single Raft Mode", button_type="success")

interactors = layout(row(text_input, drop, button))

m = layout(interactors, l)


def update_dropdown(sattr, old, new):
    new_test = drop.value

    l_new = rFP.render(run=rFP.get_current_run(), testq=new_test)
    m_new = layout(row(text_input, drop, button), l_new)
    m.children = m_new.children

drop.on_change('value', update_dropdown)

def update_text_input(sattr, old, new):
    new_run = text_input.value

    l_new_run = rFP.render(run=new_run, testq=rFP.get_current_test())
    m_new_run = layout(row(text_input, drop, button), l_new_run)
    m.children = m_new_run.children

text_input.on_change('value', update_text_input)

def update_button():
    current_mode = rFP.get_single_raft()
    new_mode = not current_mode

    rFP.set_single_raft(choice=new_mode)
    if new_mode is True:
        button.label = "Single Raft Mode"
    else:
        button.label = 'Focal Plane Mode'

button.on_click(update_button)


curdoc().add_root(m)
curdoc().title = "Focal Plane Heat Map"

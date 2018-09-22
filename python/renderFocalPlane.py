from __future__ import print_function
import numpy as np
from get_EO_analysis_results import get_EO_analysis_results
from exploreFocalPlane import exploreFocalPlane
from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection

from bokeh.models import ColumnDataSource, DataRange1d, Plot, LinearAxis, Grid, LogColorMapper, ColorBar, \
    LogTicker, BasicTicker, TapTool
from bokeh.plotting import figure, output_file, show, save, curdoc
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.widgets import TextInput, Dropdown
from bokeh.models.glyphs import Rect

"""
Create a rendering of the focal plane, composed of science and corner rafts, each made of sensors with 
their amplifiers.
"""

class renderFocalPlane():

    def __init__(self, db='Prod', server='Prod'):
        # define primitives for amps, sensors and rafts

        self.amp_width = 1/8.
        self.ccd_width = 1.
        self.raft_width = 3.

        self.single_raft_mode = False
        self.single_ccd_mode = False
        self.solo_raft_mode = False
        self.full_FP_mode = True
        self.emulate = False
        self.emulate_run_list = []
        self.emulated_runs = [0]*21

        self.single_raft_name = []
        self.single_raft_run = None
        self.single_ccd_name = []

        self.source = ColumnDataSource()
        self.current_run = 0
        self.current_test = ""
        self.EO_type = "I&T-Raft"

        self.user_hook = None
        self.tap_cb = None
        self.heatmap = None
        self.heatmap_rect = None

        self.emulate_raft_list = []

        self.menu_test = [('Gain', 'gain'), ('Gain Error', 'gain_error'), ('PSF', 'psf_sigma'),
                     ("Read Noise", 'read_noise'), ('System Noise', 'system_noise'),
                     ('Total Noise', 'total_noise'), ('Bright Pixels', 'bright_pixels'),
                     ('Bright Columns', 'bright_columns'), ('Dark Pixels', 'dark_pixels'),
                     ('Dark Columns', 'dark_columns'), ("Traps", 'num_traps'),
                     ('CTI Low Serial', 'cti_low_serial'), ('CTI High Serial', 'cti_high_serial'),
                     ('CTI Low Parallel', 'cti_low_parallel'), ('CTI High Parallel', 'cti_high_parallel'),
                     ('Dark Current 95CL', 'dark_current_95CL'),
                     ('PTC gain', 'ptc_gain'), ('Pixel mean', 'pixel_mean'), ('Full Well', 'full_well'),
                     ('Nonlinearity', 'max_frac_dev')]

        self.raft_slot_names = ["R14", "R24", "R34",
                                "R03", "R13", "R23", "R33", "R43",
                                "R02", "R12", "R22", "R32", "R42",
                                "R01", "R11", "R21", "R31", "R41",
                                "R10", "R20", "R30"
                                ]

        self.raft_is_there = [False] * 21
        self.installed_raft_names = [""] * 21

        self.raft_center_x = [-3., 0., 3.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -3., 0., 3.
                              ]
        self.raft_center_y = [6., 6., 6.,
                              3., 3., 3., 3., 3.,
                              0., 0., 0., 0., 0.,
                              -3., -3., -3., -3., -3.,
                              -6., -6., -6.
                              ]

        self.ccd_center_x = [-1., 0., 1.,
                             -1., 0., 1.,
                             -1., 0., 1.
                             ]
        self.ccd_center_y = [1., 1., 1.,
                             0., 0., 0.,
                             -1., -1., -1.
                             ]

        self.amp_center_y = [-self.ccd_width/2.-self.amp_width/2.+(j+1)/8. for j in range(8)]
        self.amp_center_y.extend([-self.ccd_width/2.-self.amp_width/2.+(j+1)/8. for j in range(8)])

        self.amp_center_x = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]
        self.amp_center_x.extend([-0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25])

        if server == 'Prod':
            pS = True
        else:
            pS = False
        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)

        self.eFP = exploreFocalPlane()
        self.eR = exploreRaft()
        self.get_EO = get_EO_analysis_results(db=db, server=server)

    def get_testq(self, run=None, testq=None):

        if self.emulate is True and (self.single_raft_mode is True or self.single_ccd_mode is True):
            run = self.single_raft_run

        if self.user_hook is not None and testq == "User":
            return self.user_hook(run=run)

        raft_list, data = self.get_EO.get_tests(site_type=self.EO_type, test_type=testq, run=run)
        res = self.get_EO.get_results(test_type=testq, data=data, device=raft_list)

        test_list = []
        for ccd in res:
            if self.single_ccd_mode is True and ccd != self.single_ccd_name[0][0]:
                continue
            test_list.extend(res[ccd])

        return test_list

    def get_raft_content(self):

        if self.emulate is False:
            if self.full_FP_mode is True:
                raft_list = self.eFP.focalPlaneContents()
            elif self.solo_raft_mode is True:
                run = self.current_run
                run_info = self.connect.getRunResults(run=run)
                raft_list = [[run_info['experimentSN'], "R22"]]
                print ("testq ", raft_list, run)
            elif self.single_raft_mode is True or self.single_ccd_mode is True:
                print ("raft content ", raft_list)
                raft_list = self.single_raft_name
        else:
            raft_list = self.emulate_raft_list
            if self.single_raft_mode is True or self.single_ccd_mode is True:
                print ("raft content ", raft_list)
                raft_list = self.single_raft_name

        for j in range(21):
            self.installed_raft_names[j] = ""
            self.raft_is_there[j] = False

        for i in range(len(self.raft_slot_names)):
            for raft in range(len(raft_list)):
                if self.raft_slot_names[i] == raft_list[raft][1]:
                    self.raft_is_there[i] = True
                    self.installed_raft_names[i] = raft_list[raft][0]
                    if self.emulate is True:
                        self.emulated_runs[i] = self.emulate_run_list[raft]
                    break

        return raft_list

    def set_emulation(self, raft_list, run_list):

        self.emulate = True

        self.emulate_raft_list = raft_list
        self.emulate_run_list = run_list

        self.menu_test.append(("User Supplied", "User"))

    def disable_emulation(self):

        self.emulate = False
        self.menu_test.remove(("User Supplied", "User"))

    def get_current_run(self):
        return self.current_run

    def get_current_test(self):
        return self.current_test

    def get_emulated_raft_info(self, raft=None):
        run = None
        slot = None
        for idx, r in enumerate(self.emulate_raft_list):
            if raft == r[0]:
                slot = r[1]
                run = self.emulate_run_list[idx]
        return slot, run


    def render(self, run=None, testq=None):

        self.current_run = run
        self.current_test = testq

        run_sum = self.connect.getRunSummary(run=run)
        if "Integration" in run_sum["subsystem"]:
            self.EO_type = "I&T-Raft"
        else:
            self.EO_type = "BNL-Raft"

        raft_list = self.get_raft_content()

        TOOLS = "pan,wheel_zoom,reset,hover,save,tap"
        color_mapper = LogColorMapper(palette=palette)
        color_bar = ColorBar(color_mapper=color_mapper, ticker=LogTicker(), label_standoff=12,
                            border_line_color=None, location=(0,0))

        fig_title = "Focal Plane"
        if self.single_raft_mode is True or self.solo_raft_mode is True:
            fig_title = self.single_raft_name[0][0]
        elif self.single_ccd_mode is True:
            fig_title = self.single_ccd_name[0][0]

        self.heatmap = figure(
            title=fig_title, tools=TOOLS, toolbar_location="below",
            tooltips=[
                ("Raft", "@raft_name"), ("Raft slot", "@raft_slot"), ("CCD slot", "@ccd_slot"),
                ("CCD name", "@ccd_name"), ("Amp","@amp_number"),
                (testq, "@test_q")
            ],
            x_axis_location=None, y_axis_location=None,)
        self.heatmap.grid.grid_line_color = None
        self.heatmap.hover.point_policy = "follow_mouse"
        self.heatmap.add_layout(color_bar,"right")

        if self.full_FP_mode is True:
            self.heatmap.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1)

        x = []
        y = []
        raft_name = []
        raft_slot = []
        ccd_name = []
        ccd_slot = []
        amp_number = []
        test_q = []
        raft_x_list = []
        raft_y_list = []
        cen_x_list = []
        cen_y_list = []

        for raft in range(21):

            raft_x = self.raft_center_x[raft]
            raft_y = self.raft_center_y[raft]
            raft_x_list.append(raft_x)
            raft_y_list.append(raft_y)

            for ccd in range(9):
                cen_x = raft_x  + self.ccd_center_x[ccd]
                cen_y = raft_y  - self.ccd_center_y[ccd]
                cen_x_list.append(cen_x)
                cen_y_list.append(cen_y)

        for raft in range(21):

            if self.raft_is_there[raft] is False:
                continue

            run_q = run
            if self.emulate is True and self.full_FP_mode is True:
                run_q = self.emulated_runs[raft]

            test_q.extend(self.get_testq(run=run_q, testq=testq))

            num_ccd = 9
            if self.single_ccd_mode is False:
                single_run = run
                if self.emulate is True:
                     _, single_run = self.get_emulated_raft_info(self.installed_raft_names[raft])
                run_info = self.connect.getRunSummary(run=single_run)
                run_time = run_info['begin']
                print ("render ", self.installed_raft_names[raft], single_run)
                ccd_list = self.eR.raftContents(raftName=self.installed_raft_names[raft], when=run_time)
            else:
                ccd_list = self.single_ccd_name
                num_ccd = 1

            raft_x = self.raft_center_x[raft]
            raft_y = self.raft_center_y[raft]

            for ccd in range(num_ccd):

                for amp in range(16):
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]

                    a_cen_x = cen_x + self.amp_center_x[amp]
                    a_cen_y = cen_y + self.amp_center_y[amp]

                    x.append(a_cen_x)
                    y.append(a_cen_y)
                    raft_name.append(self.installed_raft_names[raft])
                    raft_slot.append(self.raft_slot_names[raft])
                    ccd_name.append(ccd_list[ccd][0])
                    ccd_slot.append(ccd_list[ccd][1])
                    amp_number.append(amp)

        if self.full_FP_mode is True:
            self.heatmap.rect(x=raft_x_list, y=raft_y_list, width=self.raft_width,
                              height=self.raft_width, color="blue", fill_alpha=0.)
            self.heatmap.rect(x=cen_x_list, y=cen_y_list, width=self.ccd_width, height=self.ccd_width,
                              color="green",
                              fill_alpha=0.)

        self.source = ColumnDataSource(dict(x=x, y=y, raft_name=raft_name, raft_slot=raft_slot,
                                  ccd_name=ccd_name, ccd_slot=ccd_slot,
                                  amp_number=amp_number, test_q=test_q))
        self.source.on_change('selected', self.tap_cb)

        cm = self.heatmap.select_one(LogColorMapper)
        cm.update(low=min(test_q), high=max(test_q))

        self.heatmap_rect = self.heatmap.rect(x='x', y='y', source=self.source, height=self.amp_width,
                              width=self.ccd_width/2.,
            color="black",
            fill_alpha=0.7, fill_color={ 'field': 'test_q', 'transform': color_mapper})

        h_q, bins = np.histogram(np.array(test_q), bins=50)
        h = figure(title=testq, tools=TOOLS, toolbar_location="below")
        h.quad(top=h_q, bottom=0, left=bins[:-1], right=bins[1:], fill_color='blue', fill_alpha=0.2)


#        l = layout(self.dropdown, row(p,h))
        l = layout(row(self.heatmap,h))

#        show(l)

        return l


if __name__ == "__main__":

#    rFP = renderFocalPlane()

    raft_list = [["LCA-11021_RTM-003_ETU2", "R10"], ["LCA-11021_RTM-005", "R21"]]
#    raft_list = [["LCA-11021_RTM-003_ETU2", "R10"]]
    run_list = [5731, 6259]
#    rFP.set_emulation(raft_list, run_list)

#    l = rFP.render(run=5731, testq="gain")

    menu = [("Gain", "gain"), ("Read Noise", "read_noise")]
    drop = Dropdown(label="Select test", button_type="warning", menu=menu)

    m = layout(drop)

    print ("About to display")


    def update_dropdown(sattr, old, new):
        new_test = drop.value

        #rFP.render(run=1234, testq=new_test)

    drop.on_change('value', update_dropdown)

    curdoc().add_root(m)
    curdoc().title = "Focal Plane Heat Map"


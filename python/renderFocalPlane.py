from __future__ import print_function
import numpy as np
import pandas as pd
from get_EO_analysis_results import get_EO_analysis_results
from exploreFocalPlane import exploreFocalPlane
from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection

from bokeh.models import ColumnDataSource, LinearAxis, Grid, LogColorMapper, ColorBar, \
    LogTicker, DataRange1d
from bokeh.plotting import figure
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models.glyphs import VBar

"""
Create a rendering of the focal plane, composed of science and corner rafts, each made of sensors with
their amplifiers.

Usage modes:
 1. full Focal Plane
 2. single raft - a raft from the focal plane
 3. single CCD - CCD from the focal plane
 4. solo raft - single raft test, given a run number - could be from BNL or I&T

 Note that there is no solo CCD mode - TS3 data is not compatible with this app.

 Emulate mode:
  provide a list of single raft names, slots and run numbers to populate a simulated focal plane
  In this mode the run number selection for the focal plane is disabled.
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

        # emulate mode provides a list of single raft runs to populate a fake focal plane
        self.emulate = False
        self.emulate_run_list = []
        self.emulated_runs = [0]*25

        self.single_raft_name = []
        self.single_raft_run = None
        self.single_ccd_name = []

        self.source = ColumnDataSource()
        self.histsource = ColumnDataSource()

        self.current_run = 0
        self.current_test = ""
        self.EO_type = "I&T-Raft"

        self.user_hook = None
        self.tap_cb = None
        self.select_cb = None
        self.heatmap = None
        self.heatmap_rect = None

        self.emulate_raft_list = []

        self.drop_ccd = None
        self.slot_mapping = None

        # list of available test quantities in raft/focal plane runs
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

        self.menu_ccd = [('S00','S00'),('S01','S01'),('S02','S02'),('S10','S10'),('S11','S11'),
                        ('S12','S12'),('S20','S20'),('S21','S21'),('S22','S22')]

        # list of the slot names and their order on the focal plane
        self.raft_slot_names = ["C0","R34", "R24", "R14","C1",
                                "R43", "R33", "R23", "R13", "R03",
                                "R42", "R32", "R22", "R12", "R02",
                                "R41", "R31", "R21", "R11", "R01",
                                "C2","R30", "R20", "R10","C4" ]

        # booleans for whether a slot on the FP is occupied
        self.raft_is_there = [False] * 25
        # and which raft occupies the slot
        self.installed_raft_names = [""] * 25

        # coordinates for raft, ccd, amp locations and sizes
        self.raft_center_x = [-6.,-3., 0., 3.,6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6.,-3., 0., 3., 6.
                              ]
        self.raft_center_y = [6.,6., 6., 6.,6.,
                              3., 3., 3., 3., 3.,
                              0., 0., 0., 0., 0.,
                              -3., -3., -3., -3., -3.,
                              -6., -6., -6.,-6.,-6.
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
        """
        Get the per radt or ccd test quantity array for this run and test name.
        :param run:  run number
        :param testq: test quantity name
        :return: list of test quantities - 144 long for raft; 16 for ccd
        """

        # in emulation mode, take the run number from the single raft run, rather than Focal Plane
        if self.emulate is True and (self.single_raft_mode is True or self.single_ccd_mode is True):
            run = self.single_raft_run

        # user override for "User"
        if self.user_hook is not None and testq == "User":
            return self.user_hook(run=run)

        # use get_EO to fetch the test quantities from the eT results database
        raft_list, data = self.get_EO.get_tests(site_type=self.EO_type, test_type=testq, run=run)
        res = self.get_EO.get_results(test_type=testq, data=data, device=raft_list)

        test_list = []
        for ccd in res:
            # if in single CCD mode, only return that one's quantities
            if self.single_ccd_mode is True and ccd != self.single_ccd_name[0][0]:
                continue
            test_list.extend(res[ccd])

        return test_list

    def get_raft_content(self):
        """
        Figure out what rafts we need - be it in the full Focal Plane or single rafts
        :return: raft_list -  list of lists - [raft names, Focal plane slot]
        """
        if self.emulate is False:
            if self.full_FP_mode is True:
                raft_list = self.eFP.focalPlaneContents()
            # figure out the raft name etc from the desired run number
            elif self.solo_raft_mode is True:
                run = self.current_run
                run_info = self.connect.getRunResults(run=run)
                raft_list = [[run_info['experimentSN'], "R22"]]
            # raft or CCD is on the focal plane
            elif self.single_raft_mode is True or self.single_ccd_mode is True:
                raft_list = self.single_raft_name
        else:
            # use the supplied list of raft info
            raft_list = self.emulate_raft_list
            # use one of the rafts/ccd on the emulated focal plane
            if self.single_raft_mode is True or self.single_ccd_mode is True:
                raft_list = self.single_raft_name

        for j in range(25):
            self.installed_raft_names[j] = ""
            self.raft_is_there[j] = False

        # figure out who is where on the focal plane. For solo raft mode, it is assigned to R22
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
        """
        accept the emulation comfiguratin and set emulate to True
        :param raft_list: list of raft info - [raft name, slot]
        :param run_list: list or runs, indexed the same as raft_list
        :return: nothing
        """
        self.emulate = True

        self.emulate_raft_list = raft_list
        self.emulate_run_list = run_list

        self.menu_test.append(("User Supplied", "User"))

    def disable_emulation(self):

        self.emulate = False
        # need way to turn off user hook and do this remove
        #self.menu_test.remove(("User Supplied", "User"))

    def get_current_run(self):
        return self.current_run

    def get_current_test(self):
        return self.current_test

    def get_emulated_raft_info(self, raft=None):
        """
        Given a raft, sort out which slot and run number were assigned with it in emulaton mode
        :param raft: raft name [name, slot]
        :return: slot name and run number
        """
        run = None
        slot = None
        for idx, r in enumerate(self.emulate_raft_list):
            if raft == r[0]:
                slot = r[1]
                run = self.emulate_run_list[idx]
        return slot, run


    def render(self, run=None, testq=None, view=None,box=None):

        """
        Do the work to make the desired display
        :param run: run number (typically only used in non-emulated full Focal Plane mode
        :param testq: test quantity to draw
        :return: bokeh layout of the heatmap and histogram
        """
        self.current_run = run
        self.current_test = testq

        # figure out if this is BNL or I&T data from the run summary in eT
        run_sum = self.connect.getRunSummary(run=run)
        if "Integration" in run_sum["subsystem"]:
            self.EO_type = "I&T-Raft"
        else:
            self.EO_type = "BNL-Raft"

        raft_list = self.get_raft_content()

        # set up the bokeh heatmap figure
        TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"
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

        if self.full_FP_mode is True and view is not None:
            self.heatmap.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1,view=view)
        elif self.full_FP_mode is True:
            self.heatmap.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1)

        #if self.single_ccd_mode is True:
        #    view = CDSView(source=self.source, filters=[GroupFilter(column_name='species', group=self.single_ccd_name)])
        #    self.heatmap.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1,view=view)

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

        # work out all the squares for the rafts, CCDs and amps. If in single mode, suppress other rafts/
        # CCDs
        for raft in range(25):
            raft_x = self.raft_center_x[raft]
            raft_y = self.raft_center_y[raft]
            raft_x_list.append(raft_x)
            raft_y_list.append(raft_y)

            # Add the corner rafts
            if raft not in [0,4,20,24]:
                for ccd in range(9):
                    cen_x = raft_x  + self.ccd_center_x[ccd]
                    cen_y = raft_y  - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft==0:
                for ccd in [1,2,5]:
                    cen_x = raft_x  + self.ccd_center_x[ccd]
                    cen_y = raft_y  - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft==4:
                for ccd in [3,0,1]:
                    cen_x = raft_x  + self.ccd_center_x[ccd]
                    cen_y = raft_y  - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft==20:
                for ccd in [7,8,5]:
                    cen_x = raft_x  + self.ccd_center_x[ccd]
                    cen_y = raft_y  - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft==24:
                for ccd in [3,6,7]:
                    cen_x = raft_x  + self.ccd_center_x[ccd]
                    cen_y = raft_y  - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)

        for raft in range(25):

            if self.raft_is_there[raft] is False:
                continue

            run_q = run
            if self.emulate is True and self.full_FP_mode is True:
                run_q = self.emulated_runs[raft]
            run_data = self.get_testq(run=run_q, testq=testq)

            run_data = [run_data[i:i + 16] for i in range(0, len(run_data), 16)]
            amp_ordering = [15,14,13,12,11,10,9,8,0,1,2,3,4,5,6,7]
            run_data = [[ccd_data[j] for j in amp_ordering] for ccd_data in run_data]
            run_data = [val for sublist in run_data for val in sublist]

            test_q.extend(self.get_testq(run=run_q, testq=testq))

            num_ccd = 9
            if self.single_ccd_mode is False:
                single_run = run
                if self.emulate is True:
                     _, single_run = self.get_emulated_raft_info(self.installed_raft_names[raft])
                run_info = self.connect.getRunSummary(run=single_run)
                run_time = run_info['begin']
                ccd_list = self.eR.raftContents(raftName=self.installed_raft_names[raft], when=run_time)
                ccd_ordering = [6,3,0,7,4,1,8,5,2]
                ccd_list = [ccd_list[i] for i in ccd_ordering]

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
                    amp_number.append(amp_ordering[amp]+1)



        self.source = ColumnDataSource(pd.DataFrame(dict(x=x, y=y, raft_name=raft_name, raft_slot=raft_slot, ccd_name=ccd_name, ccd_slot=ccd_slot, amp_number=amp_number, test_q=test_q)))

        # draw all rafts and CCDs in full mode
        if self.full_FP_mode is True:
            self.heatmap.rect(x=raft_x_list, y=raft_y_list, width=self.raft_width,
                              height=self.raft_width, color="blue", fill_alpha=0.)
            self.heatmap.rect(x=cen_x_list, y=cen_y_list, width=self.ccd_width, height=self.ccd_width,
                              color="green",
                              fill_alpha=0.)


        h_q, bins = np.histogram(np.array(test_q), bins=50)
        self.histsource = ColumnDataSource(pd.DataFrame(dict(top=h_q,left=bins[:-1], right=bins[1:])))
        #Using numpy to get the index of the bins to which the value is assigned
        h = figure(title=testq, tools=TOOLS, toolbar_location="below")
        h.quad(source = self.histsource, top='top', bottom=0, left='left', right='right', fill_color='blue', fill_alpha=0.2)
        self.source.on_change('selected', self.tap_cb)
        self.histsource.on_change('selected', self.select_cb)

        cm = self.heatmap.select_one(LogColorMapper)
        cm.update(low=min(test_q), high=max(test_q))

        if self.full_FP_mode is True and view is not None:
            self.heatmap.rect(x='x', y='y', source=self.source, height=self.amp_width,
                                width=self.ccd_width/2.,
                                color="black",
                                fill_alpha=0.7, fill_color="black",view=view)
        self.heatmap.rect(x='x', y='y', source=self.source, height=self.amp_width,
                              width=self.ccd_width/2.,
                              color="black",
                              fill_alpha=0.7, fill_color={ 'field': 'test_q', 'transform': color_mapper})
        if box is not None:
            h.add_layout(box)
        xaxis = LinearAxis()
        yaxis = LinearAxis()

        h.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
        h.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

        l = layout(row(self.heatmap,h))

        return l

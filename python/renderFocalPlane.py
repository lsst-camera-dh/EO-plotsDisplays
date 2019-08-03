from __future__ import print_function
import numpy as np
import pandas as pd
from get_EO_analysis_results import get_EO_analysis_results
from exploreFocalPlane import exploreFocalPlane
from exploreRaft import exploreRaft
from eTraveler.clientAPI.connection import Connection

from bokeh.models import LinearAxis, Grid, ContinuousColorMapper, LinearColorMapper, ColorBar, \
    LogTicker
from bokeh.plotting import figure
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout
from bokeh.models import CustomJS, ColumnDataSource, CDSView, BooleanFilter
from bokeh.models.widgets import TextInput, Dropdown, Button
from bokeh.plotting import curdoc

import time

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

        self.amp_width = 1 / 8.
        self.ccd_width = 1.
        self.raft_width = 3.

        self.single_raft_mode = False
        self.single_ccd_mode = False
        self.solo_raft_mode = False
        self.full_FP_mode = True

        # emulate mode provides a list of single raft runs to populate a fake focal plane
        self.emulate = False
        self.emulate_run_list = []
        self.emulated_runs = [0] * 25

        self.single_raft_name = []
        self.single_raft_run = None
        self.single_ccd_name = []

        self.source = ColumnDataSource()
        self.histsource = ColumnDataSource()

        self.current_run = 0
        self.current_test = ""
        self.previous_test = ""
        self.current_raft = None
        self.EO_type = "I&T-Raft"
        self.current_mode = 0
        self.current_raft_list = []
        self.current_FP_raft_list = []

        self.user_hook = None
        self.tap_cb = self.tap_input
        self.select_cb = self.select_input
        #self.source.on_change('selected', self.tap_cb)
        #self.histsource.on_change('selected', self.select_cb)


        # set up run number text box - disable it in emulate mode
        self.text_input = TextInput(value=str(self.get_current_run()), title="Select Run")

        if self.emulate is True:
            self.text_input.title = "Select Run Disabled"

        # set up the dropdown menu for modes, along with available modes list
        self.menu_modes = [("Full Focal Plane", "Full Focal Plane"), ("FP single raft", "FP single raft"),
                           ("FP single CCD", "FP single CCD"), ("Solo Raft", "Solo Raft")]

        self.drop_modes = Dropdown(label="Mode: " + self.menu_modes[self.current_mode][0],
                                   button_type="success",
                                   menu=self.menu_modes)

        # set up the dropdown menu for links, along with available modes list
        self.menu_links = [("Documentation", "https://confluence.slac.stanford.edu/x/6FNSDg"),
                           ("Single Raft Run Plots",
                            "http://slac.stanford.edu/exp/lsst/camera/SingleRaftEOPlots/bokehDashboard.html"),
                           ("List of Prod Good Raft Runs",
                            "https://lsst-camera.slac.stanford.edu/DataPortal/runList.jsp?Status=-1&Traveler=any&Subsystem"
                            "=any&Site=any&Label=25&Run+min=&Run+max=&submit=Filter&dataSourceMode=Prod"),
                           ("List of Dev Good Raft Runs",
                            "https://lsst-camera.slac.stanford.edu/DataPortal/runList.jsp?Status=-1&Traveler=any&Subsystem"
                            "=any&Site=any&Label=25&Run+min=&Run+max=&submit=Filter&dataSourceMode=Dev")
                           ]

        self.drop_links_callback = CustomJS(code="""var url=cb_obj.value;window.open(url,'_blank')""")

        self.drop_links = Dropdown(label="Useful Links", button_type="success",
                                   menu=self.menu_links)
        self.drop_links.js_on_change('value', self.drop_links_callback)

        self.drop_raft = Dropdown(label="Select Raft", button_type="warning", menu=[])
        self.drop_raft.on_change('value', self.update_dropdown_raft)

        self.drop_ccd = Dropdown(label="Select CCD",
                                 button_type="warning", menu=[])
        self.drop_ccd.on_change('value', self.update_dropdown_ccd)

        # define buttons to toggle emulation mode, and to fetch a config txt file
        self.button = Button(label="Emulate Mode", button_type="success")
        self.button_file = Button(label="Upload Emulation Config", button_type="success")

        # readining in the emulation config file depends on two callbacks - one triggering reading the
        # file into the ColumnDataSource, coupled with looking for a change on the ColumnDataSource
        self.file_source = ColumnDataSource({'file_contents': [], 'file_name': []})

        self.button_file.callback = CustomJS(args=dict(file_source=self.file_source), code="""
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

        self.drop_modes.on_change('value', self.update_dropdown_modes)
        self.text_input.on_change('value', self.update_text_input)
        self.button.on_click(self.update_button)
        self.file_source.on_change('data', self.file_callback)

        self.heatmap = None
        self.heatmap_rect = None

        self.emulate_raft_list = []

        self.slot_mapping = None

        self.testq_timer = 0

        self.test_cache = {}
        self.ccd_content_cache = {}

        # list of available test quantities in raft/focal plane runs
        self.menu_test = [('Gain', 'gain'), ('Gain Error', 'gain_error'), ('PSF', 'psf_sigma'),
                          ("Read Noise", 'read_noise'), ('System Noise', 'system_noise'),
                          ('Total Noise', 'total_noise'), ('Bright Pixels', 'bright_pixels'),
                          ('Bright Columns', 'bright_columns'), ('Dark Pixels', 'dark_pixels'),
                          ('Dark Columns', 'dark_columns'), ("Traps", 'num_traps'),
                          ('CTI Low Serial', 'cti_low_serial'), ('CTI High Serial', 'cti_high_serial'),
                          ('CTI Low Parallel', 'cti_low_parallel'),
                          ('CTI High Parallel', 'cti_high_parallel'),
                          ('Dark Current 95CL', 'dark_current_95CL'),
                          ('PTC gain', 'ptc_gain'), ('Pixel mean', 'pixel_mean'), ('Full Well', 'full_well'),
                          ('Nonlinearity', 'max_frac_dev')]
        self.menu_test.append(("User supplied", "User"))

        # drop down menu of test names, taking the menu from self.menu_test
        self.drop_test = Dropdown(label="Select test", button_type="warning", menu=self.menu_test)
        self.drop_test.on_change('value', self.update_dropdown_test)

        self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test, self.drop_modes),
                                  row(self.button, self.button_file))
        self.layout = self.interactors
        self.map_layout = self.layout

        self.menu_ccd = [('S00', 'S00'), ('S01', 'S01'), ('S02', 'S02'), ('S10', 'S10'), ('S11', 'S11'),
                         ('S12', 'S12'), ('S20', 'S20'), ('S21', 'S21'), ('S22', 'S22')]

        # list of the slot names and their order on the focal plane
        self.raft_slot_names = ["C0","R41", "R42", "R43","C1",
                                "R30", "R31", "R32", "R33", "R34",
                                "R20", "R21", "R22", "R23", "R24",
                                "R10", "R11", "R12", "R13", "R14",
                                "C2","R01", "R02", "R03","C4" ]
        self.amp_ordering = [15,14,13,12,11,10,9,8,0,1,2,3,4,5,6,7]
        self.ccd_ordering = ['S00','S01','S02',
                            'S10','S11','S12',
                            'S20','S21','S22']

        # booleans for whether a slot on the FP is occupied
        self.raft_is_there = [False] * 25
        # and which raft occupies the slot
        self.installed_raft_names = [""] * 25
        self.installed_raft_slots = [""] * 25

        # coordinates for raft, ccd, amp locations and sizes
        self.raft_center_x = [-6., -3., 0., 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0., 3., 6.
                              ]
        self.raft_center_y = [6., 6., 6., 6., 6.,
                              3., 3., 3., 3., 3.,
                              0., 0., 0., 0., 0.,
                              -3., -3., -3., -3., -3.,
                              -6., -6., -6., -6., -6.
                              ]

        self.ccd_center_x = [-1., 0., 1.,
                             -1., 0., 1.,
                             -1., 0., 1.
                             ]
        self.ccd_center_y = [1., 1., 1.,
                             0., 0., 0.,
                             -1., -1., -1.
                             ]

        self.amp_center_x = [-self.ccd_width / 2. - self.amp_width / 2. + (j + 1) / 8. for j in range(8)]
        self.amp_center_x.extend(
            [-self.ccd_width / 2. - self.amp_width / 2. + (j + 1) / 8. for j in range(8)])

        self.amp_center_y = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]
        self.amp_center_y.extend([-0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25])

        """
        Layout of raft, CCDs, amps:

        Rafts:
                                    "C0","R41", "R42", "R43","C1"
                                    "R30", "R31", "R32", "R33", "R34",
                                    "R20", "R21", "R22", "R23", "R24",
                                    "R10", "R11", "R12", "R13", "R14"
                                    "C2","R01", "R02", "R03","C4"

        CCDs
                                    'S20','S21','S22'
                                    'S10','S11','S12'
                                    'S00','S01','S02'


        amps:
                                    lower: amps 1-8 (left to right)
                                    upper: amps 16-9
                                    aspect ratio is that amps long side is vertical
        """

        if server == 'Prod':
            pS = True
        else:
            pS = False
        self.connect_Prod = Connection(operator='richard', db="Prod", exp='LSST-CAMERA', prodServer=pS)
        self.connect_Dev = Connection(operator='richard', db="Dev", exp='LSST-CAMERA', prodServer=pS)

        self.eFP_Prod = exploreFocalPlane(db="Prod", prodServer=server)
        self.eR_Prod = exploreRaft(db="Prod", prodServer=server)
        self.get_EO_Prod = get_EO_analysis_results(db="Prod", server=server)

        self.eFP_Dev = exploreFocalPlane(db="Dev", prodServer=server)
        self.eR_Dev = exploreRaft(db="Dev", prodServer=server)
        self.get_EO_Dev = get_EO_analysis_results(db="Dev", server=server)

        self.connections = {}
        o = self.connections.setdefault("connect", {})
        o["Prod"] = self.connect_Prod
        o["Dev"] = self.connect_Dev

        FP = self.connections.setdefault("eFP", {})
        FP["Prod"] = self.eFP_Prod
        FP["Dev"] = self.eFP_Dev

        eR = self.connections.setdefault("eR", {})
        eR["Prod"] = self.eR_Prod
        eR["Dev"] = self.eR_Dev

        EO = self.connections.setdefault("get_EO", {})
        EO["Prod"] = self.get_EO_Prod
        EO["Dev"] = self.get_EO_Dev

        self.dbsel = "Prod"

    def get_testq(self, raft_slot=None):
        """
        Get the per raft or ccd test quantity array for this run and test name.
        :param run:  run number
        :param testq: test quantity name
        :return: list of test quantities - 144 long for raft; 16 for ccd
        """

        in_time = time.time()

        BOT = self.full_FP_mode and not self.emulate

        # user override for "User"
        if self.user_hook is not None and self.current_test == "User":
            return self.user_hook(run=self.current_run, mode=self.single_ccd_mode, slot=raft_slot)

        if self.current_run not in self.test_cache or self.current_raft not in \
                self.test_cache[self.current_run]:
            # use get_EO to fetch the test quantities from the eT results database
            raft_list, data = self.connections["get_EO"][self.dbsel].get_tests(site_type=self.EO_type,
                                                                               run=self.current_run)
            res = self.connections["get_EO"][self.dbsel].get_all_results(data=data, device=raft_list)
            if BOT:
                self.test_cache[self.current_run] = res
            else:
                c = self.test_cache.setdefault(self.current_run, {})
                c[raft_list] = res

        test_list = []
        ccd_idx = {"S00":0, "S01":1, "S02":2, "S10":3, "S11":4, "S12":5, "S20":6, "S21":7, "S22":8 }

        # fetch the test from the cache

#        if self.EO_type == "I&T-BOT":
        if BOT:
            test_list = [-1.]*144
            if self.single_ccd_mode:
                test_list = [-1.] * 16
            try:
                t = self.test_cache[self.current_run][self.current_test][raft_slot]
            except KeyError:
                raise KeyError(self.current_test + ": not available. Reverting to previous - " +
                               self.previous_test)
            for ccd in t:
                if self.single_ccd_mode and ccd != self.single_ccd_name[0][1]:
                    continue
                list_idx = 16 * ccd_idx[ccd]
                for i in range(16):
                    test_list[list_idx+i] = t[ccd][i]

        else:
            try:
                t = self.test_cache[self.current_run][self.current_raft][self.current_test]
            except KeyError:
                raise KeyError(self.current_test + ": not available. Reverting to previous - " +
                               self.previous_test)

            ccd_name = ""
            for ccd in t:
                # if in single CCD mode, only return that one's quantities
                if self.single_ccd_mode is True and ccd != self.single_ccd_name[0][0]:
                    continue
                test_list.extend(t[ccd])

        self.testq_timer += time.time() - in_time

        if self.single_ccd_mode:
            if len(test_list) != 16:
                print("CCD mode - error in length of test quantity list: ", len(test_list))
                raise ValueError
        elif len(test_list) != 144:
            print("Raft mode - error in length of test quantity list: ", len(test_list))
            raise ValueError

        return test_list

    def get_raft_content(self):
        """
        Figure out what rafts we need - be it in the full Focal Plane or single rafts
        :return: raft_list -  list of lists - [raft names, Focal plane slot]
        """
        if self.emulate is False:
            if self.full_FP_mode is True:
                raft_list = self.connections["eFP"][self.dbsel].focalPlaneContents(run=self.current_run)
                self.current_FP_raft_list = raft_list
            # figure out the raft name etc from the desired run number
            elif self.solo_raft_mode is True:
                run = self.current_run
                run_info = self.connections["connect"][self.dbsel].getRunResults(run=run)
                raft_list = [[run_info['experimentSN'], "R22"]]
                self.single_raft_name = raft_list
            # raft or CCD is on the focal plane; name set by tap_input selection
            elif self.single_raft_mode is True or self.single_ccd_mode is True:
                raft_list = self.single_raft_name
        else:
            # use the supplied list of raft info
            raft_list = self.emulate_raft_list
            self.current_FP_raft_list = raft_list
            # use one of the rafts/ccd on the emulated focal plane
            if self.single_raft_mode is True or self.single_ccd_mode is True:
                raft_list = self.single_raft_name

        for j in range(25):
            self.installed_raft_names[j] = ""
            self.installed_raft_slots[j] = ""
            self.raft_is_there[j] = False

        # figure out who is where on the focal plane. For solo raft mode, it is assigned to R22
        for i in range(len(self.raft_slot_names)):
            for raft in range(len(raft_list)):
                if self.raft_slot_names[i] == raft_list[raft][1]:
                    self.raft_is_there[i] = True
                    self.installed_raft_names[i] = raft_list[raft][0]
                    self.installed_raft_slots[i] = raft_list[raft][1]
                    if self.emulate is True:
                        self.emulated_runs[i] = self.emulate_run_list[
                            self.emulate_raft_list.index(raft_list[raft])]
                    #                    self.emulate_raft_list = raft_list
                    break

        self.current_raft_list = raft_list
        return raft_list

    def set_emulation(self, config_spec=None):
        """
        accept the emulation comfiguratin and set emulate to True
        :param raft_list: list of raft info - [raft name, slot]
        :param run_list: list or runs, indexed the same as raft_list
        :return: nothing
        """
        self.emulate = True

        raft_list, run_list = self.parse_emulation_config(file_spec=config_spec)

        self.emulate_raft_list = raft_list
        self.emulate_run_list = run_list
        self.current_raft_list = raft_list

        self.menu_test.append(("User Supplied", "User"))

    def disable_emulation(self):

        self.emulate = False
        # need way to turn off user hook and do this remove
        # self.menu_test.remove(("User Supplied", "User"))

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

    def set_mode(self, mode):

        self.full_FP_mode = False
        self.single_ccd_mode = False
        self.single_raft_mode = False
        self.solo_raft_mode = False

        if mode == "full_FP":
            self.full_FP_mode = True
            self.current_mode = 0
        elif mode == "single_ccd":
            self.single_ccd_mode = True
            self.current_mode = 2
        elif mode == "single_raft":
            self.single_raft_mode = True
            self.current_mode = 1
        elif mode == "solo_raft":
            self.solo_raft_mode = True
            self.emulate = False
            self.current_mode = 3

    def parse_emulation_config(self, file_spec):

        df = pd.read_csv(file_spec, header=0, skipinitialspace=True)
        raft_frame = df.set_index('raft', drop=False)

        raft_col = raft_frame["raft"]
        raft_list = []
        run_list = []

        for raft in raft_col:
            slot = raft_frame.loc[raft, "slot"]
            run = raft_frame.loc[raft, "run"]
            raft_list.append([raft, slot])
            run_list.append(str(run))

        self.emulate_raft_list = raft_list
        self.current_raft_list = raft_list

        return raft_list, run_list

    def get_run(self, raft=None):
        if self.emulate is False:
            run = self.current_run
        else:
            run = self.emulate_raft_list[raft]

        return run

    def tap_input(self, attr, old, new):
        """
        Handle the click in the heatmap. Does nothing if in full Focal Plane mode
        :param attr:
        :param old: previous value of self.source
        :param new: new value of self.source
        :return: nothing

        # The index of the selected glyph is : new['1d']['indices'][0]
        raft_name = self.source.data['raft_name'][new['1d']['indices'][0]]
        raft_slot = self.source.data['raft_slot'][new['1d']['indices'][0]]
        ccd_name = self.source.data['ccd_name'][new['1d']['indices'][0]]
        ccd_slot = self.source.data['ccd_slot'][new['1d']['indices'][0]]
        """

        selected_row = new[0]
        raft_name = self.source.data['raft_name'][selected_row]
        raft_slot = self.source.data['raft_slot'][selected_row]
        ccd_name = self.source.data['ccd_name'][selected_row]
        ccd_slot = self.source.data['ccd_slot'][selected_row]

        self.single_raft_name = [[raft_name, raft_slot]]
        self.current_raft = raft_name
        if self.emulate is True:
            _, self.single_raft_run = self.get_emulated_raft_info(self.single_raft_name[0][0])
            self.current_run = self.single_raft_run
        else:
            self.single_raft_run = self.get_current_run()

        if self.single_raft_mode is True:
            raft_menu = [(pair[1], pair[0]) for pair in self.current_raft_list]
            self.interactors = layout(row(self.text_input, self.drop_test, self.drop_raft, self.drop_modes),
                                      row(self.button, self.button_file))
            l_new = self.render()
            m_new = layout(self.interactors, l_new)
            self.layout.children = m_new.children

        if self.single_ccd_mode is True:
            self.single_ccd_name = [[ccd_name, ccd_slot, "Dummy REB"]]

            raftContents = self.connections["eR"][self.dbsel].raftContents(
                raftName=self.single_raft_name[0][0])
            ccd_menu = [(tup[1] + ': ' + tup[0], tup[0]) for tup in raftContents]

            self.slot_mapping = {tup[0]: tup[1] for tup in raftContents}
            self.interactors = layout(row(self.text_input, self.drop_test, self.drop_ccd, self.drop_modes),
                                      row(self.button, self.button_file))
            l_new = self.render()
            m_new = layout(self.interactors, l_new)
            self.layout.children = m_new.children

            # l_new = self.render(run=self.single_raft_run, testq=self.get_current_test())
            # m_new = layout(self.interactors, l_new)
            # self.layout.children = m_new.children

    def select_input(self, attr, old, new):
        """
        Handle the selections in the heatmap  or histogram.  Does nothing if
        not in full Focal Plane mode
        :param attr:
        :param old: previous value of self.source
        :param new: new value of self.source
        :return: nothing
        """

        if self.full_FP_mode is True:
            # The indices of the selected glyph is : new['1d']['indices']
            min = self.histsource.data['left'][new['1d']['indices'][0]]
            max = self.histsource.data['right'][new['1d']['indices'][-1]]
            booleans = [True if val >= min and val <= max else False for val in self.source.data['test_q']]
            view = CDSView(source=self.source, filters=[BooleanFilter(booleans)])
            l_new = self.render(view=view)
            m_new = layout(self.interactors, l_new)
            self.layout.children = m_new.children

    def update_dropdown_test(self, sattr, old, new):
        new_test = self.drop_test.value

        self.previous_test = self.current_test
        self.current_test = new_test
        l_new = self.render()
        m_new = layout(self.interactors, l_new)
        self.layout.children = m_new.children

    def update_dropdown_ccd(self, sattr, old, new):
        ccd_name = self.drop_ccd.value
        ccd_slot = self.slot_mapping[ccd_name]
        self.single_ccd_name = [[ccd_name, ccd_slot, "Dummy REB"]]
        self.drop_ccd.menu = []
        self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test, self.drop_ccd,
                                      self.drop_modes), row(self.button, self.button_file))
        l_new = self.render()
        m_new = layout(self.interactors, l_new)
        self.layout.children = m_new.children

    def update_dropdown_raft(self, sattr, old, new):
        # Update from raft_list for now - need to add case where we have all rafts.
        raft_name = self.drop_raft.value
        raft_slot_mapping = {pair[0]: pair[1] for pair in self.current_FP_raft_list}
        raft_slot = raft_slot_mapping[raft_name]
        #self.drop_raft.menu = []
        self.single_raft_name = [[raft_name, raft_slot]]
        self.current_raft = raft_name
        self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test, self.drop_raft,
                                      self.drop_modes), row(self.button, self.button_file))
        l_new = self.render()
        m_new = layout(self.interactors, l_new)
        self.layout.children = m_new.children

    def update_dropdown_modes(self, sattr, old, new):
        new_mode = self.drop_modes.value

        self.single_raft_mode = False
        self.single_ccd_mode = False
        self.solo_raft_mode = False
        self.full_FP_mode = False

        if new_mode == "Full Focal Plane":
            self.full_FP_mode = True
            self.button.label = "Emulate Mode"
            self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test, self.drop_modes),
                                      row(self.button, self.button_file))
            l_new = self.render()
            m_new = layout(self.interactors, l_new)
            self.layout.children = m_new.children

        elif new_mode == "FP single raft":
            try:
                self.button.label = "Emulate Mode"
                self.single_raft_mode = True
                raft_menu = [(pair[1] + " : " + pair[0], pair[0]) for pair in self.current_raft_list]
                self.drop_raft.label = "Select Raft"
                self.drop_raft.menu = raft_menu
                self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test,
                                              self.drop_raft, self.drop_modes), row(self.button,
                                                                                    self.button_file))
                l_new = self.render()
                m_new = layout(self.interactors, l_new)
                self.layout.children = m_new.children
            except Exception:
                print('Click on a raft in the heat map.')

        elif new_mode == "FP single CCD":
            try:
                self.button.label = "Emulate Mode"
                self.single_ccd_mode = True
                # if self.single_raft_name == []:
                #    self.single_raft_name = [raft_list[1]]
                raftContents = self.connections["eR"][self.dbsel].raftContents(
                    raftName=self.single_raft_name[0][0])
                ccd_menu = [(tup[1] + ': ' + tup[0], tup[0]) for tup in raftContents]
                print(ccd_menu)
                self.drop_ccd.label = "Select CCD from " + self.single_raft_name[0][0][-7:]
                self.drop_ccd.menu = ccd_menu
                self.slot_mapping = {tup[0]: tup[1] for tup in raftContents}
                self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test,
                                              self.drop_ccd, self.drop_modes), row(self.button,
                                                                                   self.button_file))
                l_new = self.render()
                m_new = layout(self.interactors, l_new)
                self.layout.children = m_new.children
            except IndexError:
                print('Click on a CCD in the heat map.')
                # box = Label(x=70, y=70, x_units='screen', y_units='screen',
                #     text='Click on CCD.', render_mode='css',
                #     border_line_color='black', border_line_alpha=1.0,
                #     background_fill_color='white', background_fill_alpha=1.0)
                # nteractors = layout(row(text_input, drop_test, drop_modes), row(button, button_file))
                # _new = self.render(run=self.get_current_run(), testq=self.get_current_test(),box=box)
                # m_new = layout(self.interactors, l_new)
                # self.layout.children = m_new.children
        # in solo mode, ensure run selecton is re-enabled
        elif new_mode == "Solo Raft":
            self.solo_raft_mode = True
            self.emulate = False
            self.button.label = "Run Mode"
            self.text_input.title = "Select Run"

            self.interactors = layout(row(self.drop_links, self.text_input, self.drop_test,
                                          self.drop_modes))
            l_new = self.render()
            m_new = layout(self.interactors, l_new)
            self.layout.children = m_new.children

        self.drop_modes.label = "Mode: " + new_mode

    def update_text_input(self, sattr, old, new):
        if self.emulate is False:
            self.text_input.title = "Select Run"
            new_run = self.text_input.value

            self.current_run = new_run
            l_new_run = self.render()
            m_new_run = layout(self.interactors, l_new_run)
            self.layout.children = m_new_run.children
        else:
            self.text_input.title = "Select Run Disabled"

    def update_button(self):
        current_mode = self.emulate_raft_list
        new_mode = not current_mode

        self.emulate_raft_list = new_mode
        if new_mode is True:
            self.button.label = "Emulate Mode"
            l_new_run = self.render()
            m_new_run = layout(self.interactors, l_new_run)
            self.layout.children = m_new_run.children

        else:
            self.button.label = 'Run Mode'

    def file_callback(self, attr, old, new):
        filename = self.file_source.data['file_name'][0]

        raft_list, run_list = self.parse_emulation_config(filename)

        self.set_emulation(config_spec=filename)

        l_new_run = self.render()
        m_new_run = layout(self.interactors, l_new_run)
        self.layout.children = m_new_run.children

    def render(self, view=None, box=None):

        """
        Do the work to make the desired display
        :param run: run number (typically only used in non-emulated full Focal Plane mode
        :param testq: test quantity to draw
        :return: bokeh layout of the heatmap and histogram
        """

        self.testq_timer = 0
        enter_time = time.time()

        raft_list = self.get_raft_content()

        # set up the bokeh heatmap figure
        TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"
        # this could be updated to better choices for the values, but for now
        # low/high are arbitrary to ensure tick marks are plotted
        color_mapper = LinearColorMapper(palette=palette,low=0,high=1e5)
        color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12,
                             border_line_color=None, location=(0, 0))

        fig_title_base = "Focal Plane" + " Run: "
        if self.emulate:
            fig_title =  fig_title_base + "Emulation Mode"
        else:
            fig_title = fig_title_base + self.current_run

        if self.single_raft_mode is True or self.solo_raft_mode is True:
            fig_title = self.single_raft_name[0][0] + " Run: " + self.current_run
        elif self.single_ccd_mode is True:
            fig_title = self.single_ccd_name[0][0] + " Run: " + self.current_run

        self.heatmap = figure(
            title=fig_title, tools=TOOLS, toolbar_location="below",
            tooltips=[
                ("Raft", "@raft_name"), ("Raft slot", "@raft_slot"), ("CCD slot", "@ccd_slot"),
                ("CCD name", "@ccd_name"), ("Amp", "@amp_number"),
                (self.current_test, "@test_q")
            ],
            x_axis_location=None, y_axis_location=None, )
        self.heatmap.grid.grid_line_color = None
        self.heatmap.hover.point_policy = "follow_mouse"
        self.heatmap.add_layout(color_bar, "right")

        if self.full_FP_mode is True and view is not None:
            self.heatmap.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1, view=view)
        elif self.full_FP_mode is True:
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

        setup_time = time.time() - enter_time

        # work out all the squares for the rafts, CCDs and amps. If in single mode, suppress other rafts/
        # CCDs
        for raft in range(25):
            raft_x = self.raft_center_x[raft]
            raft_y = self.raft_center_y[raft]
            raft_x_list.append(raft_x)
            raft_y_list.append(raft_y)

            # Add the corner rafts
            if raft not in [0, 4, 20, 24]:
                for ccd in range(9):
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft == 0:
                for ccd in [1, 2, 5]:
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft == 4:
                for ccd in [3, 0, 1]:
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft == 20:
                for ccd in [7, 8, 5]:
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)
            elif raft == 24:
                for ccd in [3, 6, 7]:
                    cen_x = raft_x + self.ccd_center_x[ccd]
                    cen_y = raft_y - self.ccd_center_y[ccd]
                    cen_x_list.append(cen_x)
                    cen_y_list.append(cen_y)

        timing_ccd_hierarchy = 0

        t_0_hierarchy = 0
        t_hierarchy = 0

        for raft in range(25):

            if self.raft_is_there[raft] is False:
                continue

            self.current_raft = self.installed_raft_names[raft]
            raft_slot_current = self.installed_raft_slots[raft]
            if self.emulate is True:
                self.current_run = self.emulated_runs[raft]

            # check the run number again for dev or prod (for mixed mode emulation where runs could be either)
            self.dbsel = "Prod"
            if 'D' in self.current_run:
                self.dbsel = "Dev"

            try:
                run_data = self.get_testq()
            except KeyError:
                self.current_test = self.previous_test
                run_data = self.get_testq()

            run_data = [run_data[i:i + 16] for i in range(0, len(run_data), 16)]
            run_data = [[ccd_data[j] for j in self.amp_ordering] for ccd_data in run_data]
            run_data = [val for sublist in run_data for val in sublist]

            test_q.extend(run_data)

            num_ccd = 9
            if self.single_ccd_mode is False:

                if self.current_run not in self.ccd_content_cache or self.installed_raft_names[raft] not in \
                        self.ccd_content_cache[self.current_run]:
                    t_0_hierarchy = time.time()
                    ccd_list_run = self.connections["eR"][self.dbsel].raftContents(
                        raftName=self.installed_raft_names[raft],
                        run=self.current_run)
                    t_hierarchy = time.time() - t_0_hierarchy
                    timing_ccd_hierarchy += t_hierarchy
                    r = self.ccd_content_cache.setdefault(self.current_run, {})
                    r[self.installed_raft_names[raft]] = ccd_list_run

                # fetch the CCD content from the cache
                ccd_list = self.ccd_content_cache[self.current_run][self.installed_raft_names[raft]]
                ccd_map = dict((ccd[1], ccd) for ccd in ccd_list)
                ccd_list = [ccd_map[ccd] for ccd in self.ccd_ordering]

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
                    amp_number.append(self.amp_ordering[amp]+1)

        ready_data_time = time.time() - enter_time

        self.source = ColumnDataSource(pd.DataFrame(dict(x=x, y=y, raft_name=raft_name, raft_slot=raft_slot,
                                                         ccd_name=ccd_name, ccd_slot=ccd_slot,
                                                         amp_number=amp_number, test_q=test_q)))

        # draw all rafts and CCDs in full mode
        if self.full_FP_mode is True:
            self.heatmap.rect(x=raft_x_list, y=raft_y_list, width=self.raft_width,
                              height=self.raft_width, color="blue", fill_alpha=0.)
            self.heatmap.rect(x=cen_x_list, y=cen_y_list, width=self.ccd_width, height=self.ccd_width,
                              color="green",
                              fill_alpha=0.)

        heat_map_done_time = time.time() - enter_time

        h_q, bins = np.histogram(np.array(test_q), bins=50)
        self.histsource = ColumnDataSource(pd.DataFrame(dict(top=h_q, left=bins[:-1], right=bins[1:])))
        # Using numpy to get the index of the bins to which the value is assigned
        h = figure(title=self.current_test, tools=TOOLS, toolbar_location="below")
        h.quad(source=self.histsource, top='top', bottom=0, left='left', right='right', fill_color='blue',
               fill_alpha=0.2)
        self.source.selected.on_change('indices', self.tap_cb)
        self.histsource.on_change('selected', self.select_cb)

        cm = self.heatmap.select_one(LinearColorMapper)
        cm.update(low=min(test_q), high=max(test_q))

        if self.full_FP_mode is True and view is not None:
            self.heatmap.rect(x='x', y='y', source=self.source, height=self.amp_width,
                                width=self.ccd_width/2.,
                                color="black",
                                fill_alpha=0.7, fill_color="black",view=view, line_width = 0.5)
        self.heatmap.rect(x='x', y='y', source=self.source, width=self.amp_width,
                          height=self.ccd_width / 2.,
                          color="black",
                          fill_alpha=0.7, fill_color={'field': 'test_q', 'transform': color_mapper},
                          line_width=0.5)
        if box is not None:
            h.add_layout(box)
        xaxis = LinearAxis()
        yaxis = LinearAxis()

        h.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
        h.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

        self.map_layout = layout(row(self.heatmap, h))

        done_time = time.time() - enter_time

        print("Timing: e ", enter_time, " s ", setup_time, " r ", ready_data_time, " h ",
              heat_map_done_time, " d ", done_time, " t ", self.testq_timer, " h_ccd ",
              timing_ccd_hierarchy)

        self.previous_test = self.current_test

        return self.map_layout

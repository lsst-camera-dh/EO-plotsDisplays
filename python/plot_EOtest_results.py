from __future__ import print_function
from get_EO_analysis_results import get_EO_analysis_results
from exploreRaft import exploreRaft
from bokeh.plotting import figure, output_file, show, save
from bokeh.layouts import gridplot, layout
from bokeh.models import ColumnDataSource
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Panel, Tabs, PreText, DataTable, TableColumn, HTMLTemplateFormatter
from eTraveler.clientAPI.connection import Connection
from bokeh.models import Span, Label
from bokeh.io import export_png
import argparse


class plot_EOtest_results():

    def __init__(self, db='Prod', server='Prod', base_dir=None):

        self.traveler_name = {}
        self.test_type = ""
        self.db = db
        self.server = server
        self.output_spec = ""

        if server == 'Prod':
            pS = True
        else:
            pS = False
        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)

    def write_run_plot(self, run=None, test_name=None, out_file=None, site=None):

        print('Operating on run ', run)
        self.output_spec = out_file

        g = get_EO_analysis_results(db=self.db, server=self.server)

        raft_list, data = g.get_tests(test_type=test_name, run=run, site_type=site)
        res = g.get_results(test_type=test_name, data=data, device=raft_list)

        test_list = []

        for raft in res[test_name]:
            for ccd in res[test_name][raft]:
                test_list.extend(res[test_name][raft][ccd])

        # NEW: create a column data source for the plots to share
        source = ColumnDataSource(data=dict(x=range(0,len(test_list)), test=test_list))

        TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select,lasso_select"

        # create a new plot with a title and axis labels
        p = figure(tools=TOOLS, title=test_name, x_axis_label='amp', y_axis_label=test_name)

        # add a line renderer with legend and line thickness
        #sensor_lines = [sensor_start, sensor_end, sensor_third]
        sensor_lines = []
        for i in range(0,160,16):
            sensor_lines.append(Span(location=i,
                                  dimension='height', line_color='grey',
                                  line_dash='dashed', line_width=3))
        p.circle('x', 'test', source=source, legend=test_name + " Run " + str(run), line_width=2)

        plot_layout = layout(p)

        export_png(plot_layout, self.output_spec)


if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Plot full focal plane EO test result to output file')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('-r', '--run', default=None, help="(raft run number (default=%(default)s)")
    parser.add_argument('-t', '--test_name', default=None, help="(test name (default=%(default)s)")
    parser.add_argument('-d', '--db', default='Prod', help="database to use (default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('-o', '--output', default='/Users/richard/LSST/Data/bokeh/',
                        help="output base directory (default=%(default)s)")
    parser.add_argument('-s', '--site_type', default='I&T-BOT', help="type & site of test (default=%("
                                                                      "default)s)")

    args = parser.parse_args()

    pG = plot_EOtest_results(db=args.db, server='Prod')

    wrt_plot = pG.write_run_plot(run=args.run, test_name=args.test_name, out_file=args.output,
                                 site=args.site_type)

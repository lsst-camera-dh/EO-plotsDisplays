from get_EO_analysis_results import get_EO_analysis_results
from bokeh.plotting import figure, output_file, show, save
from bokeh.layouts import gridplot, layout
from bokeh.models import ColumnDataSource
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Panel, Tabs, PreText, DataTable, TableColumn, HTMLTemplateFormatter
from  eTraveler.clientAPI.connection import Connection
import argparse

class plotGoodRaftRuns():

    def __init__(self, db='Prod', server='Prod', base_dir=None):

        self.traveler_name = {}
        self.test_type = "fe55_raft_analysis"
        self.traveler_name['I&T-Raft'] = 'INT-SR-EOT-01'
        self.traveler_name['BNL-Raft'] = 'SR-RTM-EOT-03'
        self.base_dir = base_dir
        self.db = db
        self.server = server

        if server == 'Prod':
            pS = True
        else:
            pS = False
        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)


    def find_runs(self,site_type=None, runs=None):

         #data = self.connect.getResultsJH(htype="LCA-11021_RTM",
         #                                stepName=self.test_type,
         #                                travelerName=self.traveler_name)

        if runs is not None:
            runs = runs

        return runs

    def make_run_pages(self, site_type=None, runs=None):

        run_list = self.find_runs(site_type=site_type, runs=runs)
        raft_list = []

        for run in run_list:
            data = self.connect.getRunResults(run=run)
            raft = data["experimentSN"]
            raft_list.append(raft)
            self.write_run_plot(run=run, site_type=site_type, raft=raft)

        return run_list, raft_list



    def write_run_plot(self, run=None, site_type=None, raft=None):

        print 'Operating on run ', run

        g = get_EO_analysis_results(db=self.db, server=self.server)

        raft_list, data = g.get_tests(site_type=site_type, test_type="gain", run=run)
        res = g.get_results(test_type="gain", data=data, device=raft)

        raft_list_ptc, data_ptc = g.get_tests(site_type=site_type, test_type="ptc_gain", run=run)
        res_ptc_gain = g.get_results(test_type='ptc_gain', data=data_ptc, device=raft)

        raft_list_psf, data_psf = g.get_tests(site_type=site_type, test_type="psf_sigma", run=run)
        res_psf = g.get_results(test_type='psf_sigma', data=data_psf, device=raft)

        raft_list_rn, data_rn = g.get_tests(site_type=site_type, test_type="read_noise", run=run)
        res_rn = g.get_results(test_type='read_noise', data=data_rn, device=raft)

        raft_list_cti_low_serial, data_cls = g.get_tests(site_type=site_type, test_type="cti_low_serial",
                                                        run=run)
        res_cls = g.get_results(test_type='cti_low_serial', data=data_cls, device=raft)
        raft_list_cti_high_serial, data_chs = g.get_tests(site_type=site_type,
                                                          test_type="cti_high_serial",
                                                        run=run)
        res_chs = g.get_results(test_type='cti_high_serial', data=data_chs, device=raft)

        raft_list_cti_low_parallel, data_clp = g.get_tests(site_type=site_type,
                                                           test_type="cti_low_parallel",
                                                        run=run)
        res_clp = g.get_results(test_type='cti_low_parallel', data=data_clp, device=raft)

        raft_list_cti_high_parallel, data_chp = g.get_tests(site_type=site_type,
                                                            test_type="cti_high_parallel",
                                                        run=run)
        res_chp = g.get_results(test_type='cti_high_parallel', data=data_chp, device=raft)

        raft_list_dark_pixels, data_dp = g.get_tests(site_type=site_type, test_type="dark_pixels",
                                                        run=run)
        res_dp = g.get_results(test_type='dark_pixels', data=data_dp, device=raft)

        raft_list_dark_columns, data_dc = g.get_tests(site_type=site_type, test_type="dark_columns",
                                                        run=run)
        res_dc = g.get_results(test_type='dark_columns', data=data_dc, device=raft)

        raft_list_bright_pixels, data_bp = g.get_tests(site_type=site_type, test_type="bright_pixels",
                                                        run=run)
        res_bp = g.get_results(test_type='bright_pixels', data=data_bp, device=raft)

        raft_list_bright_columns, data_bc = g.get_tests(site_type=site_type, test_type="bright_columns",
                                                        run=run)
        res_bc = g.get_results(test_type='bright_columns', data=data_bc, device=raft)

        raft_list_traps, data_tp = g.get_tests(site_type=site_type, test_type="num_traps", run=run)
        res_tp = g.get_results(test_type='num_traps', data=data_tp, device=raft)

        raft_list_qe, data_qe = g.get_tests(site_type=site_type, test_type="QE", run=run)
        res_qe = g.get_results(test_type='QE', data=data_qe, device=raft)

        raft_list_drkC, data_drkC = g.get_tests(site_type=site_type, test_type="dark_current_95CL", run=run)
        res_drkC = g.get_results(test_type='dark_current_95CL', data=data_drkC, device=raft)

        raft_list_fw, data_fw = g.get_tests(site_type=site_type, test_type="full_well", run=run)
        res_fw = g.get_results(test_type='full_well', data=data_fw, device=raft)

        raft_list_nonl, data_nonl = g.get_tests(site_type=site_type, test_type="max_frac_dev", run=run)
        res_nonl = g.get_results(test_type='max_frac_dev', data=data_nonl, device=raft)

        test_list = []
        test_list_ptc = []
        test_list_psf = []
        test_list_rn = []

        test_list_cls = []
        test_list_chs = []
        test_list_clp = []
        test_list_chp = []

        test_list_dp = []
        test_list_dc = []
        test_list_bp = []
        test_list_bc = []
        test_list_tp = []

        test_list_drkC = []
        test_list_fw = []
        test_list_nonl = []

        # treat qe specially since all filters are in the same list

        test_list_qe_u = []
        test_list_qe_g = []
        test_list_qe_r = []
        test_list_qe_i = []
        test_list_qe_z = []
        test_list_qe_y = []


        for ccd in res:
            test_list.extend(res[ccd])
            test_list_ptc.extend(res_ptc_gain[ccd])
            test_list_psf.extend(res_psf[ccd])
            test_list_rn.extend(res_rn[ccd])

            test_list_cls.extend(res_cls[ccd])
            test_list_chs.extend(res_chs[ccd])
            test_list_clp.extend(res_clp[ccd])
            test_list_chp.extend(res_chp[ccd])

            test_list_bp.extend(res_bp[ccd])
            test_list_bc.extend(res_bc[ccd])
            test_list_dp.extend(res_dp[ccd])
            test_list_dc.extend(res_dc[ccd])
            test_list_tp.extend(res_tp[ccd])

            test_list_drkC.extend(res_drkC[ccd])
            test_list_fw.extend(res_fw[ccd])
            test_list_nonl.extend(res_nonl[ccd])

            test_list_qe_u.append(res_qe[ccd][0])
            test_list_qe_g.append(res_qe[ccd][1])
            test_list_qe_r.append(res_qe[ccd][2])
            test_list_qe_i.append(res_qe[ccd][3])
            test_list_qe_z.append(res_qe[ccd][4])
            test_list_qe_y.append(res_qe[ccd][5])



        # NEW: create a column data source for the plots to share
        source = ColumnDataSource(data=dict(x=range(0,len(test_list)), gain=test_list, ptc=test_list_ptc,
                                psf=test_list_psf, rn=test_list_rn, cls=test_list_cls,
                                chs=test_list_chs, clp=test_list_clp, chp=test_list_chp,
                                bp=test_list_bp, bc=test_list_bc, dp=test_list_dp, dc=test_list_dc,
                                tp=test_list_tp, drkC=test_list_drkC,
                                fw=test_list_fw, nonl=test_list_nonl))

        source_qe = ColumnDataSource(data=dict(x=range(0,len(test_list_qe_u)), u=test_list_qe_u,
                                g=test_list_qe_g, r=test_list_qe_r,i=test_list_qe_i,z=test_list_qe_z,
                                y=test_list_qe_y))


        TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select,lasso_select"

        # create a new plot with a title and axis labels
        p = figure(tools=TOOLS, title="gains", x_axis_label='amp', y_axis_label='gain')
        ptc = figure(tools=TOOLS, title="ptc gains", x_axis_label='amp', y_axis_label='gain')
        psf = figure(tools=TOOLS, title="psf", x_axis_label='amp', y_axis_label='psf')
        rn = figure(tools=TOOLS, title="Read noise", x_axis_label='amp', y_axis_label='Noise')

        cls = figure(tools=TOOLS, title="CTI low serial", x_axis_label='amp', y_axis_label='CTI')
        chs = figure(tools=TOOLS, title="CTI high serial", x_axis_label='amp', y_axis_label='CTI')
        clp = figure(tools=TOOLS, title="CTI low parallel", x_axis_label='amp', y_axis_label='CTI')
        chp = figure(tools=TOOLS, title="CTI high parallel", x_axis_label='amp', y_axis_label='CTI')

        bp = figure(tools=TOOLS, title="Bright Pixels", x_axis_label='amp', y_axis_label='Bright Pixels')
        bc = figure(tools=TOOLS, title="Bright Columns", x_axis_label='amp', y_axis_label='Bright Columns')
        dp = figure(tools=TOOLS, title="Dark Pixels", x_axis_label='amp', y_axis_label='Dark Pixels')
        dc = figure(tools=TOOLS, title="Dark Columns", x_axis_label='amp', y_axis_label='Dark Columns')
        tp = figure(tools=TOOLS, title="Traps", x_axis_label='amp', y_axis_label='Traps')

        drkC = figure(tools=TOOLS, title="Dark Current", x_axis_label='amp', y_axis_label='Current')
        fw = figure(tools=TOOLS, title="Full Well", x_axis_label='amp', y_axis_label='Full Well')
        nonl = figure(tools=TOOLS, title="Non-linearity", x_axis_label='amp', y_axis_label='Max dev')

        qe_u = figure(tools=TOOLS, title="QE: u band", x_axis_label='sensor', y_axis_label='QE')
        qe_g = figure(tools=TOOLS, title="QE: g band", x_axis_label='sensor', y_axis_label='QE')
        qe_r = figure(tools=TOOLS, title="QE: r band", x_axis_label='sensor', y_axis_label='QE')
        qe_i = figure(tools=TOOLS, title="QE: i band", x_axis_label='sensor', y_axis_label='QE')
        qe_z = figure(tools=TOOLS, title="QE: z band", x_axis_label='sensor', y_axis_label='QE')
        qe_y = figure(tools=TOOLS, title="QE: y band", x_axis_label='sensor', y_axis_label='QE')

        # add a line renderer with legend and line thickness
        p.circle('x', 'gain', source=source, legend="Gain: Run " + str(run), line_width=2)
        ptc.circle('x','ptc', source=source, legend="ptc Gain: Run " + str(run), line_width=2)
        psf.circle('x','psf', source=source, legend="PSF: Run " + str(run), line_width=2)
        rn.circle('x','rn', source=source, legend="Read Noise: Run " + str(run), line_width=2)

        cls.circle('x','cls', source=source, legend="CTI low serial: Run " + str(run), line_width=2)
        chs.circle('x','chs', source=source, legend="CTI high serial: Run " + str(run), line_width=2)
        clp.circle('x','clp', source=source, legend="CTI low parallel: Run " + str(run), line_width=2)
        chp.circle('x','chp', source=source, legend="CTI high parallel: Run " + str(run), line_width=2)

        bp.circle('x','bp', source=source, legend="Bright Pixels: Run " + str(run), line_width=2)
        bc.circle('x','bc', source=source, legend="Bright Columns: Run " + str(run), line_width=2)
        dp.circle('x','dp', source=source, legend="Dark Pixels: Run " + str(run), line_width=2)
        dc.circle('x','dc', source=source, legend="Dark Columns: Run " + str(run), line_width=2)
        tp.circle('x','tp', source=source, legend="Traps: Run " + str(run), line_width=2)

        drkC.circle('x','drkC', source=source, legend="Dark Current: Run " + str(run), line_width=2)
        fw.circle('x','fw', source=source, legend="Full Well: Run " + str(run), line_width=2)
        nonl.circle('x','nonl', source=source, legend="Non-linearity: Run " + str(run), line_width=2)

        qe_u.circle('x','u', source=source_qe, legend="QE u band: Run " + str(run), line_width=2)
        qe_g.circle('x','g', source=source_qe, legend="QE g band: Run " + str(run), line_width=2)
        qe_r.circle('x','r', source=source_qe, legend="QE r band: Run " + str(run), line_width=2)
        qe_i.circle('x','i', source=source_qe, legend="QE i band: Run " + str(run), line_width=2)
        qe_z.circle('x','z', source=source_qe, legend="QE z band: Run " + str(run), line_width=2)
        qe_y.circle('x','y', source=source_qe, legend="QE y band: Run " + str(run), line_width=2)


        # NEW: put the subplots in a gridplot
        grid = gridplot([[p, ptc], [psf, rn]])
        grid_cti = gridplot([[cls, chs], [clp, chp]])
        grid_def = gridplot([[bp, bc, None], [dp, dc, tp]])
        grid_qe = gridplot([[qe_u, qe_g, qe_r], [qe_i, qe_z, qe_y]])
        grid_misc = gridplot([[fw, drkC], [nonl, None]])

        raft_text = "Plots for I&T Raft run " + str(run) + " " + raft

        pre = PreText(text=raft_text, width=1000, height=100)

        tab1 = Panel(child=grid, title="Gains, PSF, Noise")
        tab2 = Panel(child=grid_cti, title="CTI")
        tab3 = Panel(child=grid_def, title="Defects")
        tab4 = Panel(child=grid_qe, title="QE 6-band")
        tab5 = Panel(child=grid_misc, title="Dark C, Full well, Non-lin")

        tabs = Tabs(tabs=[ tab1, tab2, tab3, tab4, tab5 ])

        l= layout([widgetbox(pre), tabs], sizing_mode='scale_both')

        o_file = self.base_dir + raft + "-" + str(run) + ".html"
        output_file(o_file)
        save(l)


    def write_table(self, run_list=None, raft_list=None):

        data = dict(
                rafts=raft_list,
                runs=run_list
                )
        dashboard = ColumnDataSource(data)

        columns = [
            TableColumn(field="rafts", title="Raft"),
            TableColumn(field="runs", title="Run", formatter=
                HTMLTemplateFormatter(template=
                "<a href= \
                'http://slac.stanford.edu/~richard/LSST/<%= rafts %>-<%= runs %>.html' \
                ><%= runs %></a>"))
        ]
        data_table = DataTable(source=dashboard, columns=columns, width=400, height=280)

        return data_table

if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('--run', default=None, help="(raft run number (default=%(default)s)")
    parser.add_argument('-d', '--db', default='Prod', help="database to use (default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('-s', '--site_type', default=None,
                        help="site type (default=%((default)s)"                                                                     "default)s)")
    parser.add_argument('-o', '--output', default='/Users/richard/LSST/Data/bokeh/',
                        help="output base directory (default=%(default)s)")

    args = parser.parse_args()

    pG = plotGoodRaftRuns(db='Prod', server='Prod', base_dir=args.output)

    runs_bnl = [4390, 4417, 4418, 4576, 4613, 4625, 4626, 5508, 5511, 5634, 5635, 5675, 5761, 6131, 6147,\
                6317, 6350, 6829, 6854, 7192, 7195, 7479, 7652, 7653, 7659, 7660, 7661, 7678,\
                7983, 7984, 8028, 8404, 8696, 8705, 8746, 8758, 8872]
    run_list, raft_list = pG.make_run_pages(site_type="BNL-Raft", runs=runs_bnl)

    data_table_bnl = pG.write_table(run_list=run_list, raft_list=raft_list)

    runs_int = [5582, 5730, 5731, 6259, 7046, 7086 ]
    run_list, raft_list = pG.make_run_pages(site_type="I&T-Raft", runs=runs_int)

    data_table_int = pG.write_table(run_list=run_list, raft_list=raft_list)

    pG_dev = plotGoodRaftRuns(db='Dev', server='Prod', base_dir=args.output)

    runs_int_dev = [5708, 5715, 5867, 5899, 5923, 5941, 5943, 6006 ]
    run_list, raft_list = pG_dev.make_run_pages(site_type="I&T-Raft", runs=runs_int_dev)

    data_table_int_dev = pG_dev.write_table(run_list=run_list, raft_list=raft_list)

    dash_file = args.output + 'bokehDashboard.html'
    output_file(dash_file)

    intro_text = "EO Test Results for Good Raft Runs (scroll if more than 10 entries)"
    pre_intro = PreText(text=intro_text, width=550, height=10)


    type_text = "BNL-Raft"
    pre = PreText(text=type_text, width=500, height=10)
    l = layout(pre_intro, pre, data_table_bnl)

    type_int = "I&T-Raft (Prod)"
    pre_int = PreText(text=type_int, width=500, height=10)
    l_int= layout(pre_int, data_table_int)

    type_int_dev = "I&T-Raft (Dev)"
    pre_int_dev = PreText(text=type_int_dev, width=500, height=10)
    l_int_dev= layout(pre_int_dev, data_table_int_dev)

    p = layout(l, [l_int, l_int_dev])

    save(p)

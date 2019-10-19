import numpy as np


def hook(run=None, mode=None, raft=None, ccd=None, test_cache=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
#    print ("called user hook with run ", str(run), " raft ", raft, " ccd ", ccd)
#    max = 144
#    if raft in ["R00", "R04", "R40", "R44"]:
#        max = 48
#    fake_list = [i*1. for i in range(max)]

    if raft in ["R00", "R04", "R40", "R44"]:
        return [1.]*48

    ptc_gain_dict = test_cache[run]["ptc_gain"][raft]
    ptc_gain = []
    for ccd in ptc_gain_dict:
        ptc_gain.extend(ptc_gain_dict[ccd])

    ptc_gain_error_dict = test_cache[run]["ptc_gain_error"][raft]
    ptc_gain_error = []
    for ccd in ptc_gain_error_dict:
        ptc_gain_error.extend(ptc_gain_error_dict[ccd])

    gain_ratio = np.array(ptc_gain_error)/np.array(ptc_gain)

    return gain_ratio.tolist()

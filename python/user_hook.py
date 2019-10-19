import numpy as np


def hook(run=None, mode=None, raft=None, ccd=None, test_cache=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """

    SR_slot_index = {"S00": 0, "S01": 16, "S02": 32, "S10": 48, "S11": 64, "S12": 80, "S20": 96, "S21": 112,
                     "S22": 128}

    if raft in ["R00", "R04", "R40", "R44"]:
        return [1.]*48

# 1 REB is dead in R10 - those amps are missing from the record, hence filling in the test array by position

    ptc_gain_dict = test_cache[run]["ptc_gain"][raft]
    ptc_gain = [-1.]*144
    for ccd in ptc_gain_dict:
        amp = 0
        for val in ptc_gain_dict[ccd]:
            ptc_gain[amp+SR_slot_index[ccd]] = ptc_gain_dict[ccd][amp]
            amp += 1

    ptc_gain_error_dict = test_cache[run]["ptc_gain_error"][raft]
    ptc_gain_error = [-1.]*144
    for ccd in ptc_gain_error_dict:
        amp = 0
        for val in ptc_gain_error_dict[ccd]:
            ptc_gain_error[amp+SR_slot_index[ccd]] = ptc_gain_error_dict[ccd][amp]
            amp += 1

    a = np.array(ptc_gain_error)
    b = np.array(ptc_gain)
    gain_ratio = np.divide(a, b, out=np.zeros_like(a),
                           where=b != 0)
    return gain_ratio.tolist()

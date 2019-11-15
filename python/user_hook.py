import numpy as np


def hook(run=None, mode=None, raft=None, ccd=None, test_cache=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
# SW0 and SW1 only use 0-7 for resukts. Arrange the indexes to overwrite the back half of
# SW0 with the front half of SW1

    slot_index = {"SG0": 0, "SG1": 16, "SW0": 32, "SW1": 40,
                  "S00": 0, "S01": 16, "S02": 32, "S10": 48,
                  "S11": 64, "S12": 80, "S20": 96, "S21": 112, "S22": 128}

    if raft in ["R00", "R04", "R40", "R44"]:
        test_len = 48
    else:
        test_len = 144

# 1 REB is dead in R10 - those amps are missing from the record, hence filling in the test array by position

    gain_dict = test_cache[run]["gain"][raft]
    gain = [-1.]*test_len
    for ccd in gain_dict:
        amp = 0
        for val in gain_dict[ccd]:
            if ccd == "SW1" and amp > 7:  # squish SW0 abd SW1 together
                continue
            gain[amp + slot_index[ccd]] = gain_dict[ccd][amp]
            amp += 1

    gain_error_dict = test_cache[run]["gain_error"][raft]
    gain_error = [-1.]*test_len
    for ccd in gain_error_dict:
        amp = 0
        for val in gain_error_dict[ccd]:
            if ccd == "SW1" and amp > 7:  # squish SW0 abd SW1 together
                continue
            gain_error[amp + slot_index[ccd]] = min(gain_error_dict[ccd][amp], 10.) # bogus errors in test run
            amp += 1

    a = np.array(gain_error)
    b = np.array(gain)
    gain_ratio = np.divide(a, b, out=np.zeros_like(a),
                           where=b != 0)

    return gain_ratio.tolist()

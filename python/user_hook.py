import numpy as np
from collections import OrderedDict
import random


def init(menu_button=None):
    print("user init setting up menu")
    my_menu = [("User test 1", "User test 1")]

    menu_button.menu = my_menu

    return 0


def hook(run=None, mode=None, raft=None, ccd=None, test_cache=None, test=None, range_limits=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
# SW0 and SW1 only use 0-7 for resukts. Arrange the indexes to overwrite the back half of
# SW0 with the front half of SW1


    s = {"SG0":0, "SG1":16, "SW0":32, "SW1":40,
                  "S00":0, "S01":16, "S02":32, "S10":48,
                  "S11":64, "S12":80, "S20":96, "S21":112, "S22":128}
    slot_index = OrderedDict(s)

    if raft in ["R00", "R04", "R40", "R44"]:
        test_len = 48
        out_list = [-1.] * test_len
        return out_list
    else:
        test_len = 144

    out_list = [-1.]*test_len

    for ccd in slot_index:
        if "SG" in ccd or "SW" in ccd:   # ignore CR
            continue

        # using list comprehension + randrange()
        # to generate random number list
        res = [random.randrange(0, 100, 1) for i in range(15)]

        amp = 0
        for val in res:
            out_list[amp + slot_index[ccd]] = val
            amp += 1

    range_limits["min"] = 5.
    range_limits["max"] = 20.
    range_limits["state"] = True

    return out_list

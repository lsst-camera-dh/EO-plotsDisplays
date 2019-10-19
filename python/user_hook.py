def hook(run=None, mode=None, raft=None, ccd=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
    print ("called user hook with run ", str(run), " raft ", raft, " ccd ", ccd)
    max = 144
    if raft in ["R00", "R04", "R40", "R44"]:
        max = 48
    fake_list = [i*1. for i in range(max)]
    return fake_list

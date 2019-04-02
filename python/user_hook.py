def hook(run=None, mode=None, slot=None):
    """
    User hook for test quantity
    :param run: run number
    :return: list of user-supplied quantities to be included in the heat map
    """
    print ("called user hook with run ", str(run))
    fake_list = [i*1. for i in range(1,145) ]
    return fake_list

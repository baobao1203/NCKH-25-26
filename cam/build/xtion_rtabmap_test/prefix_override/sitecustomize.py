import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/bao/NCKH-25-26/cam/install/xtion_rtabmap_test'

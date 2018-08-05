from unittest import TestCase
from dc_scanner_test import *


class TestScan_zonefile(TestCase):
    def test_scan_zonefile(self):
        try:
            th2 = 20
            start2 = time.time()
            cnt2 = scan_zonefile(num_threads=th2, zone_file='com.zone.43656', max_domains=10000, skip_first=20000)
            end2 = time.time()
        finally:
            print_api_providers()
            dump_api_providers('dump_test_200_thread.pckl')

        print("*****")
        print("{}: {}, {}, {}/domain".format(th2, end2 - start2, cnt2, float(end2 - start2) / float(cnt2)))
        print("*****")

    def test_load_api_providers(self):
        load_api_providers('dump_test_200_thread.pckl')
        print_api_providers()


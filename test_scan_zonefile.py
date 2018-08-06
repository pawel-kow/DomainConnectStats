from unittest import TestCase
from dc_scanner_test import *


class TestScan_zonefile(TestCase):
    def test_scan_zonefile(self):
        try:
            th2 = 250
            start2 = time.time()
            cnt2 = scan_zonefile(num_threads=th2, zone_file='com.zone.43656')
            end2 = time.time()
        finally:
            print_api_providers()
            dump_api_providers('dump_full2.pckl')

        print("*****")
        print("{}: {}, {}, {}/domain".format(th2, end2 - start2, cnt2, float(end2 - start2) / float(cnt2)))
        print("*****")

    def test_load_api_providers(self):
        load_api_providers('dump_full2.pckl')
        print_api_providers()

    def test_identify(self):
        api_url = identify_domain_connect_api('connect.domains')
        assert api_url == 'api.domainconnect.1and1.com'

    def test_scan(self):
        dc = DomainConnect()
        scan_dc_record(dc, 'connect.domains', Semaphore(10))
        assert 'https://api.domainconnect.1and1.com' in api_url_map

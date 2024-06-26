import os
from unittest import TestCase
from dc_scanner_test import *


class TestScan_zonefile(TestCase):
#    folder_prefix = 'output_Feb2024'
    folder_prefix = 'output_Jul2023'
    scan_file = 'save_final_dump_full_159000000.pckl'
    zone_file = 'zonefiles/com.txt.gz'

    def test_scan_zonefile(self):
        try:
            th2 = 250
            start2 = time.time()
            cnt2 = scan_zonefile(num_threads=th2, zone_file=TestScan_zonefile.zone_file, dump_filename=os.path.join(TestScan_zonefile.folder_prefix, 'dump_full_{cnt}.pckl'), dump_frequency=100000)
            end2 = time.time()
        finally:
            print_api_providers()
            dump_api_providers('dump_full_finished.pckl')

        print("*****")
        print("{}: {}, {}, {}/domain".format(th2, end2 - start2, cnt2, float(end2 - start2) / float(cnt2)))
        print("*****")

    def test_load_api_providers(self):
        load_api_providers(os.path.join(TestScan_zonefile.folder_prefix, TestScan_zonefile.scan_file))
        print_api_providers()

    def test_scan_supported_templates(self):
        print("Loading...")
        load_api_providers(os.path.join(TestScan_zonefile.folder_prefix, TestScan_zonefile.scan_file))
        print("  Loaded")
        dc = DomainConnect()
        templ = load_templates()
        print("Started a scan")
        add_api_providers_templates(dc, templ)
        print("  Scan finished")        
        print_api_providers(templ)
        dump_api_providers(os.path.join(TestScan_zonefile.folder_prefix, TestScan_zonefile.scan_file))

    def test_loadtemplates(self):
        templ = load_templates()
        assert len(templ) > 0
        print(templ)

    def test_identify(self):
        api_url = identify_domain_connect_api('connect.domains')
        assert api_url == 'api.domainconnect.1and1.com'

    def test_scan(self):
        dc = DomainConnect()
        scan_dc_record(dc, 'connect.domains', Semaphore(10))
        assert 'https://api.domainconnect.1and1.com' in api_url_map

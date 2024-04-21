import argparse
import os
import sys
from unittest import TestCase
from dc_scanner_test import *

class TestScanZonefile(TestCase):
    def __init__(self, folder_prefix, scan_file, zone_file):
        super().__init__()
        self.folder_prefix = folder_prefix
        self.scan_file = scan_file
        self.zone_file = zone_file

    def test_scan_zonefile(self):
        th2 = 250
        start2 = time.time()
        cnt2 = scan_zonefile(num_threads=th2, zone_file=self.zone_file, dump_filename=os.path.join(self.folder_prefix, 'dump_full_{cnt}.pckl'), dump_frequency=100000)
        end2 = time.time()
        print_api_providers()
        dump_api_providers('dump_full_finished.pckl')
        print("*****")
        print(f"{th2}: {end2 - start2}, {cnt2}, {float(end2 - start2) / float(cnt2)}/domain")
        print("*****")

    def test_scan_supported_templates(self):
        print("Loading...")
        load_api_providers(os.path.join(self.folder_prefix, self.scan_file))
        print("  Loaded")
        dc = DomainConnect()
        templ = load_templates()
        print("Started a scan")
        add_api_providers_templates(dc, templ)
        print("  Scan finished")
        print_api_providers(templ)
        dump_api_providers(os.path.join(self.folder_prefix, self.scan_file))

def main():
    parser = argparse.ArgumentParser(description="Script to scan zone files or supported templates.")
    parser.add_argument("action", choices=['scan_zonefile', 'scan_supported_templates'], help="Action to perform")
    parser.add_argument("--folder_prefix", default="output_default", help="Folder prefix for output files")
    parser.add_argument("--scan_file", default="save_final_dump.pckl", help="Scan file name")
    parser.add_argument("--zone_file", default="zonefiles/com.txt.gz", help="Zone file name")

    args = parser.parse_args()

    test_case = TestScanZonefile(args.folder_prefix, args.scan_file, args.zone_file)

    if args.action == 'scan_zonefile':
        test_case.test_scan_zonefile()
    elif args.action == 'scan_supported_templates':
        test_case.test_scan_supported_templates()

if __name__ == "__main__":
    main()

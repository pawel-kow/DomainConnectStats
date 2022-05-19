# DomainConnectStats
Domain Connect adoption statistics generator

## Running a scan:
- Create an output folder and adjust `folder_prefix”`in `test_scan_zonefile.py` accordingly
- Copy and unpack a .com zone file
- adjust line 14 of `test_scan_zonefile.py` to reflect the right file
- run `screen python -m unittest test_scan_zonefile.TestScan_zonefile.test_scan_zonefile`
This will scan the zone and output an intermediate file every 100.000 domains scanned
## Scan template support:
- Adjust `scan_file` in `test_scan_zonefile.py` to reflect the filename of an output file (final or intermediate)
- run `python -u -m unittest test_scan_zonefile.TestScan_zonefile.test_scan_supported_templates > domainconnect_with_templates.txt`
- `domainconnect_with_templates.txt` will contain results, bottom part in csv format for furhter processing in a spreadsheet

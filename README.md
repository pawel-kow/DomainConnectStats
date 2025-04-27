# DomainConnectStats
Domain Connect adoption statistics generator

## Installation

Download the repository and submodules
```
git clone git@github.com:pawel-kow/DomainConnectStats.git
cd DomainConnectStats/
git submodule init && git submodule update
```

Update the templates
```
cd Templates/
git pull origin master
cd ..
```

Create python virtual env and activate it
```
python3 -m venv .venv
. .venv/bin/activate
```

Restore packages
```
pip install -r requirements.txt
```

Configure ulimit
```
ulimit -n 64000
```

## Download zone files

- configure zone access in your ICANN account
- go to subfolder [./czds-api-client-python](./czds-api-client-python)
- follow [README](./czds-api-client-python/README.md) and configure your ```config.json```
  - set up `"working.directory": "../"`
- execute `python3 download.py`

## Running a scan:
- run `screen -dmS dc_scan_$(date +%b%Y) ./runscanner.sh output_$(date +%b%Y)`
This will scan the zone and output an intermediate file every 100.000 domains scanned. Logs are in `./logs` directory.

### Monitoring a scan
```
$ ps aux | grep python | grep scanner
$ screen -dmS monitor ./monitor_fds.sh <pid>
$ screen -dmS status ./top_api_logs.sh ./logs/<logfile>
```

## Scan template support:
- Adjust `scan_file` in `test_scan_zonefile.py` to reflect the filename of an output file (final or intermediate)
- run `python -u -m unittest test_scan_zonefile.TestScan_zonefile.test_scan_supported_templates > domainconnect_with_templates.txt`
- `domainconnect_with_templates.txt` will contain results, bottom part in csv format for furhter processing in a spreadsheet

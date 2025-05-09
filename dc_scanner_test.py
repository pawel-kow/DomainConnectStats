from domainconnect import *
from string import ascii_lowercase
from multiprocessing.pool import ThreadPool
from threading import Lock, Semaphore
from dns.resolver import Resolver
from dns.nameserver import Do53Nameserver
from dns.name import EmptyLabel
import humanize
import json
import os
import gzip

import time
import validators
import sys
import pickle

import socket

connection_timeout = 10
socket.setdefaulttimeout(connection_timeout)

_resolver = Resolver()
_resolver.timeout = 2
_resolver.lifetime = 5
_resolver.retry_servfail = True
_resolver.nameservers = [
	Do53Nameserver("9.9.9.10"), # Quad9 'insecure'
	Do53Nameserver("1.1.1.1"), # Cloudflare
	Do53Nameserver("1.0.0.1"), # Cloudflare
	Do53Nameserver("8.8.8.8"), # Google
	Do53Nameserver("8.8.4.4"), # Google
]

api_url_map = dict()
api_url_map_lck = Lock()

ns_map = dict()
ns_map_lck = Lock()

start = time.time()

class dns_provider_stats:
    def __init__(self, api_url, config, example_domain):
        self.cnt = 0
        self.api_url = api_url
        self.config = config
        self.nslist = dict()
        self.example_domain = example_domain
        self.supported_templates = []

def get_none_config(none_name):
    config = DomainConnectConfig(domain='dummy.local', domain_root='dummy.local',
                                 host='', config=dict())
    config.ProviderName = none_name
    return config


def scan_threaded(num_threads, label0):
    dc = DomainConnect()
    dc._resolver.timeout = _resolver.timeout
    dc._resolver.lifetime = _resolver.lifetime
    cnt = 0
    with ThreadPool(processes=num_threads) as pool:
        for label1 in ['a', 'b']:  # ascii_lowercase:
            for label2 in ['a', 'b']:  # ascii_lowercase:
                for label3 in ascii_lowercase:
                    for label4 in ascii_lowercase:
                        dom = '{}{}{}{}{}.com'.format(label0, label1, label2, label3, label4)
                        pool.apply_async(scan_dc_record, (dc, dom,))
                        cnt += 1
        pool.close()
        pool.join()
    return cnt


def scan_zonefile(num_threads, zone_file, max_domains=sys.maxsize, num_skip=0, skip_first=0, dump_filename=None,
                  dump_frequency=0):
    """

    :type num_threads: int
    :type zone_file: str
    :type max_domains: int
    :type num_skip: int
    :type skip_first: int
    :type dump_filename: str
    :type dump_frequency: int
    :return: int
    """
    start = time.time()
    dc = DomainConnect()
    dc._resolver.timeout = _resolver.timeout
    dc._resolver.lifetime = _resolver.lifetime

    sem = Semaphore(num_threads * 2)

    cnt = 0
    real_cnt = 0
    last_domain = ''
    print("*** Start ***")
    with ThreadPool(processes=num_threads) as pool:
        with gzip.open(zone_file) as f:
            for line in f:
                segments = line.decode().replace('\t', ' ').replace('\n', '').split(sep=' ')
                if (len(segments) == 3 and segments[1].lower() == 'ns') \
			or (len(segments) == 5 and segments[3].lower() == 'ns'):
                    domain = segments[0].lower()
                    domain = domain.rstrip('.') if domain.endswith('.') else '{}.com'.format(segments[0].lower())
                    if last_domain != domain:
                        cnt += 1
                        last_domain = domain
                        if cnt > skip_first and \
                            (num_skip == 0 or cnt % num_skip == 0):
                            real_cnt += 1
                            sem.acquire(blocking=True)
                            pool.apply_async(scan_dc_record, (dc, domain, sem,))
                            if dump_filename is not None and dump_frequency !=0 and real_cnt % dump_frequency == 0:
                                filename = dump_filename.format(cnt=real_cnt)
                                dump_api_providers(filename)
                if real_cnt >= max_domains:
                    break
        pool.close()
        pool.join()
    return real_cnt


def identify_nameservers(dom):
    try:
        dns = _resolver.query(dom, 'NS')
        return dns
    except:
        return []

def get_domain_config(dc, domain_root, domain_connect_api):
    """
    :param dc: DomainConnect object
    :type dc: DomainConnect
    :param domain_root: domain name
    :type domain_root: str
    :param domain_connect_api: url of domain connect apis
    :type domain_connect_api: str
    """
    ret = dc._get_domain_config_for_root(domain_root, domain_connect_api)
    return DomainConnectConfig(domain_root, domain_root, '', ret)

def identify_domain_connect_api(domain_root):
    # noinspection PyBroadException
    try:
        dns = _resolver.query('_domainconnect.{}'.format(domain_root), 'TXT')
        for resp in dns:
            api_url_resp = str(resp).replace('"', '')
            api_url = 'https://{}'.format(api_url_resp)
            if validators.url(api_url):
                logger.debug('Domain Connect API {} for {} found.'.format(api_url_resp, domain_root))
                return api_url_resp
        return 'None: No valid URL in answers'
    except Timeout:
        logger.debug('Timeout. Failed to find Domain Connect API for "{}"'.format(domain_root))
        return 'None: Timeout'
    except NXDOMAIN or YXDOMAIN:
        logger.debug('Failed to resolve "{}"'.format(domain_root))
        return 'None: NXDOMAIN or YXDOMAIN'
    except NoAnswer:
        logger.debug('No Domain Connect API found for "{}"'.format(domain_root))
        return 'None: NoAnswer'
    except NoNameservers:
        logger.debug('No nameservers avalaible for "{}"'.format(domain_root))
        return 'None: NoNameservers'
    except EmptyLabel:
        logger.debug('A DNS label is empty for "{}"'.format(domain_root))
        return 'None: EmptyLabel'
    except Exception as e:
        logger.debug('Exception for resolving "{}": {}'.format(domain_root, e))
        return 'None: Exception {}'.format(e)


def scan_dc_record(dc, dom, sem):
    """
    :param dc: DomainConnect object
    :type dc: DomainConnect
    :param dom: domain name
    :type dom: str
    """
    try:
        try:
            api_url_orig = identify_domain_connect_api(dom)
            if not api_url_orig.startswith('None'):
                api_url = 'https://{}'.format(api_url_orig)
                if validators.url(api_url):
                    # print("{}: {}".format(dom, api_url))
                    pass
                else:
                    api_url = 'None: Invalid URL'
                    # raise InvalidDomainConnectSettingsException("Invalid URL: {}".format(api_url))
            else:
                api_url = api_url_orig
            stats = None

            with api_url_map_lck:
                stats = api_url_map.get(api_url)
                if stats is None:
                    stats = dns_provider_stats(
                        api_url,
                        get_domain_config(dc=dc, domain_root=dom, domain_connect_api=api_url_orig)
                        if not api_url.startswith('None')
                        else get_none_config(api_url),
                        dom)
                    api_url_map[api_url] = stats
                stats.cnt += 1
                if (not api_url.startswith('None') and stats.cnt % 25 == 0) \
                        or (api_url.startswith('None') and stats.cnt % 250 == 0):
                    total_cnt = 0
                    for statitem in api_url_map.values():
                        total_cnt += statitem.cnt
                    print('[{:>9d} / {}] {}: {} ({:.2%})'.format(total_cnt, humanize.naturaldelta(time.time() - start), api_url, stats.cnt, float(stats.cnt) / total_cnt))

            if not api_url.startswith('None'):
                nslist = identify_nameservers(dom)
                with api_url_map_lck:
                    for ns in nslist:
                        ns_core = get_ns_core(dc, ns)
                        if ns_core not in stats.nslist:
                            stats.nslist[ns_core] = 1
                        else:
                            stats.nslist[ns_core] += 1

        except DomainConnectException:
            pass
    finally:
        sem.release()


def get_ns_core(dc, ns):
    ns_root = dc.identify_domain_root(str(ns))
    ns_expl = ns_root.split('.')
    ns_expl = ns_expl[:-1]
    return '.'.join(ns_expl)


def print_api_providers(templates=[]):
    print('API,Provider,Example domain,Count,Nameserver,{}'.format(','.join('{}/{}'.format(x[0], x[1]) for x in templates)))
    for line in api_url_map.keys():
        print("{},{},{},{},{},{}"
              .format(line, api_url_map[line].config.providerName, api_url_map[line].example_domain,
                      api_url_map[line].cnt, 
                      ';'.join('{}:{}'.format(x[0], x[1]) for x in sorted(api_url_map[line].nslist.items(), key=lambda k:k[1], reverse=True)),
                      ','.join(
                          'X' if hasattr(api_url_map[line], 'supported_templates')
                                 and templ in list(api_url_map[line].supported_templates)
                          else ''
                          for templ in templates
                      )
             ))
#', '.join(api_url_map[line].nslist.keys())))

def load_templates():
    templates = []
    dir = os.path.join(os.curdir, 'Templates')
    for template_file in [r for r in os.listdir(dir) if r.endswith('.json')]:
        with open(os.path.join(dir, template_file)) as f:
            template_json = json.load(f)
            templates += [(template_json['providerId'], template_json['serviceId'])]
    return templates


def add_api_providers_templates(dc, templates, num_threads=20):
    """
    :param dc: DomainConnect object
    :type dc: DomainConnect
    """
    with ThreadPool(processes=num_threads) as pool:
        providercounter = dict()
        for line in api_url_map.keys():
            name = api_url_map[line].config.providerName
            if name not in providercounter:
                providercounter[name] = 1
            else:
                providercounter[name] += 1
            if providercounter[name] < 5 or api_url_map[line].cnt > 100:
                api_url_map[line].supported_templates = []
                pool.apply_async(add_api_providers_templates_for_one, (dc, line, templates))
        pool.close()
        pool.join()


def add_api_providers_templates_for_one(dc, line, templates):
    if api_url_map[line].config.providerName in ['None', None]:
        print('Skipping empty provider: {}', api_url_map[line].config)
        return
    print('Checking {}'.format(line))
    for templ in templates:
        try:
            #print('  Checking: {}'.format(templ))
            dc.check_template_supported(api_url_map[line].config, templ[0], templ[1])
            print('    {}:\t{}\t{}\tOK'.format(api_url_map[line].config.providerName, templ[0], templ[1]))
            api_url_map[line].supported_templates += [templ]
        except TemplateNotSupportedException:
            print('    {}:\t{}\t{}\tNOK'.format(api_url_map[line].config.providerName, templ[0], templ[1]))
    print('Provider: {}, Templates: {}'.format(api_url_map[line].config.providerName,
                                               api_url_map[line].supported_templates))


def dump_api_providers(filename):
    with api_url_map_lck:
        with open(filename, 'wb') as output:
            pickle.dump(obj=api_url_map, file=output)

def load_api_providers(filename):
    global api_url_map
    with api_url_map_lck:
        with open(filename, 'rb') as input:
            api_url_map = pickle.load(input)

if __name__ == '__main__':
    th2 = 10

    start2 = time.time()
    cnt2 = scan_threaded(th2, 'k')
    end2 = time.time()

    print("*****")
    print("{}: {}, {}, {}/domain".format(th2, end2 - start2, cnt2, float(end2 - start2) / float(cnt2)))
    print("*****")

    print_api_providers()

    for line in ns_map.keys():
        print("NS: {}, Provider: {}".format(line, ns_map[line].config.providerName))

from domainconnect import *
from string import ascii_lowercase
from multiprocessing.pool import ThreadPool
from threading import Lock, Semaphore
from dns.resolver import Resolver

import time
import validators
import sys
import pickle

_resolver = Resolver()
_resolver.timeout = 10
_resolver.lifetime = 120

api_url_map = dict()
api_url_map_lck = Lock()

ns_map = dict()
ns_map_lck = Lock()


class dns_provider_stats:
    api_url = None
    config = None
    cnt = 0
    nslist = None  # type: dict

    def __init__(self, api_url, config):
        self.api_url = api_url
        self.config = config
        self.nslist = dict()


api_url_map['None'] = dns_provider_stats(api_url='None',
                                         config=DomainConnectConfig(domain='dummy.local', domain_root='dummy.local',
                                                                    host='', config=dict()))
api_url_map['None'].config.ProviderName = 'None'


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


def scan_zonefile(num_threads, zone_file, max_domains=sys.maxsize, num_skip=0):
    dc = DomainConnect()
    dc._resolver.timeout = _resolver.timeout
    dc._resolver.lifetime = _resolver.lifetime

    sem = Semaphore(num_threads * 2)

    cnt = 0
    last_domain = ''
    with ThreadPool(processes=num_threads) as pool:
        with open(zone_file) as f:
            for line in f:
                segments = line.split(sep=' ')
                if len(segments) == 3 and segments[1] == 'NS':
                    domain = '{}.com'.format(segments[0].lower())
                    if last_domain != domain:
                        cnt += 1
                        last_domain = domain
                        if num_skip == 0 or cnt % num_skip == 0:
                            sem.acquire(blocking=True)
                            pool.apply_async(scan_dc_record, (dc, domain, sem,))
                if cnt >= max_domains:
                    break
    pool.close()
    pool.join()
    return int(cnt / num_skip) if num_skip != 0 else cnt


def identify_nameservers(dom):
    try:
        dns = _resolver.query(dom, 'NS')
        return dns
    except:
        return []


def scan_dc_record(dc: DomainConnect, dom, sem):
    """
    :param dc: DomainConnect object
    :type dc: DomainConnect
    :param dom: domain name
    :type dom: str
    """
    try:
        try:
            try:
                api_url = dc._identify_domain_connect_api(dom)
                api_url = 'https://{}'.format(api_url)
                if validators.url(api_url):
                    # print("{}: {}".format(dom, api_url))
                    pass
                else:
                    api_url = 'None'
                    # raise InvalidDomainConnectSettingsException("Invalid URL: {}".format(api_url))
            except NoDomainConnectRecordException:
                api_url = 'None'

            stats = None

            with api_url_map_lck:
                stats = api_url_map.get(api_url)
                if stats is None:
                    stats = dns_provider_stats(api_url, dc.get_domain_config(domain=dom))
                    api_url_map[api_url] = stats
                stats.cnt += 1
                if (api_url != 'None' and stats.cnt % 25 == 0) \
                        or (api_url == 'None' and stats.cnt % 250 == 0):
                    print('{}: {}'.format(api_url, stats.cnt))

            if api_url != 'None':
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


def print_api_providers():
    for line in api_url_map.keys():
        print("API: {}, Provider: {}, Cnt: {}, NS: {}"
              .format(line, api_url_map[line].config.providerName,
                      api_url_map[line].cnt, ', '.join(api_url_map[line].nslist.keys())))


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

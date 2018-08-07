from domainconnect import *
from string import ascii_lowercase
from multiprocessing.pool import ThreadPool
from threading import Lock, Semaphore
from dns.resolver import Resolver
from dns.name import EmptyLabel
import humanize

import time
import validators
import sys
import pickle

_resolver = Resolver()
_resolver.timeout = 15
_resolver.lifetime = 120

api_url_map = dict()
api_url_map_lck = Lock()

ns_map = dict()
ns_map_lck = Lock()

start = time.time()

class dns_provider_stats:
    api_url = None
    config = None
    cnt = 0
    nslist = None  # type: dict

    def __init__(self, api_url, config):
        self.api_url = api_url
        self.config = config
        self.nslist = dict()


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


def scan_zonefile(num_threads, zone_file, max_domains=sys.maxsize, num_skip=0, skip_first=0):
    start = time.time()
    dc = DomainConnect()
    dc._resolver.timeout = _resolver.timeout
    dc._resolver.lifetime = _resolver.lifetime

    sem = Semaphore(num_threads * 2)

    cnt = 0
    real_cnt = 0
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
                        if cnt > skip_first and \
                            (num_skip == 0 or cnt % num_skip == 0):
                            real_cnt += 1
                            sem.acquire(blocking=True)
                            pool.apply_async(scan_dc_record, (dc, domain, sem,))
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
                        else get_none_config(api_url))
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

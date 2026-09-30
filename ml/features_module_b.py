"""Offline URL features shared by fitted pipelines and inference.

Text remains trimmed but otherwise unchanged, preserving the original char-TFIDF
baseline. Parsing adds HTTP only for schemeless inputs; it never visits a URL.
The bundled PSL is pinned by tldextract's version; downloads/cache are disabled.
"""
from collections import Counter
from ipaddress import ip_address
from math import log2
import re
from urllib.parse import urlsplit, unquote, parse_qsl

import numpy as np
import tldextract
from sklearn.base import BaseEstimator, TransformerMixin

PSL = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None,
                          include_psl_private_domains=False)
KEYWORDS = ('login', 'verify', 'account', 'password', 'secure', 'update',
            'bank', 'signin', 'confirm', 'wallet', 'payment', 'support')
SHORTENERS = frozenset(('bit.ly', 't.co', 'tinyurl.com', 'goo.gl', 'ow.ly',
                       'is.gd', 'buff.ly', 'rebrand.ly', 'cutt.ly', 'tiny.cc'))
FEATURE_NAMES = ('url_length', 'hostname_length', 'path_length', 'subdomain_count',
                 'digit_ratio', 'special_character_ratio', 'entropy', 'ip_hostname',
                 'idn_hostname', 'suspicious_keyword_count', 'encoded_character_count',
                 'hostname_hyphens', 'excessive_hyphens', 'known_shortener')


def clean_url(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError('URL must be a nonempty string')
    return url.strip()


def parse_url(url):
    text = clean_url(url)
    parsed = urlsplit(text if '://' in text else 'http://' + text.lstrip('/'))
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Expected an HTTP(S) URL with a hostname')
    # Accessing port validates malformed or out-of-range ports.
    parsed.port
    return parsed


def hostname(url):
    host = parse_url(url).hostname.rstrip('.').lower()
    return host.encode('idna').decode('ascii')


def is_ip(host):
    try:
        ip_address(host)
        return True
    except ValueError:
        return False


def registered_domain(url):
    host = hostname(url)
    if is_ip(host):
        return host
    result = PSL(host)
    # ICANN eTLD+1 deliberately groups all tenants of private hosting suffixes.
    # Unknown suffixes fall back to the full hostname, not an empty group.
    return result.top_domain_under_public_suffix or host


def near_duplicate_key(url):
    """Conservative within-host template audit, not a semantic equivalence test.

    Ignore scheme, fragment and query values; decode path and collapse digits.
    Generic paths on unrelated hosts are intentionally not equated.
    """
    parsed = parse_url(url)
    path = re.sub(r'\d+', '#', unquote(parsed.path).lower()).rstrip('/')
    keys = sorted(k.lower() for k, _ in parse_qsl(parsed.query, keep_blank_values=True))
    return hostname(url) + path + '?' + '&'.join(keys)


def url_features(url):
    text = clean_url(url)
    parsed = parse_url(text)
    host = hostname(text)
    parts = PSL(host)
    n = len(text)
    counts = Counter(text)
    lowered = unquote(text).lower()
    return [n, len(host), len(parsed.path),
            len(parts.subdomain.split('.')) if parts.subdomain and not is_ip(host) else 0,
            sum(c.isdigit() for c in text) / n,
            sum(not c.isalnum() for c in text) / n,
            -sum((v / n) * log2(v / n) for v in counts.values()),
            int(is_ip(host)), int(any(p.startswith('xn--') for p in host.split('.'))),
            sum(lowered.count(k) for k in KEYWORDS),
            len(re.findall(r'%[0-9a-fA-F]{2}', text)), host.count('-'),
            int(host.count('-') >= 3), int(host in SHORTENERS)]


class URLText(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return [clean_url(u) for u in X]


class URLFeatures(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.asarray([url_features(u) for u in X], dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FEATURE_NAMES, dtype=object)

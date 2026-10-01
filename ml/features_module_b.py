"""Offline URL features shared by fitted pipelines and inference.

Text remains trimmed but otherwise unchanged, preserving the original char-TFIDF
baseline. Parsing adds HTTP only for schemeless inputs; it never visits a URL.
The bundled PSL is pinned by tldextract's version; downloads/cache are disabled.

All rule-side analysis in ``ml/predict_module_b.py`` must go through the
centralized helpers here (parse_url/hostname/is_ip/registered_domain and the
``describe_*`` helpers below) so parsing semantics stay identical between the
fitted ``URLFeatures`` transformer and the serving-time rule layer.
"""
from collections import Counter
from ipaddress import ip_address, ip_network
import ipaddress
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
                       'is.gd', 'buff.ly', 'rebrand.ly', 'cutt.ly', 'tiny.cc',
                       'rb.gy', 's.id', 'shorturl.at', 'bitly.com', 't.ly'))
FEATURE_NAMES = ('url_length', 'hostname_length', 'path_length', 'subdomain_count',
                 'digit_ratio', 'special_character_ratio', 'entropy', 'ip_hostname',
                 'idn_hostname', 'suspicious_keyword_count', 'encoded_character_count',
                 'hostname_hyphens', 'excessive_hyphens', 'known_shortener')

# Centralized offline-analysis thresholds (single source of truth for rules).
LONG_URL_CHARS = 75
EXTREME_URL_CHARS = 200
EXCESSIVE_SUBDOMAINS = 4
HIGH_ENTROPY_THRESHOLD = 4.5
DEFAULT_PORTS = {'http': 80, 'https': 443}
REDIRECT_PARAM_NAMES = frozenset((
    'url', 'u', 'redirect', 'redirect_uri', 'redirect_url', 'next', 'next_url',
    'continue', 'dest', 'destination', 'to', 'target', 'r', 'return',
    'returnurl', 'return_url', 'rurl', 'goto', 'go', 'out', 'link',
))
SUSPICIOUS_PATH_KEYWORDS = (
    'login', 'signin', 'verify', 'account', 'password', 'secure', 'update',
    'confirm', 'wallet', 'payment', 'bank', 'support', 'kyc', 'otp',
)
_PRIVATE_NETWORKS_V4 = (
    ip_network('10.0.0.0/8'), ip_network('172.16.0.0/12'),
    ip_network('192.168.0.0/16'), ip_network('127.0.0.0/8'),
    ip_network('169.254.0.0/16'), ip_network('0.0.0.0/8'),
)
_PRIVATE_NETWORKS_V6 = (
    ip_network('::1/128'), ip_network('fc00::/7'), ip_network('fe80::/10'),
)
# Homoglyph / look-alike hints: mixed scripts, confusable digit/letter swaps.
_CONFUSABLE_RE = re.compile(r'(0[a-z]*o|o[a-z]*0|1[a-z]*l|l[a-z]*1|rn|vv|cl)', re.IGNORECASE)


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


def shannon_entropy(text: str) -> float:
    """Character entropy of the raw URL string (obfuscation signal)."""
    text = clean_url(text)
    n = len(text)
    counts = Counter(text)
    return float(-sum((v / n) * log2(v / n) for v in counts.values()))


def ip_version(host: str) -> int | None:
    """4 for IPv4, 6 for IPv6, None for DNS names. Centralized via ipaddress."""
    try:
        return ip_address(host).version
    except ValueError:
        return None


def is_private_or_internal(host: str) -> bool:
    """True for localhost, loopback, link-local and RFC-1918/4193 targets.

    Never performs DNS; only literal IP hostnames are evaluated.
    """
    lowered = host.strip().lower().rstrip('.')
    if lowered == 'localhost':
        return True
    try:
        addr = ip_address(host)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
        return True
    try:
        if addr.version == 4:
            return any(addr in net for net in _PRIVATE_NETWORKS_V4)
        return any(addr in net for net in _PRIVATE_NETWORKS_V6)
    except Exception:
        return False


def is_localhost_target(url: str) -> bool:
    try:
        host = hostname(url)
    except Exception:
        return False
    return host == 'localhost' or is_private_or_internal(host)


def describe_port(url: str) -> dict:
    """Offline port finding. Never connects; only inspects the parsed port."""
    parsed = parse_url(url)
    try:
        port = parsed.port
    except ValueError:
        return {'present': False, 'malformed': True, 'unusual': False, 'port': None}
    if port is None:
        return {'present': False, 'malformed': False, 'unusual': False, 'port': None}
    unusual = port != DEFAULT_PORTS.get(parsed.scheme.lower(), None)
    return {'present': True, 'malformed': False, 'unusual': unusual, 'port': port}


def subdomain_count(url: str) -> int:
    host = hostname(url)
    if is_ip(host):
        return 0
    parts = PSL(host)
    if not parts.subdomain:
        return 0
    return len(parts.subdomain.split('.'))


def is_idn_host(url: str) -> bool:
    try:
        host = hostname(url)
    except Exception:
        return False
    return any(part.startswith('xn--') for part in host.split('.'))


def is_shortener_host(url: str) -> bool:
    try:
        return hostname(url) in SHORTENERS
    except Exception:
        return False


def describe_hostname(url: str) -> dict:
    """Offline malformed-hostname audit. Returns flags, never raises for shape."""
    try:
        host = hostname(url)
    except Exception:
        return {'malformed': True, 'reasons': ['unparseable hostname']}
    reasons = []
    if not host or len(host) > 253:
        reasons.append('invalid hostname length')
    for label in host.split('.'):
        if not label:
            reasons.append('empty hostname label')
            break
        if len(label) > 63:
            reasons.append('hostname label exceeds 63 characters')
            break
        if label.startswith('-') or label.endswith('-'):
            reasons.append('hostname label has leading/trailing hyphen')
            break
        if '_' in label:
            reasons.append('hostname contains underscore')
            break
        if not re.fullmatch(r'[a-z0-9-]+', label) and not is_ip(host):
            # IDN/punycode labels (xn--) already match; anything else is suspect.
            if not label.startswith('xn--'):
                reasons.append('hostname contains invalid characters')
                break
    # IPv6 zone identifiers ('%eth0') never appear via hostname parsing; a raw
    # '%' in the host part indicates manual obfuscation.
    return {'host': host, 'malformed': bool(reasons), 'reasons': reasons}


def suspicious_encoded_chars(url: str) -> list:
    """Suspicious percent-encodings: null/control, delimiters, double-encoding."""
    text = clean_url(url)
    hits = []
    for match in re.finditer(r'%([0-9a-fA-F]{2})', text):
        byte = int(match.group(1), 16)
        token = match.group(0)
        if byte <= 0x1F or byte == 0x7F or token.lower() in ('%00', '%2e', '%2f', '%5c', '%40', '%23', '%3f'):
            hits.append(token)
    if re.search(r'%25[0-9a-fA-F]{2}', text):
        hits.append('double-encoded %25')
    return hits


def suspicious_path_query(url: str) -> list:
    """Offline path/query phishing patterns (credential, payment, file tricks)."""
    parsed = parse_url(url)
    lowered_path = unquote(parsed.path).lower()
    lowered_query = unquote(parsed.query).lower()
    hits = []
    combined = lowered_path + '?' + lowered_query
    for keyword in SUSPICIOUS_PATH_KEYWORDS:
        if keyword in lowered_path or keyword in lowered_query:
            hits.append(keyword)
    if re.search(r'\.(php|asp|aspx|jsp|exe|scr|zip|rar)\b', lowered_path):
        hits.append('executable/script file extension in path')
    if '//' in lowered_path.strip('/'):
        # 'http://host//evil' or embedded '//' after decoding.
        pass  # handled by '@'/redirect checks; kept explicit for auditability.
    if lowered_query and any(sym in url for sym in ('@', '%40')):
        hits.append('credential-like symbol with query')
    return sorted(set(hits))


def nested_redirect_target(url: str) -> str | None:
    """Return the embedded redirect target if a query param nests another URL."""
    try:
        parsed = parse_url(url)
    except Exception:
        return None
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in REDIRECT_PARAM_NAMES:
            decoded = unquote(value).strip().lower()
            if decoded.startswith(('http://', 'https://', '//')) or re.match(r'[a-z0-9.-]+\.[a-z]{2,}/', decoded):
                return value[:200]
    # Also catch path-embedded 'http' after the authority (open-redirect style).
    try:
        after_host = url.split(parsed.hostname, 1)[1] if parsed.hostname else ''
        if re.search(r'https?%?(3a|:)%?(%2f|/){2}', after_host, re.IGNORECASE) or after_host.lower().count('http') >= 1 and '://' in after_host:
            return after_host[:200]
    except Exception:
        pass
    return None


def lookalike_indicators(url: str) -> list:
    """Offline look-alike hints: excessive digits/hyphens, confusables, punycode."""
    try:
        host = hostname(url)
    except Exception:
        return []
    if is_ip(host):
        return []
    hints = []
    if is_idn_host(url):
        hints.append('punycode (xn--) hostname')
    labels = host.split('.')
    main = labels[0] if labels else host
    if sum(ch.isdigit() for ch in host) >= 4:
        hints.append('excessive digits in hostname')
    if re.search(r'[a-z]', main) and re.search(r'\d', main):
        hints.append('letter-digit mix in domain (possible look-alike)')
    if host.count('-') >= 3:
        hints.append('excessive hyphens in hostname')
    if _CONFUSABLE_RE.search(main):
        hints.append('confusable character pattern in domain')
    if re.search(r'(.)\1{3,}', main):
        hints.append('repeated-character run in domain')
    return hints


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

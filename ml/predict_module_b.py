import os
import math
from difflib import SequenceMatcher
try:
    from ml.model_loading import load_artifact
except ImportError:
    from model_loading import load_artifact
try:
    from ml.features_module_b import (
        clean_url, parse_url, hostname as parsed_hostname, is_ip as parsed_is_ip,
        describe_port, subdomain_count, is_idn_host, is_shortener_host,
        describe_hostname, suspicious_encoded_chars, suspicious_path_query,
        nested_redirect_target, lookalike_indicators, is_private_or_internal,
        shannon_entropy, ip_version,
        LONG_URL_CHARS, EXTREME_URL_CHARS, EXCESSIVE_SUBDOMAINS,
        HIGH_ENTROPY_THRESHOLD,
    )
except ModuleNotFoundError:
    from features_module_b import (
        clean_url, parse_url, hostname as parsed_hostname, is_ip as parsed_is_ip,
        describe_port, subdomain_count, is_idn_host, is_shortener_host,
        describe_hostname, suspicious_encoded_chars, suspicious_path_query,
        nested_redirect_target, lookalike_indicators, is_private_or_internal,
        shannon_entropy, ip_version,
        LONG_URL_CHARS, EXTREME_URL_CHARS, EXCESSIVE_SUBDOMAINS,
        HIGH_ENTROPY_THRESHOLD,
    )

# -----------------------------------------------------------------------------
# NAMED RULE WEIGHT CONSTANTS
# -----------------------------------------------------------------------------
WEIGHT_IP_ADDRESS = 0.40
WEIGHT_TYPOSQUATTING = 0.35
WEIGHT_INSECURE_HTTP = 0.20
WEIGHT_SUSPICIOUS_TLD = 0.20
WEIGHT_URL_OBFUSCATION = 0.15
WEIGHT_SUSPICIOUS_LENGTH = 0.10
# Offline-only extensions (no network egress; all via centralized parsing).
WEIGHT_UNUSUAL_PORT = 0.15
WEIGHT_EXCESSIVE_SUBDOMAINS = 0.15
WEIGHT_IDN_HOST = 0.15
WEIGHT_SHORTENER = 0.25
WEIGHT_PRIVATE_TARGET = 0.25
WEIGHT_MALFORMED_HOST = 0.25
WEIGHT_SUSPICIOUS_PATH_QUERY = 0.15
WEIGHT_NESTED_REDIRECT = 0.20
WEIGHT_HIGH_ENTROPY = 0.10
WEIGHT_EXTREME_LENGTH = 0.15
WEIGHT_SUSPICIOUS_ENCODING = 0.15
WEIGHT_LOOKALIKE = 0.15

# Target brand list for typosquatting / similarity checks
CANONICAL_BRAND_DOMAINS = {
    "hdfc": {"hdfcbank.com", "hdfc.com", "hdfcbank.co.in"},
    "hdfcbank": {"hdfcbank.com", "hdfcbank.co.in"},
    "icici": {"icicibank.com", "icicibank.org"},
    "icicibank": {"icicibank.com", "icicibank.org"},
    "sbi": {"sbi.co.in", "onlinesbi.sbi", "statebankofindia.com"},
    "paytm": {"paytm.com", "paytmbank.com"},
    "google": {"google.com", "google.co.in"},
    "paypal": {"paypal.com", "paypal.me"},
    "amazon": {"amazon.com", "amazon.in"},
    "axisbank": {"axisbank.com"},
    "kotak": {"kotak.com"},
    "phonepe": {"phonepe.com"}
}

HIGH_RISK_TLDS = {
    ".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".site", ".work",
    ".click", ".link", ".download", ".racing", ".zip", ".review"
}

_ML_MODEL_ARTIFACT = None

def _get_model_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    return os.path.join(project_root, "ml", "models", "module_b.pkl")

def _load_ml_model(model_path: str = None):
    global _ML_MODEL_ARTIFACT
    if model_path is None:
        model_path = _get_model_path()
    
    _ML_MODEL_ARTIFACT = load_artifact(model_path, _ML_MODEL_ARTIFACT)
    return _ML_MODEL_ARTIFACT


def check_typosquatting(hostname: str) -> tuple[bool, str]:
    """
    Checks if hostname attempts brand typosquatting or similarity spoofing.
    Returns (is_typosquatted, matched_brand)
    """
    clean_host = hostname.lower().removeprefix("www.")
    domain_parts = clean_host.split(".")
    main_domain = domain_parts[0] if domain_parts else clean_host

    for brand, canonical_domains in CANONICAL_BRAND_DOMAINS.items():
        # Canonical domain check (e.g. hdfcbank.com is legitimate)
        if any(clean_host == domain or clean_host.endswith("." + domain) for domain in canonical_domains):
            continue

        # 1. Brand name embedded in suspicious domain (e.g., hdfcbank-login.com or paytm-verify.net)
        if brand in clean_host:
            return True, brand

        # 2. Similarity ratio / edit distance check (e.g. hdfcbaank or paytmm)
        ratio = SequenceMatcher(None, main_domain, brand).ratio()
        if 0.78 <= ratio < 1.0:
            return True, brand

    return False, ""



def inspect_live_page(url: str) -> tuple[bool, str, list[str]]:
    """Compatibility stub: user-supplied destinations are never fetched.

    Kept so callers can assert the no-egress contract; it performs no I/O and
    therefore never contributes a login-form finding or any score weight.
    """
    return False, url, ["Live page fetching is disabled; only offline URL checks ran."]


def check_url(url: str, fetch_live_page: bool = False) -> dict:
    """
    Evaluates URL safety score (0.0 to 1.0) and generates human-readable risk explanations.

    Returns:
    --------
    dict: {
        "score": float (0.0 safe to 1.0 phishing/dangerous),
        "reasons": list[str],
        "ml_status": str
    }
    """
    url = clean_url(url)
    parsed_url = parse_url(url)
    hostname = parsed_hostname(url)
    is_https = parsed_url.scheme.lower() == "https"

    reasons = []
    rule_score_sum = 0.0

    # 1. HTTP vs HTTPS check
    if not is_https:
        rule_score_sum += WEIGHT_INSECURE_HTTP
        reasons.append("Insecure protocol: URL does not use encrypted HTTPS connection")

    # 2. IP Address Host check (IPv4 and IPv6 via centralized ipaddress parsing).
    ip_ver = ip_version(hostname)
    if parsed_is_ip(hostname):
        rule_score_sum += WEIGHT_IP_ADDRESS
        label = f"IPv{ip_ver}" if ip_ver else "IP"
        reasons.append(f"Host is a raw IP address ({label}; {hostname}) rather than a registered domain name")

    # 2b. Localhost / private / internal targets (extra suspicion beyond raw IP).
    if is_private_or_internal(hostname):
        rule_score_sum += WEIGHT_PRIVATE_TARGET
        reasons.append(f"Localhost/private/internal target ({hostname}); not a public destination")

    # 3. Typosquatting & Brand Impersonation check
    is_typosquatted, brand = check_typosquatting(hostname)
    if is_typosquatted:
        rule_score_sum += WEIGHT_TYPOSQUATTING
        reasons.append(f"Potential typosquatting / brand spoofing targeting '{brand}'")

    # 3b. Generic look-alike indicators (confusables, digits, punycode handled
    # separately). Hyphen overuse is counted once in the obfuscation bucket, so
    # it is excluded here to avoid double-counting the same characters.
    lookalikes = [h for h in lookalike_indicators(url) if 'hyphen' not in h]
    if is_idn_host(url) and 'punycode (xn--) hostname' in lookalike_indicators(url):
        # Punycode gets its own IDN weight below; don't double-count here.
        lookalikes = [h for h in lookalikes if 'punycode' not in h]
    if lookalikes:
        rule_score_sum += WEIGHT_LOOKALIKE
        reasons.append(f"Look-alike domain indicators: {'; '.join(sorted(set(lookalikes)))}")

    # 3c. IDN / punycode hostname.
    if is_idn_host(url):
        rule_score_sum += WEIGHT_IDN_HOST
        reasons.append("Internationalized (punycode xn--) hostname; visually confusable domains possible")

    # 3d. Known URL shortener (destination hidden without fetching).
    if is_shortener_host(url):
        rule_score_sum += WEIGHT_SHORTENER
        reasons.append(f"Known URL shortener ({hostname}); final destination is hidden without following redirects")

    # 4. High-Risk TLD check
    tld_match = [tld for tld in HIGH_RISK_TLDS if hostname.endswith(tld)]
    if tld_match:
        rule_score_sum += WEIGHT_SUSPICIOUS_TLD
        reasons.append(f"High-risk top-level domain detected ({tld_match[0]})")

    # 5. URL Obfuscation / Special Characters
    obfuscated = False
    if "@" in url:
        obfuscated = True
        reasons.append("URL contains '@' user-credential symbol (frequently used for domain masking)")
    if hostname.count("-") >= 3:
        obfuscated = True
        reasons.append(f"Excessive hyphens ({hostname.count('-')}) in domain name")
    if "%" in url:
        obfuscated = True
        reasons.append("URL contains hex-encoded characters")

    if obfuscated:
        rule_score_sum += WEIGHT_URL_OBFUSCATION

    # 5b. Suspicious encoded bytes (control chars, delimiters, double-encoding).
    # Escalation on top of the generic hex-encoding bucket above.
    suspicious_enc = suspicious_encoded_chars(url)
    if suspicious_enc:
        rule_score_sum += WEIGHT_SUSPICIOUS_ENCODING
        reasons.append(f"Suspicious encoded characters: {', '.join(sorted(set(suspicious_enc))[:5])}")

    # 5c. Malformed hostname labels (offline audit; unparseable URLs already raise).
    host_audit = describe_hostname(url)
    if host_audit.get('malformed'):
        rule_score_sum += WEIGHT_MALFORMED_HOST
        reasons.append(f"Malformed hostname: {'; '.join(host_audit.get('reasons', ['invalid']))}")

    # 5d. Unusual port (non-default or explicitly specified).
    port_info = describe_port(url)
    if port_info.get('unusual'):
        rule_score_sum += WEIGHT_UNUSUAL_PORT
        reasons.append(f"Unusual port (:{port_info.get('port')}) for {parsed_url.scheme.lower()}")

    # 5e. Excessive subdomains (depth used to bury the real domain).
    try:
        n_sub = subdomain_count(url)
    except Exception:
        n_sub = 0
    if n_sub >= EXCESSIVE_SUBDOMAINS:
        rule_score_sum += WEIGHT_EXCESSIVE_SUBDOMAINS
        reasons.append(f"Excessive subdomains ({n_sub} levels); real domain may be buried")

    # 5f. Suspicious path/query patterns (credential, payment, executable).
    pq_hits = suspicious_path_query(url)
    # Avoid double-counting the generic '@'-with-query hint when '@' already fired.
    pq_hits = [h for h in pq_hits if not (h == 'credential-like symbol with query' and "@" in url)]
    if pq_hits:
        rule_score_sum += WEIGHT_SUSPICIOUS_PATH_QUERY
        shown = ', '.join(pq_hits[:5])
        reasons.append(f"Suspicious path/query patterns: {shown}")

    # 5g. Nested redirect / open-redirect parameter embedding another URL.
    nested = nested_redirect_target(url)
    if nested:
        rule_score_sum += WEIGHT_NESTED_REDIRECT
        reasons.append(f"Nested redirect parameter embeds another URL ({nested[:80]})")

    # 6. Suspicious Length check (tiered: long, then extremely long escalation).
    if len(url) > LONG_URL_CHARS:
        rule_score_sum += WEIGHT_SUSPICIOUS_LENGTH
        reasons.append(f"Excessively long URL ({len(url)} characters)")
    if len(url) > EXTREME_URL_CHARS:
        rule_score_sum += WEIGHT_EXTREME_LENGTH
        reasons.append(f"Extremely long URL ({len(url)} characters); typical of obfuscated payloads")

    # 6b. High character entropy (random-looking / generated strings).
    try:
        entropy = shannon_entropy(url)
    except Exception:
        entropy = 0.0
    if entropy >= HIGH_ENTROPY_THRESHOLD:
        rule_score_sum += WEIGHT_HIGH_ENTROPY
        reasons.append(f"High URL entropy ({entropy:.2f}); random-looking or generated string")

    # 7. Live page inspection is permanently disabled. When a caller still asks
    # for it, surface that fact in the reasons instead of inventing findings.
    if fetch_live_page:
        _has_login_form, _final_url, page_reasons = inspect_live_page(url)
        reasons.extend(page_reasons)

    # Cap rule risk score at 1.0
    rule_score = min(1.0, rule_score_sum)

    # 8. Check ML Model Combination if available
    artifact = _load_ml_model()
    if artifact is not None:
        try:
            pipeline = artifact["pipeline"]
            phishing_index = list(pipeline.classes_).index(1)
            ml_proba = float(pipeline.predict_proba([url])[0, phishing_index])
            if not math.isfinite(ml_proba) or not 0 <= ml_proba <= 1:
                raise ValueError("Invalid model output")
            final_score = round(min(1.0, 0.50 * rule_score + 0.50 * ml_proba), 4)
            ml_status = "active"
        except Exception:
            final_score = round(rule_score, 4)
            ml_status = "rules_only (ML inference failed)"
    else:
        final_score = round(rule_score, 4)
        ml_status = "rules_only (model unavailable)"

    return {
        "score": final_score,
        "reasons": reasons,
        "ml_status": ml_status
    }

if __name__ == "__main__":
    test_urls = [
        "https://www.hdfcbank.com/personal/pay",
        "http://192.168.1.1/verify-account",
        "http://hdfcbaank-login.xyz/update-kyc",
        "http://t.co/abc"
    ]
    for test_u in test_urls:
        res = check_url(test_u, fetch_live_page=False)
        print(f"URL: {test_u}\nResult: {res}\n")

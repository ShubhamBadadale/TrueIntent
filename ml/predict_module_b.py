import re
import os
import urllib.parse
from difflib import SequenceMatcher
import joblib

# Optional requests import for live page fetching
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# -----------------------------------------------------------------------------
# NAMED RULE WEIGHT CONSTANTS
# -----------------------------------------------------------------------------
WEIGHT_IP_ADDRESS = 0.40
WEIGHT_TYPOSQUATTING = 0.35
WEIGHT_LOGIN_FORM_PRESENT = 0.25
WEIGHT_INSECURE_HTTP = 0.20
WEIGHT_SUSPICIOUS_TLD = 0.20
WEIGHT_URL_OBFUSCATION = 0.15
WEIGHT_SUSPICIOUS_LENGTH = 0.10

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
    
    if _ML_MODEL_ARTIFACT is None or _ML_MODEL_ARTIFACT.get("_path") != model_path:
        if os.path.exists(model_path):
            try:
                artifact = joblib.load(model_path)
                artifact["_path"] = model_path
                _ML_MODEL_ARTIFACT = artifact
            except Exception:
                _ML_MODEL_ARTIFACT = None
        else:
            _ML_MODEL_ARTIFACT = None
    return _ML_MODEL_ARTIFACT


def is_ip_address(hostname: str) -> bool:
    """Checks if host is an IPv4 address."""
    ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    return bool(re.match(ipv4_pattern, hostname))


def check_typosquatting(hostname: str) -> tuple[bool, str]:
    """
    Checks if hostname attempts brand typosquatting or similarity spoofing.
    Returns (is_typosquatted, matched_brand)
    """
    clean_host = hostname.lower().replace("www.", "")
    domain_parts = clean_host.split(".")
    main_domain = domain_parts[0] if domain_parts else clean_host

    for brand, canonical_domains in CANONICAL_BRAND_DOMAINS.items():
        # Canonical domain check (e.g. hdfcbank.com is legitimate)
        if clean_host in canonical_domains:
            continue

        # 1. Brand name embedded in suspicious domain (e.g., hdfcbank-login.com or paytm-verify.net)
        if brand in clean_host:
            return True, brand

        # 2. Similarity ratio / edit distance check (e.g. hdfcbaank or paytmm)
        ratio = SequenceMatcher(None, main_domain, brand).ratio()
        if 0.78 <= ratio < 1.0:
            return True, brand

    return False, ""



def inspect_live_page(url: str, timeout: float = 2.0) -> tuple[bool, str, list[str]]:
    """
    Option (a): Lightweight page-fetch step.
    Follows redirects (up to 2.0 sec timeout) and checks destination HTML for login forms.
    Returns (has_login_form, final_url, page_reasons)
    """
    if not REQUESTS_AVAILABLE:
        return False, url, []

    reasons = []
    has_login_form = False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrueIntent/1.0 URLChecker"
        }
        response = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers)
        final_url = response.url

        # Check redirect domain shift
        orig_parsed = urllib.parse.urlparse(url)
        final_parsed = urllib.parse.urlparse(final_url)
        if orig_parsed.netloc and final_parsed.netloc and orig_parsed.netloc != final_parsed.netloc:
            reasons.append(f"Redirect chain detected: redirected from {orig_parsed.netloc} to {final_parsed.netloc}")

        # HTML Login Form detection
        if response.status_code == 200:
            content_lower = response.text.lower()
            if "<form" in content_lower and ("type=\"password\"" in content_lower or "type='password'" in content_lower or "name=\"password\"" in content_lower or "login" in content_lower):
                has_login_form = True
                reasons.append("Destination page contains a login / credential entry form")
    except Exception:
        # Gracefully handle timeouts or connection failures without breaking inference
        pass

    return has_login_form, url, reasons


def check_url(url: str, fetch_live_page: bool = True) -> dict:
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
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        # Default to http:// for parsing if scheme missing
        parsed_url = urllib.parse.urlparse("http://" + url)
        has_explicit_scheme = False
        is_https = False
    else:
        parsed_url = urllib.parse.urlparse(url)
        has_explicit_scheme = True
        is_https = (parsed_url.scheme.lower() == "https")

    hostname = parsed_url.netloc.split(":")[0] if parsed_url.netloc else parsed_url.path.split("/")[0]

    reasons = []
    rule_score_sum = 0.0

    # 1. HTTP vs HTTPS check
    if not is_https:
        rule_score_sum += WEIGHT_INSECURE_HTTP
        reasons.append("Insecure protocol: URL does not use encrypted HTTPS connection")

    # 2. IP Address Host check
    if is_ip_address(hostname):
        rule_score_sum += WEIGHT_IP_ADDRESS
        reasons.append(f"Host is a raw IP address ({hostname}) rather than a registered domain name")

    # 3. Typosquatting & Brand Impersonation check
    is_typosquatted, brand = check_typosquatting(hostname)
    if is_typosquatted:
        rule_score_sum += WEIGHT_TYPOSQUATTING
        reasons.append(f"Potential typosquatting / brand spoofing targeting '{brand}'")

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

    # 6. Suspicious Length check
    if len(url) > 75:
        rule_score_sum += WEIGHT_SUSPICIOUS_LENGTH
        reasons.append(f"Excessively long URL ({len(url)} characters)")

    # 7. Live Page Fetch & Login Form Detection (Option a)
    if fetch_live_page and url.startswith(("http://", "https://")):
        has_login_form, final_url, page_reasons = inspect_live_page(url)
        reasons.extend(page_reasons)
        if has_login_form:
            rule_score_sum += WEIGHT_LOGIN_FORM_PRESENT

    # Cap rule risk score at 1.0
    rule_score = min(1.0, rule_score_sum)

    # 8. Check ML Model Combination if available
    artifact = _load_ml_model()
    if artifact is not None:
        try:
            pipeline = artifact["pipeline"]
            ml_proba = float(pipeline.predict_proba([url])[0, 1])
            final_score = round(min(1.0, 0.50 * rule_score + 0.50 * ml_proba), 4)
            ml_status = "combined (rules + ML classifier)"
        except Exception:
            final_score = round(rule_score, 4)
            ml_status = "rules_only (ML inference failed)"
    else:
        final_score = round(rule_score, 4)
        ml_status = "rules_only (dataset pending)"

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

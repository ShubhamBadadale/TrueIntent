"""Shared, Unicode-preserving text features and explicit intent definitions."""
import re
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

INTENTS = ('benign', 'urgency_pressure', 'authority_fear', 'digital_arrest',
           'investment_scam', 'kyc_upi_scam', 'impersonation',
           'courier_customs_scam', 'credential_theft', 'other_fraud')
# Structured heuristic evidence taxonomy. Heuristics are evidence only: they
# never set a score, a signature or an ML probability. One entry per signal
# per message (deduplicated) so repeated wording cannot inflate severity.
HEURISTIC_CATEGORIES = (
    'urgency', 'threats', 'fear', 'authority_impersonation', 'investment_scam',
    'guaranteed_rewards', 'credential_request', 'otp_request', 'payment_request',
    'remote_access_request', 'account_suspension', 'kyc_update_scam',
    'suspicious_links',
)
HEURISTIC_SEVERITIES = ('low', 'medium', 'high')

# signal -> (category, description, severity, [regex patterns on normalized text])
HEURISTIC_DEFINITIONS = (
    ('urgency_keywords', 'urgency',
     'Time pressure pushing the reader to act without verifying.',
     'medium',
     (r'\burgent\b', r'\bact (now|immediately)\b', r'\bimmediately\b',
      r'\blimited time\b', r'\bhurry\b', r'\bexpires?\b', r'\blast chance\b',
      r'\bdo not delay\b', r'\bright ?now\b')),
    ('threat_language', 'threats',
     'Explicit threats of arrest, legal action or harm.',
     'high',
     (r'\barrest warrant\b', r'\bwill be arrested\b', r'\blegal action\b',
      r'\bpolice case\b', r'\bfir\b', r'\bjail\b', r'\bsevere consequences\b')),
    ('fear_pressure', 'fear',
     'Fear-based coercion (investigation, secrecy, staying on the line).',
     'high',
     (r'\bunder investigation\b', r'\bmoney laundering\b',
      r'\bstay on the (line|call)\b', r'\bdo not (disconnect|hang ?up)\b',
      r'\bkeep this confidential\b', r'\bdigital arrest\b')),
    ('authority_impersonation', 'authority_impersonation',
     'Claims to be police, court, central agency or bank authority.',
     'high',
     (r'\bcbi\b', r'\bed\b', r'\brbi\b', r'\bpolice officer\b',
      r'\bcourt order\b', r'\bcyber ?crime\b', r'\bincome tax department\b',
      r'\bcustoms officer\b', r'\bgovernment (of india|official)\b')),
    ('investment_scam', 'investment_scam',
     'Fake trading / investment opportunity with social-proof pressure.',
     'high',
     (r'\bguaranteed returns\b', r'\bassured returns\b',
      r'\bdouble your money\b', r'\brisk-?free profit\b',
      r'\bstock tip\b', r'\btrading group\b', r'\binvest now\b')),
    ('guaranteed_rewards', 'guaranteed_rewards',
     'Prize, lottery or reward that requires a fee or action to claim.',
     'medium',
     (r'\bcongratulations\b.{0,40}\b(won|winner|prize)\b', r'\blottery\b',
      r'\bclaim your (prize|reward|bonus)\b', r'\byou have won\b')),
    ('credential_request', 'credential_request',
     'Asks for passwords, logins or account verification details.',
     'high',
     (r'\bpassword\b', r'\bshare your (password|login)\b',
      r'\bverify your account\b', r'\blogin (details|credentials)\b',
      r'\baccount verification\b')),
    ('otp_request', 'otp_request',
     'Asks for a one-time password or verification code.',
     'high',
     (r'\botp\b', r'\bone-?time password\b', r'\bshare.*otp\b',
      r'\botp.*shar\b', r'\bverification code\b')),
    ('payment_request', 'payment_request',
     'Direct demand to send money, pay or transfer funds.',
     'high',
     (r'\bsend money\b', r'\btransfer (rs|inr|money|funds)\b',
      r'\bpay (now|immediately|urgently)\b', r'\bupi (id|pin|payment)\b',
      r'\badvance fee\b')),
    ('remote_access_request', 'remote_access_request',
     'Asks to install an app or grant remote/screen access.',
     'high',
     (r'\banydesk\b', r'\bteamviewer\b', r'\bremote access\b',
      r'\bscreen shar\w*\b', r'\binstall.*(app|apk)\b',
      r'\benable.*remote\b')),
    ('account_suspension', 'account_suspension',
     'Claims the account will be suspended, blocked or frozen.',
     'medium',
     (r'\baccount.*suspend\w*\b', r'\baccount.*block\w*\b',
      r'\baccount.*freez\w*|frozen\b', r'\bdeactivat\w* your account\b',
      r'\blast warning.*account\b')),
    ('kyc_update_scam', 'kyc_update_scam',
     'Fake KYC / account-update lure with a link or document request.',
     'medium',
     (r'\bkyc\b', r'\bupdate.*(kyc|account)\b', r'\bcomplete.*verification\b',
      r'\bre-?verify\b.{0,20}\bkyc\b', r'\bsubmit.*documents\b')),
)

# Compatibility psychology labels are separate from the more specific intent.
LEGACY_MAP = {'benign': 'none', 'urgency_pressure': 'fear_authority',
              'authority_fear': 'fear_authority', 'digital_arrest': 'fear_authority',
              'investment_scam': 'greed_opportunity', 'kyc_upi_scam': 'none',
              'impersonation': 'fear_authority', 'courier_customs_scam': 'fear_authority',
              'credential_theft': 'none', 'other_fraud': 'greed_opportunity'}


def normalize_text(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    text = re.sub('[\u200b\u200c\u200d\ufeff]', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' urltoken ', text)
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[a-z]+\b', ' emailtoken ', text)
    return re.sub(r'\s+', ' ', text).strip()


def word_tokens(text):
    # Whitespace/punctuation tokenization keeps Devanagari vowel marks with letters.
    return re.findall(r'[^\s.,!?;:()\[\]{}<>/\\"\u201c\u201d]+', text)


def make_intent_pipeline(kind='word_char'):
    if kind == 'baseline':
        # Exact old word-vectorizer configuration for a fair same-data comparison.
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000)
    elif kind == 'word_char':
        vectorizer = FeatureUnion([
            ('word', TfidfVectorizer(preprocessor=normalize_text, tokenizer=word_tokens,
                                    token_pattern=None, lowercase=False,
                                    ngram_range=(1, 2), max_features=10000, sublinear_tf=True)),
            ('char', TfidfVectorizer(preprocessor=normalize_text, lowercase=False,
                                    analyzer='char_wb', ngram_range=(3, 5),
                                    max_features=15000, sublinear_tf=True)),
        ], transformer_weights={'word': 1.0, 'char': 1.0})
    else:
        raise ValueError('Unknown text feature configuration')
    return Pipeline([('tfidf', vectorizer), ('clf', LogisticRegression(
        max_iter=1000, random_state=42, class_weight='balanced'))])

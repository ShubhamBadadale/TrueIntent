"""Assemble real text with explicit source/weak behavioral labels; no synthetic padding."""
import argparse
import email
from email import policy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
from urllib.request import Request, urlopen
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SMS_URL = 'https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip'
EMAIL_URL = 'https://www.kaggle.com/api/v1/datasets/download/rtatman/fraudulent-email-corpus?datasetVersionNumber=1'
SMS_CITATION = 'https://archive.ics.uci.edu/dataset/228/sms+spam+collection'
EMAIL_CITATION = 'https://www.kaggle.com/datasets/rtatman/fraudulent-email-corpus'
LABELS = ('fear_authority', 'greed_opportunity', 'none')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def group_key(text):
    # Collapse simple campaign variations before splitting/deduplication.
    text = re.sub(r'https?://\S+|\b\S+@\S+\b', ' contact ', text.lower())
    text = re.sub(r'\d+', ' number ', text)
    return digest(re.sub(r'\W+', ' ', text).strip().encode())


def download_if_missing(path, url):
    if not path.exists():
        with urlopen(Request(url, headers={'User-Agent': 'TrueIntent-ModuleC/1.0'}), timeout=60) as response:
            payload = response.read()
        if not zipfile.is_zipfile(io.BytesIO(payload)):
            raise ValueError('Source did not return a ZIP; check current access/format')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def email_bodies(payload):
    # Corpus is mbox text. Keep bodies only: sender/recipient/subject are not features.
    chunks = re.split(br'(?m)^From .+\r?\n', payload)
    for number, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        message = email.message_from_bytes(chunk, policy=policy.default)
        parts = message.walk() if message.is_multipart() else [message]
        body = []
        for part in parts:
            if part.get_content_type() == 'text/plain' and part.get_content_disposition() != 'attachment':
                raw = part.get_payload(decode=True)
                if raw:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body.append(raw.decode(charset, errors='replace'))
                    except LookupError:
                        body.append(raw.decode('utf-8', errors='replace'))
        text = re.sub(r'\s+', ' ', ' '.join(body)).strip()
        if text:
            yield number, text


def validate_examples(frame):
    required = ['text', 'signature', 'source_url', 'source_id', 'source_kind', 'label_basis', 'group_id']
    if not set(required).issubset(frame.columns) or frame[required].isna().any().any():
        raise ValueError('Every training example needs text, label, source and grouping metadata')
    if not frame.signature.isin(LABELS).all() or frame.text.str.strip().eq('').any():
        raise ValueError('Invalid signature or empty text')
    if (frame.groupby('group_id').signature.nunique() > 1).any():
        raise ValueError('Conflicting labels for duplicate text')
    return frame.drop_duplicates('group_id').reset_index(drop=True)


def generate_module_c_data(raw_dir=ROOT / 'data/raw', fear_path=ROOT / 'data/module_c_fear_sources.json'):
    raw_dir = Path(raw_dir)
    sms_zip, email_zip = raw_dir / 'module_c_sms.zip', raw_dir / 'module_c_emails.zip'
    download_if_missing(sms_zip, SMS_URL)
    download_if_missing(email_zip, EMAIL_URL)
    rows = []
    with zipfile.ZipFile(sms_zip) as archive:
        sms = archive.read('SMSSpamCollection').decode('utf-8-sig')
    excluded = 0
    for number, line in enumerate(sms.splitlines(), 1):
        label, text = line.split('\t', 1)
        if label not in ('ham', 'spam'):
            raise ValueError('Unknown SMS source label')
        if label == 'ham':
            signature, basis = 'none', 'Source ham label; mapped to none (not proof of all legitimate language)'
        elif re.search(r'\b(prize|winner|won|lottery|awarded|cash reward)\b', text, re.I):
            signature, basis = 'greed_opportunity', 'Weak label: source spam plus prize/winnings lexical selection; not gold behavioral annotation'
        else:
            excluded += 1
            continue
        rows.append(dict(text=text, signature=signature, source_url=SMS_CITATION, source_id=f'sms:{number}',
                         source_kind='real_sms', label_basis=basis, group_id=group_key(text)))
    with zipfile.ZipFile(email_zip) as archive:
        payload = archive.read('fradulent_emails.txt')
    for number, text in email_bodies(payload):
        rows.append(dict(text=text, signature='greed_opportunity', source_url=EMAIL_CITATION,
                         source_id=f'email:{number}', source_kind='real_419_email',
                         label_basis='Weak corpus-level mapping: advance-fee fraud to greed/opportunity; not individually reviewed',
                         group_id=group_key(text)))
    for item in json.loads(Path(fear_path).read_text(encoding='utf-8')):
        rows.append(dict(text=item['text'], signature=item['signature'], source_url=item['source_url'],
                         source_id=item['example_id'], source_kind=item['source_kind'], label_basis=item['label_basis'],
                         group_id=group_key(item['text'])))
    data = validate_examples(pd.DataFrame(rows))
    output = raw_dir / 'signature_examples.csv'
    if output.exists():
        shutil.copy2(output, output.with_name('signature_examples.before-' + digest(output.read_bytes())[:12] + '.csv'))
    data.to_csv(output, index=False, lineterminator='\n')
    metadata = dict(rows=len(data), counts=data.signature.value_counts().to_dict(),
                    source_counts=data.source_kind.value_counts().to_dict(), duplicates_removed=len(rows)-len(data),
                    sms_spam_excluded=excluded, data_sha256=digest(output.read_bytes()),
                    source_hashes={p.name:digest(p.read_bytes()) for p in (sms_zip,email_zip,Path(fear_path))},
                    caveat='Only five fear examples, mostly victim-reported fragments; no invented text. Weak greed labels. Not real-world performance.')
    output.with_suffix('.metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    return data


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    args=parser.parse_args()
    generate_module_c_data(args.raw_dir)

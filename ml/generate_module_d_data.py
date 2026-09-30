"""Synthetic joint scenarios made from real module outputs; labels are an explicit policy."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message

ROOT=Path(__file__).resolve().parents[1]
FEATURES=['module_a_score','module_b_score','module_c_score']
POLICY='combined_label=1 iff at least one PRESENT component has a positive source label; independently paired components are synthetic scenarios, not linked incidents.'


def active_score(result):
    """Do not silently build learned fusion data from rules-only fallback scores."""
    if not result.get('ml_status', '').startswith('active'):
        raise RuntimeError('Module D data requires active trained base classifiers')
    return result['score']


def generate_legacy_module_d_data():
    rng=np.random.default_rng(42)
    a=pd.read_csv(ROOT/'data/raw/module_a_transactions.csv')
    am=joblib.load(ROOT/'ml/models/module_a.pkl')
    if am.get('feature_contract', {}).get('version') == 2:
        raise ValueError('Module A v2 is a source-unit benchmark; existing transaction fusion is disabled.')
    a=a[a.TransactionDT>=am['split']['cutoff_TransactionDT']].copy()
    a['score']=am['model'].predict_proba(a[am['feature_cols']])[:,1]
    a['positive']=a.label.eq('fraud').astype(int)
    a['source_id']=a.TransactionID.astype(str)
    b=pd.read_csv(ROOT/'data/raw/module_b_urls.csv')
    _,b=train_test_split(b,test_size=.2,random_state=42,stratify=b.label)
    b=b.copy(); b['positive']=b.label.eq('phishing').astype(int); b['source_id']=b.index.astype(str)
    c=pd.read_csv(ROOT/'data/raw/signature_examples.csv')
    c['positive']=c.signature.ne('none').astype(int)
    pools={}
    for name,frame in [('a',a),('b',b),('c',c)]:
        for positive in (0,1):
            subset=frame[frame.positive==positive]
            train,test=train_test_split(subset,test_size=.25,random_state=42)
            for split,part in [('train',train),('test',test)]:
                # Limit inference cost. Pool splitting precedes independent pairing.
                part=part.sample(n=min(len(part),160),random_state=42).copy()
                if name=='b': part['score']=[active_score(check_url(u,False)) for u in part.url]
                if name=='c': part['score']=[active_score(analyze_message(t,False)) for t in part.text]
                pools[name,positive,split]=part
    rows=[]
    for split,count in [('train',1600),('test',400)]:
        for i in range(count):
            bits=rng.integers(0,2,3)
            mask=int(rng.integers(1,8))
            row={'scenario_id':f'{split}-{i}','split':split,'presence_mask':mask,'combined_label':0,'label_basis':POLICY}
            for index,name in enumerate('abc'):
                pool=pools[name,int(bits[index]),split]
                component=pool.iloc[int(rng.integers(len(pool)))]
                present=bool(mask & (1<<index))
                row[FEATURES[index]]=float(component.score) if present else 0.0
                row[f'{name}_source_id']=str(component.source_id) if present else 'missing'
                row[f'{name}_source_label']=int(bits[index]) if present else -1
                row['combined_label'] |= int(present and bits[index])
            rows.append(row)
    data=pd.DataFrame(rows)
    path=ROOT/'data/raw/module_d_scenarios.csv'
    data.to_csv(path,index=False,lineterminator='\n')
    metadata={'rows':len(data),'seed':42,'policy':POLICY,'features':FEATURES,
              'missing_policy':'Absent scores encoded as zero; zero score and missing are not distinguished by the three-feature model.',
              'base_scores':'A/B from their held-out source pools; C from fitted real-text model plus rules (in-sample). No base models retrained.',
              'caveat':'All joint pairings and combined labels are synthetic policy data. A telemetry is synthetic; C fear is unvalidated. Not real-world performance.',
              'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'model_sha256':{m:hashlib.sha256((ROOT/f'ml/models/module_{m}.pkl').read_bytes()).hexdigest() for m in 'abc'},
              'counts':data.groupby(['split','combined_label']).size().to_dict()}
    metadata['counts']={str(k):int(v) for k,v in metadata['counts'].items()}
    path.with_suffix('.metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    return data


def generate_module_d_data():
    """Current explicit simulation; never silently reinterpret Module A benchmark outputs."""
    from ml.evaluate_module_d import generate_scenarios
    return generate_scenarios(ROOT / 'data/raw/module_d_interaction_scenarios.csv')


if __name__=='__main__': generate_module_d_data()

"""Interpretable three-score logistic policy, with training-fold coefficient spread."""
import hashlib
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.generate_module_d_data import FEATURES, ROOT


def fit_model(X,y):
    return LogisticRegression(C=1.0,max_iter=1000,random_state=42).fit(X,y)


def train_module_d():
    path=ROOT/'data/raw/module_d_scenarios.csv'
    metadata=json.loads(path.with_suffix('.metadata.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['data_sha256']: raise ValueError('Data hash mismatch')
    data=pd.read_csv(path)
    if not np.isfinite(data[FEATURES]).all().all() or not data[FEATURES].ge(0).all().all() or not data[FEATURES].le(1).all().all(): raise ValueError('Invalid scores')
    if not data.combined_label.isin([0,1]).all(): raise ValueError('Invalid labels')
    train=data[data.split=='train']; test=data[data.split=='test']
    for name in 'abc':
        a=set(train[f'{name}_source_id'].astype(str))-{'missing'}
        b=set(test[f'{name}_source_id'].astype(str))-{'missing'}
        if a & b: raise ValueError('Component source leakage across holdout')
    X=train[FEATURES]; y=train.combined_label
    coefficients=[]
    for tr,va in StratifiedKFold(5,shuffle=True,random_state=42).split(X,y):
        m=fit_model(X.iloc[tr],y.iloc[tr]); coefficients.append(m.coef_[0].tolist()+[float(m.intercept_[0])])
    model=fit_model(X,y)
    report={'sklearn_version':sklearn.__version__,'policy':metadata['policy'],
            'coefficient_names':FEATURES+['intercept'],'coefficients':model.coef_[0].tolist()+[float(model.intercept_[0])],
            'cv_coefficients':coefficients,'cv_min':np.min(coefficients,axis=0).tolist(),'cv_max':np.max(coefficients,axis=0).tolist(),
            'spread_note':'Five training-row folds; descriptive coefficient spread, not a confidence interval. Component reuse within training makes folds dependent.',
            'heldout':classification_report(test.combined_label,model.predict(test[FEATURES]),output_dict=True,zero_division=0),
            'confusion_matrix':confusion_matrix(test.combined_label,model.predict(test[FEATURES])).tolist(),
            'train_rows':len(train),'test_rows':len(test),'provenance':metadata}
    artifact={'model':model,'feature_cols':FEATURES,'baseline':[0.,0.,0.],'report':report,'format_version':1}
    output=ROOT/'ml/models/module_d.pkl'
    output.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(artifact,output)
    output.with_suffix('.metrics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return artifact


if __name__=='__main__': train_module_d()

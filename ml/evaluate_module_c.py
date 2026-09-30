"""Grouped intent comparison with separate real and authored diagnostics."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from threadpoolctl import threadpool_limits
from ml.features_module_c import INTENTS, LEGACY_MAP, make_intent_pipeline, normalize_text
from ml.module_c_dataset import assemble_intents


def report(y, pred, risk=None):
    values = classification_report(y, pred, labels=list(INTENTS), output_dict=True, zero_division=0)
    binary_pred = np.asarray(pred) != 'benign' if risk is None else np.asarray(risk) >= .5
    p, r, f, _ = precision_recall_fscore_support(np.asarray(y) != 'benign', binary_pred,
                                               average='binary', zero_division=0)
    return dict(binary_scam=dict(precision=float(p), recall=float(r), f1=float(f)),
                macro_f1=values['macro avg']['f1-score'],
                supported_label_macro_f1=float(np.mean([values[label]['f1-score'] for label in INTENTS if values[label]['support'] > 0])),
                per_class=values,
                confusion_matrix=confusion_matrix(y, pred, labels=list(INTENTS)).tolist(),
                label_order=list(INTENTS), rows=len(y))


def slices(data, pred, risk=None):
    result = {'all': report(data.intent, pred, risk)}
    for name, mask in [('public_only', data.origin.eq('public')),
                       ('authored_only', data.origin.eq('synthetic')),
                       ('hinglish', data.language.eq('hinglish')),
                       ('hindi', data.language.eq('hi'))]:
        result[name] = report(data.intent[mask], pred[mask], None if risk is None else risk[mask])
    return result


def rule_candidates():
    from ml.predict_module_c import FEAR_AUTHORITY_KEYWORDS, GREED_OPPORTUNITY_KEYWORDS
    return [(phrase, 'digital_arrest' if phrase == 'digital arrest' else 'authority_fear')
            for phrase in FEAR_AUTHORITY_KEYWORDS] + [(phrase, 'investment_scam') for phrase in GREED_OPPORTUNITY_KEYWORDS]


def supported_rules(data):
    """Support comes from training groups, never translated row counts."""
    normalized = data.text.map(normalize_text)
    selected = []
    for phrase, target in rule_candidates():
        hits = data[normalized.str.contains(phrase, regex=False)]
        if hits.empty:
            continue
        group_hits = hits.drop_duplicates(['group_id', 'intent'])
        positives = int(group_hits.intent.eq(target).sum())
        precision = positives / len(group_hits)
        if positives >= 2 and precision >= .9:
            selected.append(dict(phrase=phrase, intent=target, training_groups=len(group_hits),
                                 training_precision=precision))
    return selected


def apply_rules(texts, predictions, rules):
    result = np.asarray(predictions, dtype=object).copy()
    for i, text in enumerate(texts):
        matched = [rule for rule in rules if rule['phrase'] in normalize_text(text)]
        if matched:
            result[i] = matched[0]['intent']
    return result


def train_intents(signature_path='data/raw/signature_examples.csv', model_output_path='ml/models/module_c.pkl'):
    data, provenance = assemble_intents(signature_path)
    group_support = data.groupby('intent').group_id.nunique()
    if set(group_support.index) != set(INTENTS) or group_support.min() < 5:
        raise ValueError('Five independent groups per intent are required for five-fold evaluation')
    split = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42).split(
        data.text, data.intent, data.group_id))
    kinds = ('baseline', 'word_char')
    predictions = {kind: np.empty(len(data), dtype=object) for kind in kinds}
    risk = {kind: np.empty(len(data), dtype=float) for kind in kinds}
    ablations = {kind: np.empty(len(data), dtype=object) for kind in kinds}
    fold_ids = np.full(len(data), -1)
    fold_audit = []
    with threadpool_limits(limits=1):
        for fold, (train, test) in enumerate(split):
            train_data, test_data = data.iloc[train], data.iloc[test]
            if set(train_data.group_id) & set(test_data.group_id):
                raise AssertionError('Leaking related examples')
            if set(train_data.intent) != set(INTENTS):
                raise ValueError('A training fold lacks an intent; collect more independent examples')
            fold_ids[test] = fold
            rules = supported_rules(train_data)
            fold_audit.append(dict(fold=fold, train_rows=len(train), test_rows=len(test),
                                   shared_groups=0, shared_seeds=len(set(train_data.seed_id) & set(test_data.seed_id)),
                                   retained_rules=rules))
            for kind in kinds:
                model = make_intent_pipeline(kind)
                model.fit(train_data.text, train_data.intent, clf__sample_weight=train_data.sample_weight)
                predictions[kind][test] = model.predict(test_data.text)
                risk[kind][test] = 1 - model.predict_proba(test_data.text)[:, list(model.classes_).index('benign')]
                ablations[kind][test] = apply_rules(test_data.text, predictions[kind][test], rules)
            print(f'Intent fold {fold + 1}/5 complete', flush=True)
        results = {kind: slices(data, predictions[kind], risk[kind]) for kind in kinds}
        rule_results = {kind: slices(data, ablations[kind]) for kind in kinds}
        # Real-data protection plus an authored-language diagnostic, not a claim of
        # production improvement. Candidates compared by CV; no independent test remains.
        public_baseline = results['baseline']['public_only']['binary_scam']['f1']
        use_candidate = (results['word_char']['public_only']['binary_scam']['f1'] >= public_baseline - .005
                         and results['word_char']['authored_only']['macro_f1'] > results['baseline']['authored_only']['macro_f1'])
        selected = 'word_char' if use_candidate else 'baseline'
        model = make_intent_pipeline(selected).fit(data.text, data.intent, clf__sample_weight=data.sample_weight)
        # D's existing explanation helper expects three psychology classes in pipeline.
        # Keep a separately fitted compatibility model, using the same text features.
        psychology = make_intent_pipeline(selected).fit(data.text, data.intent.map(LEGACY_MAP),
                                                        clf__sample_weight=data.sample_weight)
    evaluation = dict(provenance=provenance, comparisons=results, rule_override_ablation=rule_results,
                      selected=selected, folds=fold_audit,
                      evaluation='Five grouped OOF folds; lineage and near-duplicate components stay together. All transformations fit on training folds.',
                      selection='Keep candidate only if public binary F1 drops <=0.005 and authored macro-F1 rises; exploratory CV selection, no untouched final test.',
                      rule_policy='No keyword score/signature override. Fold-trained supported rules evaluated separately; retained as evidence only if the ablation improves macro-F1.',
                      binary_metric='Scam if 1-P(benign)>=0.5, matching text score; rule ablation binary uses overridden argmax label instead.',
                      macro_definition='macro_f1 averages all ten declared labels including zero-support classes; supported_label_macro_f1 excludes classes absent from that slice.',
                      limitation='Expanded scam types have synthetic/augmented support only. Hindi/Hinglish results are authored diagnostics, not real-world recall. Public source/style confounding remains.')
    rules_help = (rule_results[selected]['all']['macro_f1'] > results[selected]['all']['macro_f1']
                  and rule_results[selected]['authored_only']['macro_f1'] > results[selected]['authored_only']['macro_f1'])
    rules = supported_rules(data) if rules_help else []
    evaluation['retained_rules'] = rules
    artifact = dict(pipeline=psychology, intent_pipeline=model, labels=list(psychology.classes_),
                    intent_labels=list(INTENTS), mode='intent-v2', metrics=results[selected]['all'],
                    evaluation=evaluation, evidence_rules=rules,
                    coverage_warning=evaluation['limitation'])
    output = Path(model_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        import shutil
        from ml.generate_module_c_data import digest
        shutil.copy2(output, output.with_name(output.stem + '.before-' + digest(output.read_bytes())[:12] + '.pkl'))
    joblib.dump(artifact, output)
    output.with_suffix('.metrics.json').write_text(json.dumps(evaluation, indent=2) + '\n', encoding='utf-8')
    data.assign(fold=fold_ids, baseline_risk=risk['baseline'], candidate_risk=risk['word_char'], baseline_prediction=predictions['baseline'],
                candidate_prediction=predictions['word_char']).to_csv(
                    Path(signature_path).with_name('module_c_intent_oof.csv'), index=False)
    print(json.dumps({kind: {'macro_f1': results[kind]['all']['macro_f1'],
                             'hinglish_macro_f1': results[kind]['hinglish']['macro_f1']} for kind in kinds}, indent=2))
    return artifact

"""Synthetic interaction-policy benchmark. No linked real incident claims."""
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
from threadpoolctl import threadpool_limits
from ml.features_module_d import FEATURES, ABLATIONS, frame_for, rule_score

ROOT = Path(__file__).resolve().parents[1]
POLICY = ('Simulated latent incident label: severe A/B/C evidence OR unusual transaction with '
          '(manipulative message OR active call OR authority pressure) OR phishing link with credential request. '
          'Observed scores are noisy beta samples. This policy and its prevalence are invented, not adjudicated fraud.')


def generate_scenarios(output=None):
    rng = np.random.default_rng(42)
    rows = []
    for split, count in [('train', 300), ('validation', 100), ('test', 200)]:
        for i in range(count):
            a, b, c, call, credential, authority = rng.random(6) < [.35, .30, .35, .4, .30, .25]
            severe = rng.random(3) < .12
            latent = np.asarray([a, b, c]) | severe
            values = [rng.beta(6, 2) if signal else rng.beta(2, 6) for signal in latent]
            # Mimic dependence: message text alone is kept separate from its URL score.
            y = bool(severe.any() or (a and (c or call or authority)) or (b and credential))
            rows.append(dict(scenario_id=f'{split}-{i}', family_id=f'{split}-{i}', split=split,
                module_a_score=values[0], module_b_score=values[1], module_c_score=values[2],
                active_call=bool(call), credential_request=rng.beta(6, 2) if credential else rng.beta(2, 6),
                authority_fear=rng.beta(6, 2) if authority else rng.beta(2, 6),
                combined_label=int(y), legacy_or_label=int(latent.any()),
                provenance='synthetic_policy', label_basis=POLICY))
    data = pd.DataFrame(rows)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False)
    return data


def metrics(y, probabilities):
    predictions = np.asarray(probabilities) >= .5
    return dict(precision=float(precision_score(y, predictions, zero_division=0)),
                recall=float(recall_score(y, predictions, zero_division=0)),
                f1=float(f1_score(y, predictions, zero_division=0)),
                roc_auc=float(roc_auc_score(y, probabilities)),
                average_precision=float(average_precision_score(y, probabilities)),
                confusion_matrix=confusion_matrix(y, predictions, labels=[0, 1]).tolist())


def new_model(kind):
    if kind == 'gradient_boosting':
        return HistGradientBoostingClassifier(max_iter=80, max_leaf_nodes=7, l2_regularization=2., random_state=42)
    return LogisticRegression(C=1., max_iter=1000, random_state=42)


def evaluate(output=ROOT / 'ml/models/module_d.pkl'):
    path = ROOT / 'data/raw/module_d_interaction_scenarios.csv'
    data = generate_scenarios(path)
    parts = {s: data[data.split.eq(s)] for s in ('train', 'validation', 'test')}
    families = [set(part.family_id) for part in parts.values()]
    assert not families[0] & families[1] and not families[0] & families[2] and not families[1] & families[2]
    kinds = ('existing_three_scores', 'simple_rules', 'logistic_interactions', 'gradient_boosting')
    results, validation = {}, {}
    with threadpool_limits(limits=1):
        for ablation, channels in ABLATIONS.items():
            frames = {s: frame_for(part, channels) for s, part in parts.items()}
            results[ablation], validation[ablation] = {}, {}
            for kind in kinds:
                if kind == 'simple_rules':
                    probabilities = {s: frames[s].apply(rule_score, axis=1) for s in ('validation', 'test')}
                else:
                    cols = FEATURES[:3] if kind == 'existing_three_scores' else FEATURES
                    model = new_model(kind).fit(frames['train'][cols], parts['train'].combined_label)
                    probabilities = {s: model.predict_proba(frames[s][cols])[:, 1] for s in ('validation', 'test')}
                results[ablation][kind] = metrics(parts['test'].combined_label, probabilities['test'])
                validation[ablation][kind] = metrics(parts['validation'].combined_label, probabilities['validation'])
        # Use LR for the serving contract: few features and exact coefficient explanations.
        # Evaluate GB but do not automatically deploy a more complex synthetic-policy fit.
        train_frames = [frame_for(parts['train'], channels) for channels in ABLATIONS.values()]
        train_y = np.tile(parts['train'].combined_label.to_numpy(), len(train_frames))
        model = new_model('logistic_interactions').fit(pd.concat(train_frames, ignore_index=True), train_y)
        serving = {name: metrics(parts['test'].combined_label, model.predict_proba(frame_for(parts['test'], channels))[:, 1])
                   for name, channels in ABLATIONS.items()}
    report = dict(scope='Synthetic policy recovery only, not real-world fraud detection', policy=POLICY,
        seed=42, split_counts=data.split.value_counts().to_dict(), features=FEATURES,
        legacy_audit='Original generator label is exactly OR of PRESENT source labels; C scores were in-sample; missing scores were indistinguishable from zero.',
        original_or_agreement=float(data.combined_label.eq(data.legacy_or_label).mean()),
        original_label_caveat='Old source-label OR is distinct from thresholding detector scores. New labels are also hand-designed policy.',
        model_comparison=results, validation=validation, serving_model_test=serving,
        model_choice='Interaction logistic regression, fixed before comparison for simplicity/explanation; GB reported without automatic promotion.',
        ablation='Retrain each approach per subset; same 200 test incidents/labels across subsets. Final serving LR trains all eight availability masks, all siblings within one split.',
        training_families=300, training_masked_rows=2400, shared_family_ids=0,
        data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        availability='Observed zero differs from missing; unknown call differs from false. Latent labels are never recomputed after hiding channels.',
        limitations=['No linked or adjudicated real incidents', 'All signals/calls/tactics and detector errors are simulated',
                    'Beta score distribution and fraud prevalence are assumptions', 'No base-model accuracy improvement or deployment calibration established',
                    'A remains unavailable to the live backend; its ablations are offline experiments only',
                    'Live C text scores are uncertain; probability-derived tactic signals are not verified requests'])
    artifact = dict(format_version=2, model=model, feature_cols=FEATURES, report=report,
                    scope='synthetic_policy_experiment', model_type='logistic_interactions')
    output = Path(output)
    if output.exists():
        import shutil
        digest = hashlib.sha256(output.read_bytes()).hexdigest()[:12]
        shutil.copy2(output, output.with_name(f'{output.stem}.before-{digest}.pkl'))
    joblib.dump(artifact, output)
    output.with_suffix('.metrics.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))
    return artifact


if __name__ == '__main__':
    evaluate()

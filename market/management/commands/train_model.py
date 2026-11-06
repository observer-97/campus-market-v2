import csv
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import joblib
import numpy as np
import sklearn
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from market.models import CATEGORIES

SEED = 20261022
LABELS = [x[0] for x in CATEGORIES]

def normalize(text):
    return re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())

def prepare(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'id', 'title', 'description', 'category', 'source', 'group_id'}
        if not required.issubset(reader.fieldnames or []):
            raise CommandError('CSV 缺少字段：' + ', '.join(sorted(required)))
        raw = list(reader)
    rows, seen, removed = [], {}, []
    ids = set()
    for row in raw:
        row = {k: (row.get(k) or '').strip() for k in required}
        if any(not row[k] for k in required):
            removed.append({'id': row['id'], 'reason': 'missing_field'})
            continue
        if row['category'] not in LABELS: raise CommandError('未知类别：' + row['category'])
        if row['id'] in ids: raise CommandError('重复 id：' + row['id'])
        ids.add(row['id'])
        text = normalize(row['title'] + row['description'])
        if not text:
            removed.append({'id': row['id'], 'reason': 'empty_normalized_text'})
            continue
        if text in seen:
            if seen[text]['category'] != row['category']: raise CommandError('重复文本标注冲突')
            removed.append({'id': row['id'], 'reason': 'exact_duplicate'})
            continue
        seen[text] = row
        row['text'] = row['title'] + ' ' + row['description']
        row['normalized'] = text
        rows.append(row)
    # Connected components merge curator template groups and detected near duplicates BEFORE splitting.
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    pairs = []
    for i in range(len(rows)):
        for j in range(i):
            a, b = rows[i], rows[j]
            sa = {a['normalized'][k:k+2] for k in range(len(a['normalized'])-1)}
            sb = {b['normalized'][k:k+2] for k in range(len(b['normalized'])-1)}
            jac = len(sa & sb) / max(1, len(sa | sb))
            ratio = SequenceMatcher(None, a['normalized'], b['normalized']).ratio()
            same = a['group_id'] == b['group_id']
            if same or jac >= .65 or ratio >= .82:
                parent[root(i)] = root(j)
                pairs.append({'a': a['id'], 'b': b['id'], 'manual_group': same, 'jaccard': round(jac, 4), 'sequence_ratio': round(ratio, 4)})
    for i, row in enumerate(rows): row['leakage_group'] = str(root(i))
    if len(rows) < 40: raise CommandError('有效数据少于 40 条，不能执行当前五折分组划分。')
    return rows, {'raw_count': len(raw), 'clean_count': len(rows), 'removed': removed, 'grouped_pairs': pairs}

class Command(BaseCommand):
    help = '清理数据、识别近重复、分组划分、比较 NB 与 LR，保存模型和真实评估。'
    def add_arguments(self, parser):
        parser.add_argument('--data', default=str(settings.BASE_DIR / 'data' / 'examples.csv'))
    def handle(self, *args, **options):
        path = Path(options['data'])
        rows, audit = prepare(path)
        texts = np.array([r['text'] for r in rows])
        y = np.array([r['category'] for r in rows])
        groups = np.array([r['leakage_group'] for r in rows])
        for label in LABELS:
            if len(set(groups[y == label])) < 5: raise CommandError(f'{label} 至少需要 5 个独立组。')
        folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(texts, y, groups))
        test = folds[0][1]
        valid = folds[1][1]
        train = np.array(sorted(set(range(len(rows))) - set(test) - set(valid)))
        splits = {'train': train, 'validation': valid, 'test': test}
        for name, indices in splits.items():
            if set(y[indices]) != set(LABELS): raise CommandError(f'{name} 未覆盖全部类别，请增加独立组。')
        assert not (set(groups[train]) & set(groups[valid]) or set(groups[train]) & set(groups[test]) or set(groups[valid]) & set(groups[test]))
        folder = settings.BASE_DIR / 'artifacts'
        folder.mkdir(exist_ok=True)
        def evaluate(model, indices):
            predictions = model.predict(texts[indices])
            return {'accuracy': accuracy_score(y[indices], predictions), 'macro_f1': f1_score(y[indices], predictions, labels=LABELS, average='macro', zero_division=0), 'per_class': classification_report(y[indices], predictions, labels=LABELS, output_dict=True, zero_division=0), 'confusion_matrix': confusion_matrix(y[indices], predictions, labels=LABELS).tolist(), 'errors': [{'id': rows[int(i)]['id'], 'text': texts[i], 'actual': str(actual), 'predicted': str(pred)} for i, actual, pred in zip(indices, y[indices], predictions) if actual != pred]}
        models, results = {}, {}
        for name, estimator in [('MultinomialNB', MultinomialNB(alpha=.5)), ('LogisticRegression', LogisticRegression(C=4, max_iter=1500, random_state=SEED))]:
            model = Pipeline([('tfidf', TfidfVectorizer(analyzer='char', ngram_range=(1, 3), min_df=1, sublinear_tf=True)), ('classifier', estimator)])
            model.fit(texts[train], y[train])
            models[name] = model
            results[name] = {'validation': evaluate(model, valid)}
        selected = max(results, key=lambda name: (results[name]['validation']['macro_f1'], results[name]['validation']['accuracy'], name == 'MultinomialNB'))
        # Select only by validation. Final test is evaluated once per fixed candidate after selection.
        for name in models: results[name]['test'] = evaluate(models[name], test)
        artifact = folder / 'category_model.joblib'
        joblib.dump(models[selected], artifact)
        metadata = {'algorithm': selected, 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(), 'dataset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'seed': SEED, 'sklearn_version': sklearn.__version__, 'fitted_on': 'train only; no refit on validation or test', 'features': 'character TF-IDF (1,3), min_df=1, sublinear_tf=True', 'selection': 'validation Macro-F1, then Accuracy; ties prefer NB', 'labels': dict(CATEGORIES)}
        report = {'metadata': metadata, 'audit': audit, 'class_order': LABELS, 'splits': {name: {'count': len(indices), 'distribution': dict(Counter(y[indices])), 'ids': [rows[int(i)]['id'] for i in indices], 'groups': sorted(set(groups[indices]))} for name, indices in splits.items()}, 'results': results, 'limitations': '全部为 AI 辅助逐条编写的课程示例，非真实交易。样本小，测试集不能代表真实泛化；近重复启发式可能漏检，替换数据需人工审查模板组。'}
        (folder / 'model_meta.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        (folder / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        with (folder / 'split_manifest.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'category', 'group_id', 'leakage_group', 'split'])
            for name, indices in splits.items():
                for i in indices: writer.writerow([rows[i]['id'], rows[i]['category'], rows[i]['group_id'], rows[i]['leakage_group'], name])
        lines = ['# 实际运行评估', '', '随机种子：' + str(SEED), '部署模型：' + selected, '', '| 算法 | 验证 Accuracy | 验证 Macro-F1 | 测试 Accuracy | 测试 Macro-F1 |', '|---|---:|---:|---:|---:|']
        for name, result in results.items(): lines.append(f"| {name} | {result['validation']['accuracy']:.4f} | {result['validation']['macro_f1']:.4f} | {result['test']['accuracy']:.4f} | {result['test']['macro_f1']:.4f} |")
        for name, result in results.items():
            for split, metrics in result.items():
                lines += ['', f'## {name} / {split}', '', '```json', json.dumps(metrics, ensure_ascii=False, indent=2), '```']
        lines += ['', report['limitations'], '', '完整清洗审计、每类指标、混淆矩阵（行=真实，列=预测）、全部错误见 evaluation.json；划分见 split_manifest.csv。']
        (folder / 'evaluation.md').write_text('\n'.join(lines), encoding='utf-8')
        self.stdout.write(f'已保存 {len(rows)} 条数据评估；部署模型 {selected}；结果：{folder}')

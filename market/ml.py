"""Only loads this project's generated, hash-checked local artifact. Never trains in requests."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
import joblib
from django.conf import settings

@lru_cache(maxsize=1)
def load_model():
    folder = settings.BASE_DIR / 'artifacts'
    path = folder / 'category_model.joblib'
    metadata = json.loads((folder / 'model_meta.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
        raise ValueError('模型完整性校验失败')
    return joblib.load(path), metadata

def classify(title, description):
    model, meta = load_model()
    text = f'{title.strip()} {description.strip()}'
    if model.named_steps['tfidf'].transform([re.sub(r'\s+', '', text)]).nnz == 0:
        raise ValueError('输入没有模型可识别的文本特征，请补充商品描述。')
    return str(model.predict([text])[0]), meta['algorithm']

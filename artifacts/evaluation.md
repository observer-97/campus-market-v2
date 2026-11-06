# 实际运行评估

随机种子：20261022
部署模型：MultinomialNB

| 算法 | 验证 Accuracy | 验证 Macro-F1 | 测试 Accuracy | 测试 Macro-F1 |
|---|---:|---:|---:|---:|
| MultinomialNB | 0.7619 | 0.7595 | 0.7778 | 0.7328 |
| LogisticRegression | 0.7619 | 0.7595 | 0.7778 | 0.7328 |

## MultinomialNB / validation

```json
{
  "accuracy": 0.7619047619047619,
  "macro_f1": 0.759469696969697,
  "per_class": {
    "study": {
      "precision": 1.0,
      "recall": 0.6,
      "f1-score": 0.75,
      "support": 5.0
    },
    "digital": {
      "precision": 0.7142857142857143,
      "recall": 1.0,
      "f1-score": 0.8333333333333334,
      "support": 5.0
    },
    "sports": {
      "precision": 0.6666666666666666,
      "recall": 0.8,
      "f1-score": 0.7272727272727273,
      "support": 5.0
    },
    "daily": {
      "precision": 0.8,
      "recall": 0.6666666666666666,
      "f1-score": 0.7272727272727273,
      "support": 6.0
    },
    "accuracy": 0.7619047619047619,
    "macro avg": {
      "precision": 0.7952380952380953,
      "recall": 0.7666666666666667,
      "f1-score": 0.759469696969697,
      "support": 21.0
    },
    "weighted avg": {
      "precision": 0.7954648526077098,
      "recall": 0.7619047619047619,
      "f1-score": 0.757936507936508,
      "support": 21.0
    }
  },
  "confusion_matrix": [
    [
      3,
      1,
      0,
      1
    ],
    [
      0,
      5,
      0,
      0
    ],
    [
      0,
      1,
      4,
      0
    ],
    [
      0,
      0,
      2,
      4
    ]
  ],
  "errors": [
    {
      "id": "study-014",
      "text": "函数科学计算器 考试允许的无编程计算器，按键正常，带保护盖。",
      "actual": "study",
      "predicted": "digital"
    },
    {
      "id": "study-023",
      "text": "文具收纳袋 装笔和橡皮的双层笔袋，拉链完好，附几支铅笔。",
      "actual": "study",
      "predicted": "daily"
    },
    {
      "id": "sports-017",
      "text": "运动飞盘 社团活动用标准盘，没有裂口，飞行稳定。",
      "actual": "sports",
      "predicted": "digital"
    },
    {
      "id": "daily-014",
      "text": "行李箱 二十四寸拉杆箱，轮子顺滑，锁扣正常。",
      "actual": "daily",
      "predicted": "sports"
    },
    {
      "id": "daily-023",
      "text": "旅行洗漱包 分隔装牙刷护肤品，防水内衬，拉链完好。",
      "actual": "daily",
      "predicted": "sports"
    }
  ]
}
```

## MultinomialNB / test

```json
{
  "accuracy": 0.7777777777777778,
  "macro_f1": 0.7328282828282829,
  "per_class": {
    "study": {
      "precision": 0.8,
      "recall": 1.0,
      "f1-score": 0.8888888888888888,
      "support": 4.0
    },
    "digital": {
      "precision": 0.8333333333333334,
      "recall": 1.0,
      "f1-score": 0.9090909090909091,
      "support": 5.0
    },
    "sports": {
      "precision": 0.6666666666666666,
      "recall": 1.0,
      "f1-score": 0.8,
      "support": 4.0
    },
    "daily": {
      "precision": 1.0,
      "recall": 0.2,
      "f1-score": 0.3333333333333333,
      "support": 5.0
    },
    "accuracy": 0.7777777777777778,
    "macro avg": {
      "precision": 0.825,
      "recall": 0.8,
      "f1-score": 0.7328282828282829,
      "support": 18.0
    },
    "weighted avg": {
      "precision": 0.8351851851851851,
      "recall": 0.7777777777777778,
      "f1-score": 0.7204264870931536,
      "support": 18.0
    }
  },
  "confusion_matrix": [
    [
      4,
      0,
      0,
      0
    ],
    [
      0,
      5,
      0,
      0
    ],
    [
      0,
      0,
      4,
      0
    ],
    [
      1,
      1,
      2,
      1
    ]
  ],
  "errors": [
    {
      "id": "daily-004",
      "text": "折叠雨伞 晴雨两用伞，伞骨牢固，收起来能放进背包。",
      "actual": "daily",
      "predicted": "sports"
    },
    {
      "id": "daily-005",
      "text": "桌面化妆镜 可折叠双面镜，没有照明功能，宿舍梳妆用。",
      "actual": "daily",
      "predicted": "digital"
    },
    {
      "id": "daily-009",
      "text": "冬季棉被 两公斤棉花被，已晒干装袋，毕业带不走。",
      "actual": "daily",
      "predicted": "study"
    },
    {
      "id": "daily-015",
      "text": "帆布托特包 上课装随身物品，米色厚帆布，已清洗晾干。",
      "actual": "daily",
      "predicted": "sports"
    }
  ]
}
```

## LogisticRegression / validation

```json
{
  "accuracy": 0.7619047619047619,
  "macro_f1": 0.759469696969697,
  "per_class": {
    "study": {
      "precision": 1.0,
      "recall": 0.6,
      "f1-score": 0.75,
      "support": 5.0
    },
    "digital": {
      "precision": 0.7142857142857143,
      "recall": 1.0,
      "f1-score": 0.8333333333333334,
      "support": 5.0
    },
    "sports": {
      "precision": 0.6666666666666666,
      "recall": 0.8,
      "f1-score": 0.7272727272727273,
      "support": 5.0
    },
    "daily": {
      "precision": 0.8,
      "recall": 0.6666666666666666,
      "f1-score": 0.7272727272727273,
      "support": 6.0
    },
    "accuracy": 0.7619047619047619,
    "macro avg": {
      "precision": 0.7952380952380953,
      "recall": 0.7666666666666667,
      "f1-score": 0.759469696969697,
      "support": 21.0
    },
    "weighted avg": {
      "precision": 0.7954648526077098,
      "recall": 0.7619047619047619,
      "f1-score": 0.757936507936508,
      "support": 21.0
    }
  },
  "confusion_matrix": [
    [
      3,
      1,
      0,
      1
    ],
    [
      0,
      5,
      0,
      0
    ],
    [
      0,
      1,
      4,
      0
    ],
    [
      0,
      0,
      2,
      4
    ]
  ],
  "errors": [
    {
      "id": "study-014",
      "text": "函数科学计算器 考试允许的无编程计算器，按键正常，带保护盖。",
      "actual": "study",
      "predicted": "digital"
    },
    {
      "id": "study-023",
      "text": "文具收纳袋 装笔和橡皮的双层笔袋，拉链完好，附几支铅笔。",
      "actual": "study",
      "predicted": "daily"
    },
    {
      "id": "sports-017",
      "text": "运动飞盘 社团活动用标准盘，没有裂口，飞行稳定。",
      "actual": "sports",
      "predicted": "digital"
    },
    {
      "id": "daily-014",
      "text": "行李箱 二十四寸拉杆箱，轮子顺滑，锁扣正常。",
      "actual": "daily",
      "predicted": "sports"
    },
    {
      "id": "daily-023",
      "text": "旅行洗漱包 分隔装牙刷护肤品，防水内衬，拉链完好。",
      "actual": "daily",
      "predicted": "sports"
    }
  ]
}
```

## LogisticRegression / test

```json
{
  "accuracy": 0.7777777777777778,
  "macro_f1": 0.7328282828282829,
  "per_class": {
    "study": {
      "precision": 0.8,
      "recall": 1.0,
      "f1-score": 0.8888888888888888,
      "support": 4.0
    },
    "digital": {
      "precision": 0.8333333333333334,
      "recall": 1.0,
      "f1-score": 0.9090909090909091,
      "support": 5.0
    },
    "sports": {
      "precision": 0.6666666666666666,
      "recall": 1.0,
      "f1-score": 0.8,
      "support": 4.0
    },
    "daily": {
      "precision": 1.0,
      "recall": 0.2,
      "f1-score": 0.3333333333333333,
      "support": 5.0
    },
    "accuracy": 0.7777777777777778,
    "macro avg": {
      "precision": 0.825,
      "recall": 0.8,
      "f1-score": 0.7328282828282829,
      "support": 18.0
    },
    "weighted avg": {
      "precision": 0.8351851851851851,
      "recall": 0.7777777777777778,
      "f1-score": 0.7204264870931536,
      "support": 18.0
    }
  },
  "confusion_matrix": [
    [
      4,
      0,
      0,
      0
    ],
    [
      0,
      5,
      0,
      0
    ],
    [
      0,
      0,
      4,
      0
    ],
    [
      1,
      1,
      2,
      1
    ]
  ],
  "errors": [
    {
      "id": "daily-004",
      "text": "折叠雨伞 晴雨两用伞，伞骨牢固，收起来能放进背包。",
      "actual": "daily",
      "predicted": "sports"
    },
    {
      "id": "daily-005",
      "text": "桌面化妆镜 可折叠双面镜，没有照明功能，宿舍梳妆用。",
      "actual": "daily",
      "predicted": "digital"
    },
    {
      "id": "daily-009",
      "text": "冬季棉被 两公斤棉花被，已晒干装袋，毕业带不走。",
      "actual": "daily",
      "predicted": "study"
    },
    {
      "id": "daily-015",
      "text": "帆布托特包 上课装随身物品，米色厚帆布，已清洗晾干。",
      "actual": "daily",
      "predicted": "sports"
    }
  ]
}
```

全部为 AI 辅助逐条编写的课程示例，非真实交易。样本小，测试集不能代表真实泛化；近重复启发式可能漏检，替换数据需人工审查模板组。

完整清洗审计、每类指标、混淆矩阵（行=真实，列=预测）、全部错误见 evaluation.json；划分见 split_manifest.csv。
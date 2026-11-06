# 青禾集 校园二手交易平台

**在线访问：[https://campus-market-v2-six.vercel.app](https://campus-market-v2-six.vercel.app)**

管理后台：[进入后台](https://campus-market-v2-six.vercel.app/admin/)。普通访客无需登录 Vercel。

面向明故宫、将军路和天目湖三个校区的二手交易网页应用，支持电脑和手机浏览器。使用 Django、PostgreSQL 和 scikit-learn，前端模板、后端接口、管理后台与分类模型部署在同一个 Vercel 项目。

## 功能

- 注册、登录、退出及密码修改，使用 Django 自带认证和会话。
- 发布和编辑商品，上传图片，后端检查商品归属；修改后重新审核。
- 管理员通过或驳回商品并记录理由；卖家查看处理状态。
- 关键词、类别、校区、价格区间、发布时间筛选与排序，分页保留条件。
- 商品详情、收藏、个人主页、在售/售出/下架状态及历史记录。
- 按商品建立私信会话，协商校区和具体交易地点。
- 私信分享见面校区和地点，线下验货、自行付款，卖家标记已售出并保留历史。
- 账号简介、默认联系方式、个人主页公开设置及商品举报处理。
- 根据标题和描述推荐商品类别，用户确认或修改后发布。

平台不提供充值、付款、托管、退款、结算或提现。旧版模拟订单保留为仅双方可见的只读历史，旧操作接口返回 410，旧订单不再锁定商品。默认联系方式保存时不公开；发布商品前会提示公开范围。

## 部署

代码仓库：[observer-97/campus-market-v2](https://github.com/observer-97/campus-market-v2)

在 Vercel 导入本仓库，Root Directory 选择仓库根目录，Framework 选择 Django。Python 固定为 3.12，构建命令为 `python build.py`，Output Directory 使用默认设置。

在 Vercel Storage / Marketplace 关联 PostgreSQL，并配置以下 Production 环境变量：

| 变量 | 用途 |
|---|---|
| DATABASE_URL | 开启 SSL 的 PostgreSQL 连接串 |
| DJANGO_SECRET_KEY | 至少 50 字符的随机密钥 |
| DJANGO_ALLOWED_HOSTS | 正式域名，不带协议或斜杠 |
| DJANGO_CSRF_TRUSTED_ORIGINS | 对应的 HTTPS 来源 |
| CAMPUS_INIT_DEMO | 设为 1 时初始化独立示例数据 |
| CAMPUS_ADMIN_USERNAME | 独立管理员用户名 |
| CAMPUS_ADMIN_PASSWORD | 至少 16 字符的私有随机密码 |

参考 [.env.example](.env.example) 和 [部署指南](docs/VERCEL部署指南.md)。不要把真实密钥或数据库连接串提交到 GitHub。修改管理员密码环境变量不会重置已有账号密码。

构建执行配置检查、模型完整性校验及数据库迁移。初始化不覆盖已有密码、商品、历史记录或审核结果；只自动通过本次新建的示例商品。普通用户发布和编辑仍需审核。

前端 CSS 由 Vercel CDN 提供，Django WSGI 在 Vercel 执行全部业务接口。账号、商品、图片、会话、私信及交易记录存入云端 PostgreSQL，不依赖本机服务或临时 SQLite。图片限 JPEG、PNG、WebP，最大 3 MB、2000 万像素。默认禁止 Preview 共用生产数据库进行迁移。

当前部署状态见 [部署日志](docs/部署日志.md)。部署成功后使用正式 Production HTTPS 网址访问，无需在访问者电脑上运行 Python 或终端。

## 管理与发布验证

- 管理后台：`/admin/`，使用独立管理员账号。
- 完整上线检查：`/admin/deployment-check/`，仅超级管理员可访问。可保存数据库标记并在刷新、换设备及重新部署后核对。
- 公开健康检查：`/api/health/`，检查真实数据库、表结构、模型和云端运行条件，不输出密钥或用户数据。
- GitHub Actions 的 **Django and PostgreSQL checks** 执行 Linux/PostgreSQL 测试及跨进程持久化流程。
- **Verify public Vercel deployment** 可手动输入正式网址，检查匿名首页、CSS、后端和数据库图片。只读报告不能替代完整业务操作与跨设备验证。

普通注册用户无后台权限，用户只能编辑或下架自己的商品。后台工作人员权限需显式分配。未审核商品及图片仅由所有者和有相应权限的管理员访问。

## 示例账号

首次开启初始化后提供以下普通账号；已有账号保留原密码。

| 角色 | 用户名 | 初始密码 |
|---|---|---|
| 浏览与发布 | demo_student | CampusDemo2026! |
| 卖家 | demo_seller | CampusTrade2026! |
| 买家 | demo_buyer | CampusTrade2026! |

示例账号为公开共享账号，不应录入真实隐私。管理员账号和密码由部署者单独设置，不公开。

## 商品智能分类

输入标题与描述，使用中文字符级 TF-IDF（1～3 gram）提取特征，对比 MultinomialNB 与 LogisticRegression。按验证 Macro-F1、再按 Accuracy 选型，平局选择 NB；当前部署 MultinomialNB。

数据为 97 条 AI 辅助逐条编写的标注示例，不是真实用户交易数据。训练前清理缺失、重复文本，按同模板和检测出的近重复分组，固定随机种子 20261022，划分为训练 58、验证 21、测试 18 条。TF-IDF 仅拟合训练集。

| 算法 | 验证 Accuracy | 验证 Macro-F1 | 测试 Accuracy | 测试 Macro-F1 |
|---|---:|---:|---:|---:|
| MultinomialNB | 0.7619 | 0.7595 | 0.7778 | 0.7328 |
| LogisticRegression | 0.7619 | 0.7595 | 0.7778 | 0.7328 |

小规模编写数据和 18 条测试样本不能代表真实场景效果。数据来源、格式及分组方法见 [数据说明](data/README.md)，完整指标、混淆矩阵和错误案例见 [评估报告](artifacts/evaluation.md)。

模型由独立训练命令生成，网页请求只加载并校验本项目生成的模型，不重新训练，不调用大模型 API。模型缺失或输入无效时返回明确错误，仍可手动选择类别。只使用本项目生成的 joblib 文件。

## 本地开发与验证

```text
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py train_model
python manage.py init_demo
python manage.py test market
python manage.py runserver 127.0.0.1:8001
```

本地默认使用 SQLite；Vercel 环境必须使用 PostgreSQL。Windows 也可通过 `run.ps1` 调用已配置的 Python 3.12。本地开发服务器不用于公网部署。

## 当前版本与展示材料

当前为线下交易版 v3：浏览商品 → 私信约时间地点 → 线下验货并自行付款 → 卖家标记已售出。

新增验证记录见 [新版浏览器验收](docs/offline-v3-browser-verification.json)；旧版模拟支付验证仅作为历史记录。

最新图文说明书与设计思路由 `tools/build_offline_documents.py` 和 `tools/render_offline_documents.cjs` 生成到 `output/pdf/`；后者需本机 Playwright/Chrome 与 PDF.js 渲染环境，属于材料生成工具，不是网站运行依赖。提交包保存于部署者本机 `交付包/线下交易版v3/`。旧版 `课程展示材料/` 和 v2 压缩包对应早期功能，不能替代本版材料。

# GitHub 与 Vercel 部署指南

## 架构与仓库

仓库为 https://github.com/observer-97/campus-market-v2 。Django 模板、CSS、WSGI 后端、管理后台和模型接口在同一 Vercel 项目中部署；账号、商品、图片、会话、私信和模拟交易记录存入关联的 PostgreSQL。

## 创建生产部署

1. 在 Vercel 导入上述 GitHub 仓库，Root Directory 为仓库根目录，Framework 选择 Django。
2. Python 使用项目 .python-version 指定的 3.12；Build Command 为 python build.py；Output Directory 不填写。
3. 关联 PostgreSQL 服务并获取 DATABASE_URL，开启 SSL，仅授予 Production 环境。
4. 配置 README 和 .env.example 列出的 Production 环境变量。密钥和管理员密码用随机值，不使用占位文字。
5. 发布 main 分支到 Production。构建检查配置和本地模型、执行迁移；CAMPUS_INIT_DEMO=1 时初始化独立示例数据。
6. 确认 Production 网址可匿名访问。普通访客打开首页不应被要求登录 Vercel。

Vercel 会自动收集 staticfiles 并通过 CDN 提供 CSS、管理后台脚本及图标。不要部署为纯静态站点，也不要配置依赖本机地址的后端接口。

## 环境变量

- DATABASE_URL：服务提供方生成的 PostgreSQL 连接串。
- DJANGO_SECRET_KEY：至少 50 字符的随机字符串。
- DJANGO_ALLOWED_HOSTS：实际域名，不带 https:// 或路径；多域名用英文逗号。
- DJANGO_CSRF_TRUSTED_ORIGINS：同一域名带 https://。
- CAMPUS_INIT_DEMO：1 表示启用幂等初始化，完成后可改为 0。
- CAMPUS_ADMIN_USERNAME：独立管理员用户名，不能与公开示例账号重名。
- CAMPUS_ADMIN_PASSWORD：至少 16 字符的私有随机密码。

VERCEL、VERCEL_ENV、VERCEL_URL 和 VERCEL_PROJECT_PRODUCTION_URL 由平台提供。不要手动伪造。DEBUG 在 Vercel 强制关闭。默认拒绝 Preview 对生产数据库执行迁移，开发预览应使用隔离数据库和独立发布策略。

不要上传真实 .env、数据库或个人图片。修改环境变量不会重置已有管理员密码；请保存最初设置的密码，登录后台后可正常修改。

## 发布后验证

1. 匿名打开正式 HTTPS 首页，检查 CSS、图片、搜索和校区筛选。
2. 注册独立账号，发布带图片的商品并调用智能分类；管理员审核后另一账号可查看、收藏和私聊。
3. 双方协商具体地点，完成模拟付款、确认收货或退款，核对记录。
4. 管理员访问 /admin/deployment-check/，检查 Vercel Production、PostgreSQL、SSL、图片存储和真实模型，保存数据库标记。
5. 关闭本机项目服务，用另一设备和网络访问正式网址，核对相同商品、图片、消息及标记。
6. 重新部署后再次核对原数据保留。不要重建或删除数据库来执行此检查。

所有付款为模拟记录，不代表真实资金托管。

## GitHub 检查

Django and PostgreSQL checks 在 Linux/PostgreSQL 上运行测试，并以两个独立进程验证业务数据及会话保留。

Verify public Vercel deployment 可在 Actions 中手动触发，输入正式 https://项目名.vercel.app 根地址。它只执行匿名首页、CSS、后端和图片等只读检查，不需要管理员或数据库密码。报告不能代替完整业务操作和跨设备验证。

## 故障排查

- 缺少 DATABASE_URL 或随机密钥：补齐 Production 变量后重新部署。
- 400：检查实际域名是否在 ALLOWED_HOSTS，变量中不应包含协议或斜杠。
- 403 CSRF：检查 HTTPS 来源、实际域名及旧 Cookie。
- 无商品：确认初始化成功，或在后台审核通过新发布的商品。
- 图片过大：压缩到 3 MB 以内后重新上传。
- 模型不可用：上传 artifacts/category_model.joblib 与 model_meta.json，保持固定依赖版本；不加载外部模型文件。
- security.W021：项目没有申请 HSTS preload，保留该建议；HTTPS 跳转及 Secure Cookie 已启用。

## 参考

- https://vercel.com/docs/frameworks/full-stack/django
- https://vercel.com/docs/functions/runtimes/python
- https://docs.djangoproject.com/en/5.2/ref/files/storage/

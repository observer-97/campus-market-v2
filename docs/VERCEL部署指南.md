# 青禾集 GitHub 和 Vercel 图形界面部署指南

更新日期：2026-11-06。此包是部署适配完成的源码，不是已经发布的网站。以下操作在 GitHub、Vercel 网页内完成，不要求你或老师使用终端。云数据库和平台可能有额度、地区或计费条件，选择时以账号页面为准；不要在未核实额度时开通付费方案。

## 必须满足的最新要求

本项目采用 Django 服务端模板：前端页面和 Django 后端、审核后台、站内私信及分类模型接口在同一个 Vercel Project 中运行，数据库及图片使用云端 PostgreSQL。完整部署不等于必须拆成两个仓库，更不能只把 HTML/CSS 当静态网站上传。本包没有依赖本机 app.py、localhost API、内网穿透或本机常驻服务。

本压缩包尚未替你创建仓库、数据库或 Vercel 网站；缺少这些账号资源和实际公网验收时，不能保证已经可访问。老师最新通知截止 11 月 8 日，随后按分组信息中的正式网址验收。完成下面所有步骤再填写网址。

## 1 解压并上传 GitHub

1. 解压 `campus-market-vercel-fullstack-v2.zip`，打开里面的 `campus-market` 文件夹。
2. GitHub 登录后点击右上角 + → New repository。名称可填 `campus-market`；Public/Private 由你决定，Vercel 要有读取权限。不要另外初始化 README。
3. 点击上传现有文件（uploading an existing file / Add file → Upload files），把 `campus-market` **里面的文件及文件夹**拖入，不能只上传 zip，也不要让 manage.py 再套一层目录。
4. 如上传界面提示超过单次数量限制，分批提交；先传 config、market、templates、static、artifacts、data 及根目录配置，再补 docs 和 tools。隐藏文件 `.python-version`、`.gitignore`、`.vercelignore`、`.env.example` 也要上传。点 Commit changes。
5. 仓库根目录应直接看到 `manage.py`、`requirements.txt`、`vercel.json`、`build.py` 和 config 文件夹。压缩包内没有本机数据库、图片、真实密码或 Windows 依赖目录。
6. `.github/workflows/test.yml` 是可选的 Linux + PostgreSQL 检查配置。GitHub 网页若拒绝拖入隐藏 `.github` 目录，可用 Add file → Create new file，输入完整路径 `.github/workflows/test.yml` 后粘贴文件内容；也可稍后再加，Vercel 运行不依赖此文件。上传后才能查看 Actions 实际结果，本地未运行该云端任务。

## 2 导入 Vercel 项目

1. 登录 Vercel，Add New → Project → Import Git Repository，选择刚才的 GitHub 仓库。
2. Root Directory 保持仓库根目录（manage.py 所在目录）。Framework Preset 选 **Django**；Python 由 `.python-version` 固定为 3.12。构建命令为 `python build.py`；不要填 `runserver`，不要手动设置 Output Directory。
3. 可以先创建项目，再配置数据库和环境变量后重新部署。缺少 DATABASE_URL 时首次构建会明确失败，这是防止误用临时数据库的保护；补齐后 Redeploy。
4. Vercel 原生 Django 支持会自动收集 staticfiles 并通过 CDN 提供，不需要自己上传静态目录。

## 3 创建持久化 PostgreSQL

1. 在 Vercel 项目 Storage / Marketplace 中选择 PostgreSQL 提供方，例如 Neon；按界面创建数据库并 Connect Project。这里只需一个数据库，商品图片也存在其中，适合小规模课堂演示。
2. 选择 **Production** 环境，不勾选共享同一个数据库的 Preview。生产分支用 main。
3. 检查 Environment Variables 中存在 `DATABASE_URL`，值是提供方给出的 `postgresql://...` 连接串，包含 SSL 配置。若提供方只创建了其他名称的变量，在控制台复制它到名为 DATABASE_URL 的变量。
4. 如提供方同时给出 pooled/direct 地址，使用支持 Django 普通事务的 PostgreSQL pooled 地址；本项目关闭长连接和服务端游标。
5. 不要上传 SQLite 到仓库，不要把 SQLite 复制到 /tmp 作为云数据库。后者会丢失账号、私信、订单及图片。
6. 免费数据库可能冷启动或休眠。展示前访问一次并完整排练；不能承诺任何免费服务永久在线或零费用。

## 4 设置 Production 环境变量

进入 Project → Settings → Environment Variables，以下均仅选择 Production：

| 名称 | 填写内容 |
|---|---|
| DATABASE_URL | 数据库提供方生成的 PostgreSQL 连接串，保持私密 |
| DJANGO_SECRET_KEY | 用密码管理器生成至少 50 字符、建议 64 字符的随机字符串，不用示例文字 |
| DJANGO_ALLOWED_HOSTS | 实际项目域名，例如 campus-market-yourname.vercel.app；不带 https:// 或斜杠，多域名英文逗号分隔 |
| DJANGO_CSRF_TRUSTED_ORIGINS | 同一个域名带 https://，如 https://campus-market-yourname.vercel.app |
| CAMPUS_INIT_DEMO | 1 |
| CAMPUS_ADMIN_USERNAME | 自己选的管理员名，如 course_admin，不得与 demo_* 账号重名 |
| CAMPUS_ADMIN_PASSWORD | 密码管理器生成至少 16 字符的私有随机密码，不与演示账号共用 |

项目自动允许 VERCEL_URL 与 VERCEL_PROJECT_PRODUCTION_URL 提供的实际域名。自定义域名仍须在上述两项中添加。VERCEL、VERCEL_ENV 由平台提供，不要手动伪造。Vercel 上 DEBUG 强制关闭。

管理员密码不会在构建日志中输出。请自己保存；重复部署不会覆盖已有管理员密码，改环境变量也不会重置它。已登录时可在后台修改密码；忘记密码需通过有权限的数据库维护环境运行 Django changepassword，不提供公开网页重置后门。

## 5 重新部署并验收

1. Deployments → 最新部署 → Redeploy（Production）。构建会检查配置及模型完整性、执行迁移；开启初始化时创建三个普通演示账号、一个独立管理员、9 件新演示商品。
2. 只有初始化本次新建的、明确标识的演示商品会自动通过审核。已有用户商品、驳回结果、密码、订单不会被覆盖。新增用户发布继续等待管理员审核。
3. 打开正式 HTTPS 地址。若看到 Vercel 登录/保护页，在项目 Deployment Protection 中检查 **Production** 访问保护，让老师无需登录 Vercel 即可访问。不要只把受保护的 Preview 链接交给老师。
4. 管理后台在同一网址后加 `/admin/`。管理员使用步骤 4 自行设置的账号密码，不使用本地旧管理员。
5. 全部核对后填写正式网址、GitHub 地址及成员信息，再提交材料。可将 CAMPUS_INIT_DEMO 改为 0 并重新部署，后续仅迁移，不补建被删除的演示商品。

公开演示账号（首次创建时）：demo_student / CampusDemo2026!；demo_seller、demo_buyer / CampusTrade2026!。这些普通账号没有管理权限。任何访客都可能使用它们，不要录入真实身份、联系信息或私密聊天；老师需要独立数据时可自行注册。

### 必做的公网操作检查

- 手机流量或另一台电脑直接打开正式网址，首页、图片、CSS 均正常；无需登录 Vercel。
- 注册、登录、退出；用账号设置保存校区。
- 关键词 + 校区 + 价格筛选及排序，分页后条件保留。
- 填写标题“羽毛球拍”、描述“体育课训练使用，附拍套，线床完整”，点击智能分类，再采用或修改建议。模型可能误判，不伪造结果。
- 提交新商品（可带小于 3 MB 的 JPEG/PNG/WebP），在管理后台通过；其他用户查看、收藏、私信；卖家编辑后重新待审。
- 两个账号演示交易意愿、协商地点、模拟付款和确认收货。全部是模拟资金。
- 重复刷新或再次部署，确认账号、商品、上传图片和历史仍在。

## 6 网页内完整上线验收

管理员登录后，顶部点击“完整上线验收”，或打开正式网址的 `/admin/deployment-check/`。

- 必须看到 Vercel Production、PostgreSQL、数据库加密连接、数据库表、图片存储、真实模型、前端模板及 CSS 检查通过。本机运行会明确显示尚未满足云端条件，不会假装通过。
- 点击“保存新的验收标记”，记下标记和时间，刷新确认仍在。标记保存在云数据库的管理日志中。
- **关掉本机全部终端和项目服务**，用手机流量或另一台电脑打开正式首页；普通用户不需要 Vercel 账号。再用管理员登录验收页核对同一标记。
- 创建一个新注册账号，发布带图片的商品，点击模型分类，提交后管理员审核。另一账号浏览、按校区筛选、收藏和私聊，约定地点；完成模拟付款与确认收货。
- 在 Vercel 点 Redeploy，等待成功后用另一设备刷新：原账号、商品图片、收藏、消息、交易记录和验收标记应仍在。不要删除 PostgreSQL 或重建数据库。
- 只有完成这些操作，才把完整的 `https://项目名.vercel.app` Production 地址填入分组信息。GitHub 链接、localhost、预览截图或“先启动 app.py”说明都不能替代正式网址。

## 7 在 GitHub 网页执行公开访问检查

仓库上传 `.github/workflows/verify-live.yml` 后，进入 Actions → Verify public Vercel deployment → Run workflow，输入正式 https://项目名.vercel.app 根地址。此检查无需数据库密码或管理员密码。

检查会从 GitHub 的云端访问你的匿名首页、动态后端健康接口、CSS 和数据库商品图片；启用 Vercel 登录保护、后端没部署、数据库/模型不可用时会失败。通过后可下载 public-readiness-report。报告会明确标注：只读检查不能代替注册发布、跨设备和重新部署验收。

如果上传时没有显示 `.github`，在 GitHub 用 Add file → Create new file 按完整路径创建两个 workflow 文件。另一个 Django and PostgreSQL checks 会在 Linux/PostgreSQL 上执行完整测试，并通过两个独立 Python 进程写入、读取注册、审核、图片、会话、收藏、私信和模拟订单数据。

## 常见问题

- 缺少 DATABASE_URL / SECRET_KEY：补齐 Production 环境变量，再 Redeploy。
- 400 Bad Request：域名配置需使用浏览器正在访问的真实主机名；不能填写 https:// 到 ALLOWED_HOSTS。
- 403 CSRF：检查 TRUSTED_ORIGINS 带 https:// 且域名一致，清理旧登录 Cookie 后重试。
- 首页无商品：确认 CAMPUS_INIT_DEMO=1 且初始化构建成功，或者在后台通过用户发布商品。
- 图片请求太大：本项目限 3 MB，以留出 Vercel 请求体限制所需空间，压缩图片后重传。
- 模型不可用：artifacts/category_model.joblib 与 model_meta.json 必须一起上传，依赖版本不要随意修改。不要使用来源不明的 joblib；网页不会重新训练。
- Preview 构建提示禁用：本方案有意拒绝 Preview 向生产数据库迁移。请 main 分支部署 Production；要开发预览需另建隔离数据库后调整构建策略。
- security.W021：项目没有申请 HSTS preload 预加载名单，此建议会保留显示；HTTPS 跳转与 Secure Cookie 已启用，构建仅把 ERROR 作为失败。不要为消除提示随意把他人主域名提交浏览器预加载名单。

## 官方参考

- Vercel Django：https://vercel.com/docs/frameworks/full-stack/django
- Vercel Python：https://vercel.com/docs/functions/runtimes/python
- Django 文件存储：https://docs.djangoproject.com/en/5.2/ref/files/storage/
- Django 5.2.19 安全更新：https://www.djangoproject.com/weblog/2026/nov/03/security-releases/

代码已做本地回归与配置验证；尚未连接你的真实云数据库、执行 Vercel 构建或取得公网地址。务必完成步骤 5 后再告诉老师“已部署”。

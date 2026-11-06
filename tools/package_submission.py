"""Rebuild sanitized source and teacher-document archives with an explicit allowlist."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '交付包' / '完整上线版v2'
ROOT_FILES = ['README.md', 'requirements.txt', 'requirement.txt', 'manage.py', 'run.ps1', 'setup.ps1',
              'vercel.json', 'build.py', '.python-version', '.gitignore', '.vercelignore', '.env.example']
SOURCE_DIRS = ['config', 'market', 'templates', 'static', 'artifacts', 'data', 'tools', '.github']
DOC_FILES = [str(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / 'docs').glob('*.md'))]
DOC_FILES += ['docs/vercel-ml-check.json', 'docs/vercel-regression-output.txt', 'docs/fullstack-v2-test-output.txt', 'docs/AI用量快照.json', 'docs/fullstack-vercel-schema.json']
DOC_FILES += [str(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / 'docs/screenshots').glob('*.png'))]
DOC_FILES += [str(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / '课程展示材料').iterdir()) if p.is_file() and p.suffix in {'.md', '.docx', '.pdf'}]


def source_files():
    for name in ROOT_FILES + DOC_FILES:
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        yield path
    for folder in SOURCE_DIRS:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.log'}:
                yield path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    with ZipFile(OUT / 'campus-market-vercel-fullstack-v2.zip', 'w', ZIP_DEFLATED) as archive:
        for path in source_files():
            rel = path.relative_to(ROOT).as_posix()
            archive.write(path, 'campus-market/' + rel)
            manifest.append({'path': rel, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    with ZipFile(OUT / '待填写姓名和分工比例_课程设计文档_v2.zip', 'w', ZIP_DEFLATED) as archive:
        for prefix in ['02 ', '03 ']:
            for path in sorted((ROOT / '课程展示材料').glob(prefix + '*')):
                if path.suffix in {'.pdf', '.docx'}:
                    archive.write(path, path.name)
        path = ROOT / '课程展示材料/提交信息待填写.md'
        archive.write(path, path.name)
    (OUT / '源码文件清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / '先读我.txt').write_text(
        '1. 只使用本目录的 v2 部署包。解压，上传 campus-market 文件夹内全部内容到 GitHub，Vercel 选择 Django 并配置 PostgreSQL。\n'
        '2. 图形界面步骤见 解压后 docs/VERCEL部署指南.md；需要配置 PostgreSQL 和环境变量，不能只上传 zip 就直接运行。\n'
        '3. 待填写姓名和分工比例_课程设计文档_v2.zip：两份文档的 PDF 与可编辑 DOCX，另附提交字段。先填写并按真实姓名和比例重命名，再提交老师。\n'
        '4. 前端页面、Django 后端、分类模型均由 Vercel 运行；数据和图片存云端 PostgreSQL。不需要本机 app.py、终端常驻或内网穿透。\n'
        '5. 本包不等于已上线，尚无真实网址。上线后必须关闭本机服务，用其他设备访问并检查刷新、重新部署后数据保留；后台有完整上线验收入口。\n'
        '6. 老师截止 11 月 8 日，验收用正式 Production 网址；在分组信息中填写网址，检查老师无需登录 Vercel。\n', encoding='utf-8')
    for path in OUT.glob('*.zip'):
        with ZipFile(path) as archive:
            assert archive.testzip() is None
            print(path.name, len(archive.namelist()), 'files', path.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()

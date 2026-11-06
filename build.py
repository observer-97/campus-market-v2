"""Vercel build only. Never imported by an HTTP request."""
import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    if os.environ.get('VERCEL') != '1':
        raise SystemExit('build.py 用于 Vercel 云端构建；请从 Vercel 导入完整项目。')
    if os.environ.get('VERCEL_ENV') != 'production':
        raise SystemExit('当前项目默认不向 Preview 部署写入数据库；请部署 main 分支到 Production。')
    def command(*args):
        subprocess.run([sys.executable, 'manage.py', *args], cwd=root, check=True)
    command('check', '--deploy', '--fail-level', 'ERROR')
    # Fail if artifacts are missing/corrupt, rather than training during requests.
    command('shell', '-c', 'from market.ml import load_model; load_model(); print("Local trained model verified")')
    command('migrate', '--noinput')
    if os.environ.get('CAMPUS_INIT_DEMO') == '1':
        command('init_cloud_demo')
    # Native Vercel Django support runs collectstatic automatically.


if __name__ == '__main__':
    main()

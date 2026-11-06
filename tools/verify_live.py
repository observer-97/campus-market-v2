"""Read-only checks against a public Vercel URL, runnable from GitHub Actions."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


def verify(url, get=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.vercel.app') or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment or parsed.path not in ['', '/']:
        raise ValueError('请填写正式 https://项目名.vercel.app 根地址，不接受本机地址、登录页或其他路径。')
    base = url.rstrip('/')
    def fetch(path):
        target = urllib.parse.urljoin(base + '/', path)
        if urllib.parse.urlsplit(target).hostname != parsed.hostname:
            raise ValueError('静态资源或图片没有使用本站地址。')
        if get is not None:
            return get(target)
        request = urllib.request.Request(target, headers={'User-Agent': 'CampusMarket-Readiness/2', 'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=45) as response:
            if urllib.parse.urlsplit(response.url).hostname != parsed.hostname:
                raise ValueError('网址跳转到其他站点，可能启用了 Vercel 登录保护。')
            return response.status, response.headers.get('Content-Type', ''), response.read()
    checks = []
    status, mime, body = fetch('/')
    home = body.decode('utf-8')
    if status != 200 or '青禾集' not in home or 'text/html' not in mime:
        raise ValueError('首页不是可直接访问的完整应用，或启用了部署保护。')
    if re.search(r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?=[:/])', home):
        raise ValueError('首页仍引用本机地址。')
    checks.append('匿名访问动态首页')
    status, mime, body = fetch('/api/health/')
    health = json.loads(body)
    if status != 200 or not health.get('cloud_ready') or not health.get('checks', {}).get('vercel_production'):
        raise ValueError('云端后端、数据库、SSL 或模型检查未通过。')
    checks.append('Vercel 后端、PostgreSQL、图片存储与真实模型')
    match = re.search(r'href=["\']([^"\']*?/static/app\.css)["\']', home)
    if not match:
        raise ValueError('未找到前端 CSS。')
    status, mime, body = fetch(match.group(1))
    if status != 200 or 'text/css' not in mime or b'body' not in body:
        raise ValueError('前端 CSS 没有正确部署。')
    checks.append('浏览器可获取前端 CSS')
    match = re.search(r'src=["\']([^"\']*?/uploads/[^"\']+)["\']', home)
    if not match:
        raise ValueError('首页无可验证的已上架图片，请先初始化并审核演示商品。')
    status, mime, body = fetch(match.group(1))
    if status != 200 or not mime.startswith('image/') or not body:
        raise ValueError('云端商品图片不可访问。')
    checks.append('云端数据库图片可读取')
    return {'url': base, 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'read_only_checks': checks,
            'release': health.get('release'), 'passed': True,
            'remaining_manual_checks': ['新账号注册登录与发布', '管理员审核与收藏私信', '模拟交易', '关闭本机并换设备访问', '重新部署后数据与验收标记仍在'],
            'scope': '本报告只证明上述只读检查成功，不代表完整业务、跨设备及重部署验收全部通过。'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', default='live-readiness.json')
    args = parser.parse_args()
    try:
        result = verify(args.url)
    except Exception as exc:
        raise SystemExit('公网检查失败：' + str(exc)) from exc
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Switch this repository's Pages source using the workflow's short-lived token."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = 'https://api.github.com/repos/WayneLiang94/wayneliang94.github.io/pages'

def main():
    token = os.environ.get('PAGES_SETTINGS_TOKEN')
    if not token:
        raise SystemExit('Pages settings token is only provided inside GitHub Actions.')
    headers = {'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json', 'User-Agent': 'WayneLAB-Pages-setup'}
    def request(method='GET', payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        with urlopen(Request(URL, data=data, headers=headers, method=method), timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    try:
        existing = request()
        if existing.get('build_type') != 'workflow':
            # An additive field update: retain custom domain, HTTPS, and other site settings.
            request('PUT', {'build_type': 'workflow'})
        current = request()
        if current.get('build_type') != 'workflow':
            raise ValueError('Pages source change was not confirmed.')
    except (HTTPError, URLError, ValueError) as error:
        code = f' HTTP {error.code}.' if isinstance(error, HTTPError) else ''
        print('::warning::Could not automatically confirm the Pages source.'+code+' Open Settings > Pages and select GitHub Actions as Source before publishing from the editor.')
        raise SystemExit(1)
    print('Confirmed: Pages Source is GitHub Actions. Legacy branch publishing is disabled.')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write('### Publishing enabled\n\nPages Source is **GitHub Actions**. Editor commits will build and publish through this workflow.\n')

if __name__ == '__main__':
    main()

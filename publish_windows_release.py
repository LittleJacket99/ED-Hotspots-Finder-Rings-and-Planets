"""Upgrade the source-only v7.11 release after real Windows build checks pass."""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAG = 'v7.11'
SOURCE_ONLY_TAG_SHA = 'b0896452ee288e9f3e1cb7d02cf6a96f89c7e168'
EXE_NAME = 'ED Hotspots & Landables Finder.exe'
ZIP_NAME = 'ED-Hotspots-Landables-Finder-v7.11-Windows.zip'


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    commit = os.environ['GITHUB_SHA']
    if repo != 'LittleJacket99/ED-Hotspots-Landables-Finder':
        raise RuntimeError('This publication script is for the official repository')
    files = [ROOT / 'dist' / EXE_NAME, ROOT / 'release' / ZIP_NAME,
             ROOT / 'release' / 'SHA256.txt']
    if any(not path.is_file() or not path.stat().st_size for path in files):
        raise RuntimeError('Windows release assets are missing or empty')
    checksums = dict(line.split('  ', 1)[::-1] for line in files[2].read_text().splitlines() if line)
    for path in files[:2]:
        if checksums.get(path.name, '').upper() != digest(path):
            raise RuntimeError('Checksum mismatch before upload: ' + path.name)

    ref = json.loads(gh('api', f'repos/{repo}/git/ref/tags/{TAG}'))
    if ref['object']['sha'] not in (SOURCE_ONLY_TAG_SHA, commit):
        raise RuntimeError('Tag changed since the source-only release; inspect it before replacing')

    # Keep an incomplete upload out of the public release listing. A failed run
    # leaves a draft that can be retried from the same commit.
    gh('release', 'edit', TAG, '--repo', repo, '--draft=true')
    release = json.loads(gh('api', f'repos/{repo}/releases/tags/{TAG}'))
    for asset in release['assets']:
        if asset['name'] in {path.name for path in files} or asset.get('label') in {path.name for path in files}:
            gh('api', '--method', 'DELETE', f"repos/{repo}/releases/assets/{asset['id']}")
    gh('release', 'upload', TAG, '--repo', repo,
       *[str(path) + '#' + path.name for path in files[:2]])
    release = json.loads(gh('api', f'repos/{repo}/releases/tags/{TAG}'))
    actual_names = {}
    for path in files[:2]:
        candidates = [asset for asset in release['assets']
                      if asset['name'] == path.name or asset.get('label') == path.name]
        if len(candidates) != 1 or candidates[0]['state'] != 'uploaded':
            raise RuntimeError('Could not identify uploaded asset: ' + path.name)
        actual_names[path.name] = candidates[0]['name']

    # GitHub may normalize spaces and special characters in download filenames.
    # Keep the exact application filename inside the ZIP and make the external
    # checksum file match the actual standalone download names returned by GitHub.
    files[2].write_text(''.join(digest(path) + '  ' + actual_names[path.name] + '\n'
                              for path in files[:2]), encoding='ascii')
    gh('release', 'upload', TAG, '--repo', repo, str(files[2]))
    actual_names[files[2].name] = files[2].name

    # Download the actual assets again and compare bytes before publishing.
    with tempfile.TemporaryDirectory(prefix='hf-release-check-') as temp:
        for path in files:
            name = actual_names[path.name]
            gh('release', 'download', TAG, '--repo', repo, '--pattern', name, '--dir', temp)
            downloaded = Path(temp) / name
            if not downloaded.is_file() or digest(downloaded) != digest(path):
                raise RuntimeError('Published asset differs from local build: ' + path.name)

    # Replace only the known source-only tag, after all Windows assets verify.
    # The tag will then identify the exact source and packaging used by this build.
    if ref['object']['sha'] != commit:
        gh('api', '--method', 'PATCH', f'repos/{repo}/git/refs/tags/{TAG}',
           '-f', f'sha={commit}', '-F', 'force=true')
    gh('release', 'edit', TAG, '--repo', repo,
       '--title', 'v7.11 - Windows ready to use',
       '--notes-file', str(ROOT / 'RELEASE_NOTES.md'),
       '--draft=false', '--prerelease=false', '--latest')
    info = json.loads(gh('release', 'view', TAG, '--repo', repo,
                         '--json', 'assets,isDraft,url'))
    published_names = {asset['name'] for asset in info['assets']}
    if info['isDraft'] or not set(actual_names.values()).issubset(published_names):
        raise RuntimeError('The public release is missing required Windows assets')
    print('Verified ready-to-use Windows release: ' + info['url'])


if __name__ == '__main__':
    main()

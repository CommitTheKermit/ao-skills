"""Launch the pinned Jev runtime with the existing agent and driver guards."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def runtime_info(current):
    runtime = current.resolve(strict=True)
    python = runtime / 'bin/python'
    receipt = json.loads((runtime / 'runtime.json').read_text())
    if (not re.fullmatch(r'[0-9a-f]{40}', receipt.get('source_sha', ''))
            or receipt.get('package_version') != '0.2.0'):
        raise ValueError('실행기 설치 영수증이 유효하지 않습니다.')
    probe = subprocess.run([str(python), '-I', '-c',
        'import json,sys,importlib.metadata,jev_mobile_use; '
        'print(json.dumps(dict(version=importlib.metadata.version("jev-mobile-use"),'
        'module=jev_mobile_use.__file__,prefix=sys.prefix)))'],
        capture_output=True, text=True, timeout=15, check=True)
    installed = json.loads(probe.stdout)
    if (installed['version'] != receipt['package_version']
            or Path(installed['prefix']).resolve() != runtime
            or not Path(installed['module']).resolve().is_relative_to(runtime)):
        raise ValueError('실행기 설치본과 영수증이 일치하지 않습니다.')
    return dict(receipt, python=str(python), module=installed['module'],
                backend='droidrun', coordination='agent')


def main(argv=None, current=None):
    args = list(sys.argv[1:] if argv is None else argv)
    current = current or Path.home()/'.local/share/jev-mobile-use/current'
    try:
        info = runtime_info(current)
        if args == ['--runtime-info']:
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 0
        # Last arguments win in argparse. A caller cannot replace either guard.
        os.execv(info['python'], [info['python'], '-I', '-m', 'jev_mobile_use', *args,
                                 '--backend', 'droidrun', '--coordination', 'agent'])
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError):
        print('Jev 고정 실행 환경을 확인할 수 없습니다. 설치 영수증과 current 경로를 확인하세요. '
              '기존 체크아웃 또는 ADB로 자동 전환하지 않습니다.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Submit fixed Plipa validation jobs over the configured private SSH transport."""
# usage-stats: harness plipa-remote-validation
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import uuid


def ps_quote(value):
    return "'"+value.replace("'","''")+"'"


def call(config, message):
    command='& '+ps_quote(config['python'])+' '+ps_quote(config['cli'])+' --config '+ps_quote(config['server_config'])
    encoded=base64.b64encode(command.encode('utf-16le')).decode('ascii')
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',config['host'],'powershell -NoProfile -EncodedCommand '+encoded],input=json.dumps(message).encode('utf-8'),capture_output=True,timeout=70)
    try:response=json.loads(result.stdout.decode('utf-8-sig'))
    except (ValueError,UnicodeError):raise ValueError('SSH 연결 또는 서버 응답을 확인하세요. 원격 작업은 자동 취소되지 않습니다.') from None
    if not response.get('ok'):raise ValueError(response.get('error','원격 요청 실패'))
    return response['result']


def main():
    usage=Path.home()/'.agents/skills/usage-stats/scripts/usage_stats.py'
    if usage.is_file():
        subprocess.run([sys.executable,str(usage),'record','harness','plipa-remote-validation'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=str(Path.home()/'.config/plipa-remote/client.json'))
    sub=parser.add_subparsers(dest='action',required=True)
    submit=sub.add_parser('submit');submit.add_argument('--sha',required=True);submit.add_argument('--profile',default='android-smoke');submit.add_argument('--request-id')
    sub.add_parser('list')
    for action in ('status','wait','cancel','results'):
        p=sub.add_parser(action);p.add_argument('job')
        if action=='results':p.add_argument('--output',required=True)
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text())
    if args.action=='submit':
        request_id=args.request_id or uuid.uuid4().hex
        print(json.dumps({'request_id':request_id}),file=sys.stderr,flush=True)
        message={'action':'submit','request':{'request_id':request_id,'sha':args.sha,'profile':args.profile}}
    else:
        message={'action':args.action}
        if hasattr(args,'job'):message['job']=args.job
    result=call(config,message)
    if args.action=='results':
        target=Path(args.output).expanduser()
        with target.open('xb') as output:output.write(base64.b64decode(result['data'],validate=True))
        result={'job':result['job'],'saved':str(target.resolve())}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.TimeoutExpired) as error:
        print(str(error) if isinstance(error,ValueError) else '로컬 설정, 연결 또는 결과 저장을 확인하세요.',file=sys.stderr)
        sys.exit(2)

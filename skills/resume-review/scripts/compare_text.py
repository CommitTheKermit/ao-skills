#!/usr/bin/env python3
"""이력서 원문을 고치기 전후로 비교한다.

사라지거나 새로 생긴 숫자, 바뀐 링크 주소, 금지 기호를 보고한다.
HTML이면 태그를 벗기고 글자만 본다. 숫자 하나가 달라졌으면 그것이
의도한 삭제인지 확인하라는 뜻이다.

사용법: compare_text.py <전 파일> <후 파일> [--forbid "금지할 글자들"]
"""
import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path


def plain(text):
    if '<' in text and '>' in text:
        text = re.sub(r'<script.*?</script>|<!--.*?-->', '', text, flags=re.S)
        text = re.sub(r'<[^>]+>', ' ', text)
    return html.unescape(text)


def numbers(text):
    return Counter(re.findall(r'\d[\d,.]*', text))


def hrefs(text):
    return Counter(re.findall(r'href="([^"]+)"', text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--forbid', default='\u00b7\u2014\u2013', help='결과에 있으면 안 되는 글자들(기본: 가운뎃점과 대시)')
    args = parser.parse_args()
    before = args.before.read_text(encoding='utf-8')
    after = args.after.read_text(encoding='utf-8')

    gone = numbers(plain(before)) - numbers(plain(after))
    new = numbers(plain(after)) - numbers(plain(before))
    link_gone = hrefs(before) - hrefs(after)
    link_new = hrefs(after) - hrefs(before)
    body = plain(after)
    forbidden = {c: body.count(c) for c in args.forbid if body.count(c)}

    print('사라진 숫자:', dict(gone) or '없음')
    print('새 숫자:', dict(new) or '없음')
    print('사라진 링크:', dict(link_gone) or '없음')
    print('새 링크:', dict(link_new) or '없음')
    print('금지 기호:', forbidden or '없음')
    return 1 if (gone or new or link_gone or link_new or forbidden) else 0


if __name__ == '__main__':
    sys.exit(main())

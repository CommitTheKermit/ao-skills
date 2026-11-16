#!/usr/bin/env python3
"""이력서 한 장을 평가하기 전에 훑어보기 재료를 뽑는다. 파일은 고치지 않는다.

뽑는 것: 제목과 굵은 글씨만 이은 목록(훑는 사람이 보는 것), 굵은 글씨가
없는 줄, 링크의 글자와 주소, 숫자가 든 줄, 어림 표현이 든 줄, 긴 줄.
HTML이 가장 정확하다. PDF는 굵은 글씨를 알 수 없어 글자, 숫자, 링크만 뽑는다.

사용법: inventory.py <이력서.html|.pdf|.md|.txt> [--bold-class 이름 ...] [--page-class page]
"""
import argparse
import re
import shutil
import subprocess
import sys
import zlib
from html.parser import HTMLParser
from pathlib import Path

INLINE = {'a', 'b', 'strong', 'span', 'em', 'i', 'u', 'code', 'small', 'sup', 'sub', 'mark', 'font', 'img'}
HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
VAGUE = re.compile(
    r'약\s?\d|대략|\d[\d,]*\s?여\s?(개|명|건|회|곳)|\d\s?(개|명|건|회|배|%)?\s?(이상|정도|가량|내외|안팎)'
    r'|수(십|백|천|만)\s?(개|명|건|회)|다수(?!결)|대폭|크게'
)
NUMBER = re.compile(r'\d')
LONG_LINE = 90


def bold_classes_from_css(css):
    """font-weight가 굵게 잡힌 규칙의 마지막 클래스 이름을 모은다."""
    found = set()
    for selector, body in re.findall(r'([^{}]+)\{([^}]*)\}', css):
        if re.search(r'font-weight\s*:\s*(bold|[6-9]00)', body):
            for part in selector.split(','):
                m = re.search(r'\.([\w-]+)\s*$', part.strip())
                if m:
                    found.add(m.group(1))
    return found


class Reader(HTMLParser):
    def __init__(self, bold_classes, page_class):
        super().__init__(convert_charrefs=True)
        self.bold_classes = bold_classes
        self.page_class = page_class
        self.lines = []  # (쪽, 종류, 전체 글자, 굵은 글자)
        self.links = []  # (쪽, 글자, 주소)
        self.page = 0
        self.buf, self.bold_buf = [], []
        self.stack = []  # (태그, 굵은지)
        self.skip = 0
        self.link = None
        self.heading = False

    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
        bold = re.sub(r'\s+', ' ', ''.join(self.bold_buf)).strip()
        if text:
            self.lines.append((self.page, '제목' if self.heading else '본문', text, bold))
        self.buf, self.bold_buf = [], []
        self.heading = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'title'):
            self.skip += 1
            return
        classes = (a.get('class') or '').split()
        if tag not in INLINE:
            self.flush()
        if self.page_class in classes:
            self.page += 1
        if tag in HEADINGS:
            self.heading = True
        is_bold = tag in ('b', 'strong') or bool(self.bold_classes & set(classes))
        if tag not in ('br', 'img', 'hr', 'meta', 'link', 'input'):
            self.stack.append((tag, is_bold))
        if tag == 'a':
            self.link = [a.get('href') or '', []]

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'title'):
            self.skip = max(0, self.skip - 1)
            return
        if tag == 'a' and self.link:
            label = re.sub(r'\s+', ' ', ''.join(self.link[1])).strip()
            self.links.append((self.page, label, self.link[0]))
            self.link = None
        if tag not in INLINE:
            self.flush()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip:
            return
        self.buf.append(data)
        if any(s[1] for s in self.stack):
            self.bold_buf.append(data)
        if self.link:
            self.link[1].append(data)


def read_html(path, extra_bold, page_class):
    html = path.read_text(encoding='utf-8')
    css = ' '.join(re.findall(r'<style[^>]*>(.*?)</style>', html, flags=re.S))
    for href in re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', html):
        sheet = path.parent / href
        if '://' not in href and sheet.is_file():
            css += sheet.read_text(encoding='utf-8', errors='ignore')
    reader = Reader(bold_classes_from_css(css) | set(extra_bold), page_class)
    reader.feed(html)
    reader.flush()
    return reader.lines, reader.links, []


def read_pdf(path):
    notes = ['PDF에서는 굵은 글씨와 링크 글자를 알 수 없다. 원본(HTML 등)이 있으면 그 파일로 다시 돌린다.']
    if not shutil.which('pdftotext'):
        sys.exit('pdftotext가 없다. poppler를 설치하거나, PDF를 직접 읽고 이 스크립트 없이 진행한다.')
    text = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True).stdout
    lines = []
    for page, chunk in enumerate(text.split('\f'), 1):
        for line in chunk.splitlines():
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                lines.append((page, '본문', line, ''))
    raw = path.read_bytes()
    blobs = [raw]
    for m in re.finditer(rb'stream\r?\n(.*?)endstream', raw, flags=re.S):
        try:
            blobs.append(zlib.decompress(m.group(1)))
        except zlib.error:
            pass
    uris = []
    for blob in blobs:
        for u in re.findall(rb'/URI\s*\((.*?)\)', blob):
            u = u.decode('latin-1')
            if u not in uris:
                uris.append(u)
    links = [(0, '(글자 알 수 없음)', u) for u in uris]
    if not links:
        notes.append('PDF에서 링크 주소를 찾지 못했다. 링크가 없거나 뽑을 수 없는 형식이다. 직접 눌러 확인한다.')
    return lines, links, notes


def read_text(path):
    lines, links = [], []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line:
            continue
        for label, url in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line):
            links.append((0, label, url))
        bold = ' '.join(re.findall(r'\*\*(.+?)\*\*', line))
        kind = '제목' if line.startswith('#') else '본문'
        lines.append((0, kind, re.sub(r'\*\*|^#+\s*', '', line), bold))
    return lines, links, []


def where(page):
    return f'[{page}쪽] ' if page else ''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('file', type=Path)
    parser.add_argument('--bold-class', action='append', default=[], help='굵게 보이는 CSS 클래스 이름(자동으로 못 찾을 때)')
    parser.add_argument('--page-class', default='page', help='한 쪽을 감싸는 요소의 클래스 이름(기본 page)')
    args = parser.parse_args()
    suffix = args.file.suffix.lower()
    if suffix in ('.html', '.htm'):
        lines, links, notes = read_html(args.file, args.bold_class, args.page_class)
    elif suffix == '.pdf':
        lines, links, notes = read_pdf(args.file)
    else:
        lines, links, notes = read_text(args.file)

    pages = max((line[0] for line in lines), default=0)
    chars = sum(len(line[2]) for line in lines)
    print(f'# {args.file.name}')
    print(f'쪽 {pages or "알 수 없음"}, 줄 {len(lines)}개, 글자 {chars}자')
    for note in notes:
        print(f'주의: {note}')

    if suffix != '.pdf':
        print('\n## 훑어보기: 제목과 굵은 글씨만 이은 것')
        for page, kind, text, bold in lines:
            if kind == '제목':
                print(f'{where(page)}(제목) {text}')
            elif bold:
                print(f'{where(page)}{bold}')
        plain = [(p, t) for p, k, t, b in lines if k == '본문' and not b]
        print(f'\n## 굵은 글씨가 없는 줄 {len(plain)}개 (훑는 사람에게는 안 보일 수 있다)')
        for page, text in plain:
            print(f'{where(page)}{text}')

    print(f'\n## 링크 {len(links)}개 (전부 열어 본다)')
    for page, label, url in links:
        flag = '  <- 주소 없음' if url in ('', '#') else ''
        print(f'{where(page)}"{label}" -> {url}{flag}')

    numbered = [(p, t) for p, k, t, b in lines if NUMBER.search(t)]
    print(f'\n## 숫자가 든 줄 {len(numbered)}개 (숫자마다 근거를 대조한다)')
    for page, text in numbered:
        print(f'{where(page)}{text}')

    vague = [(p, t, VAGUE.search(t).group(0)) for p, k, t, b in lines if VAGUE.search(t)]
    print(f'\n## 어림 표현이 든 줄 {len(vague)}개')
    for page, text, hit in vague:
        print(f'{where(page)}({hit.strip()}) {text}')

    longs = sorted(((len(t), p, t) for p, k, t, b in lines if len(t) >= LONG_LINE), reverse=True)
    print(f'\n## 긴 줄 {len(longs)}개 ({LONG_LINE}자 이상, 긴 순서)')
    for size, page, text in longs:
        print(f'{where(page)}{size}자: {text}')


if __name__ == '__main__':
    main()

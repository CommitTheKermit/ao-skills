#!/usr/bin/env node
/*
 * CSS 핸드오프 가드 — 빠른 2종(편집 즉시 훅용)
 *
 * 빌드/타입체크/단위테스트가 못 잡는 "문법상 valid 인데 규칙이 통째로 죽는" CSS
 * 잠복 버그를 직접 노린다. 실제 사례: 주석 안에 별표-슬래시 시퀀스(예: "sb-sub" 뒤에
 * 별표와 슬래시가 이어진 표기)가 들어가 주석이 조기 종료되고, 그 뒤 파서가 깨진 상태로
 * 다음 규칙 블록 전체를 잘못된 셀렉터의 본문으로 삼켜 통째로 버린다(렌더링에서만 드러남).
 *
 * 검사 2종:
 *   1) 구문(주석/괄호) 무결성  — 주석 조기종료(코드 영역의 stray 닫기), 미종료 주석, 괄호 불균형,
 *      그리고 postcss 로 파싱해 셀렉터에 주석 기호가 섞인 깨진 규칙 탐지(있을 때만).
 *   2) 누락 CSS 변수          — var(--x) 참조가 어디에도 정의되지 않고 fallback 도 없음.
 *
 * 사용:
 *   node css-guard.mjs <file.css> [file2.css ...]   # 지정 파일만 검사 (PostToolUse 훅)
 *   node css-guard.mjs --all                         # frontend/src 전체 css 스캔 (수동 스크립트)
 *
 * 종료코드: 문제 0개 → 0, 1개 이상 → 1. 사람이 읽는 메시지는 stderr.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, relative } from "node:path";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = resolve(SCRIPT_DIR, "..");
const SRC_ROOT = join(FRONTEND_ROOT, "src");

/* ── 파일 수집 ─────────────────────────────────────────────────────────── */
function walk(dir, exts, out = []) {
  let entries;
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const p = join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === "node_modules" || e.name === "dist" || e.name === "lib") continue;
      walk(p, exts, out);
    } else if (exts.some((x) => e.name.endsWith(x))) {
      out.push(p);
    }
  }
  return out;
}

/* ── 검사 1: 구문(주석/괄호) 상태머신 ───────────────────────────────────
   주석/문자열을 정확히 추적하며 코드 영역에서 별표-슬래시 닫기를 만나면 stray(조기종료 흔적)로 본다. */
function checkSyntax(src) {
  const errors = [];
  let i = 0, line = 1;
  let state = "code"; // code | comment | string
  let quote = null;
  let brace = 0;
  let commentStartLine = 0;
  while (i < src.length) {
    const c = src[i], n = src[i + 1];
    if (c === "\n") line++;
    if (state === "code") {
      if (c === "/" && n === "*") { state = "comment"; commentStartLine = line; i += 2; continue; }
      if (c === "*" && n === "/") {
        errors.push({ line, msg: "주석 밖에서 '*/' 발견 — 주석 안에 '*/' 가 섞여 주석이 조기 종료됐을 가능성. 이 지점 뒤 규칙이 통째로 무시될 수 있음." });
        i += 2; continue;
      }
      if (c === '"' || c === "'") { state = "string"; quote = c; }
      else if (c === "{") brace++;
      else if (c === "}") { brace--; if (brace < 0) { errors.push({ line, msg: "'}' 가 짝보다 많음 — 중괄호 불균형." }); brace = 0; } }
    } else if (state === "comment") {
      if (c === "*" && n === "/") { state = "code"; i += 2; continue; }
    } else if (state === "string") {
      if (c === "\\") { i += 2; continue; }
      if (c === quote) state = "code";
      else if (c === "\n") state = "code"; // CSS 문자열은 줄을 넘지 않음 → 복구
    }
    i++;
  }
  if (state === "comment") errors.push({ line: commentStartLine, msg: "주석이 닫히지 않음 (미종료 '/*')." });
  if (brace > 0) errors.push({ line, msg: `'{' 가 ${brace}개 안 닫힘 — 중괄호 불균형.` });
  return errors;
}

/* ── 검사 1b: postcss 보강 — 셀렉터에 주석 기호가 섞인 깨진 규칙 탐지 ──────
   postcss 는 lenient 라 안 던질 수 있어, 상태머신과 별개의 방어층으로만 쓴다. */
async function checkPostcss(src, file) {
  let postcss;
  try { ({ default: postcss } = await import("postcss")); } catch { return []; }
  const errors = [];
  let root;
  try {
    root = postcss.parse(src, { from: file });
  } catch (e) {
    errors.push({ line: e.line || 0, msg: `postcss 파싱 오류: ${e.reason || e.message}` });
    return errors;
  }
  root.walkRules((rule) => {
    if (/\*\/|\/\*/.test(rule.selector)) {
      const snip = rule.selector.replace(/\s+/g, " ").slice(0, 60);
      errors.push({
        line: rule.source?.start?.line || 0,
        msg: `셀렉터에 주석 기호(/* 또는 */)가 섞임 — 규칙 경계가 깨졌음: "${snip}…"`,
      });
    }
  });
  return errors;
}

/* ── 검사 2: 누락 CSS 변수 ─────────────────────────────────────────────── */
const DEF_RE = /(--[A-Za-z0-9_-]+)\s*:/g;          // 정의:  --x:
const SETPROP_RE = /setProperty\(\s*["'](--[A-Za-z0-9_-]+)["']/g; // JS 주입: setProperty("--x"
const USE_RE = /var\(\s*(--[A-Za-z0-9_-]+)\s*\)/g; // 참조(폴백 없음): var(--x)

function collectDefinedVars() {
  const defined = new Set();
  for (const f of walk(SRC_ROOT, [".css"])) {
    const s = readFileSync(f, "utf8");
    for (const m of s.matchAll(DEF_RE)) defined.add(m[1]);
  }
  for (const f of walk(SRC_ROOT, [".ts", ".tsx"])) {
    const s = readFileSync(f, "utf8");
    for (const m of s.matchAll(SETPROP_RE)) defined.add(m[1]);
  }
  return defined;
}

function checkMissingVars(src, defined) {
  const errors = [];
  for (const m of src.matchAll(USE_RE)) {
    const name = m[1];
    if (!defined.has(name)) {
      const line = src.slice(0, m.index).split("\n").length;
      errors.push({ line, msg: `정의되지 않은 CSS 변수 var(${name}) 참조(폴백 없음). 토큰 정의 누락이거나 오타.` });
    }
  }
  return errors;
}

/* ── 실행 ───────────────────────────────────────────────────────────────── */
async function main() {
  const args = process.argv.slice(2);
  let files;
  if (args.includes("--all")) {
    files = walk(SRC_ROOT, [".css"]);
  } else {
    files = args.filter((a) => a.endsWith(".css")).map((a) => resolve(a));
  }
  if (files.length === 0) process.exit(0);

  const defined = collectDefinedVars();
  let total = 0;
  for (const file of files) {
    let src;
    try { src = readFileSync(file, "utf8"); } catch { continue; }
    const errs = [
      ...checkSyntax(src),
      ...(await checkPostcss(src, file)),
      ...checkMissingVars(src, defined),
    ].sort((a, b) => a.line - b.line);
    if (errs.length) {
      const rel = relative(process.cwd(), file);
      for (const e of errs) {
        process.stderr.write(`  ${rel}:${e.line}  ${e.msg}\n`);
        total++;
      }
    }
  }
  if (total > 0) {
    process.stderr.write(`\n[css-guard 실패] CSS 무결성 문제 ${total}건 — 위 항목을 고칠 것.\n`);
    process.exit(1);
  }
  process.exit(0);
}

main();

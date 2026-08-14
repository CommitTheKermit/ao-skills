#!/usr/bin/env node
/*
 * 핸드오프 검증 오케스트레이터 — 넓은 검사(핸드오프 적용 직후 수동 실행)
 *
 *   npm run validate-handoff                       기본: 가드(전체) + stylelint + 셀렉터 리포트
 *   npm run validate-handoff -- --live <list.json> 추가: stale 번들 검사(라이브 파일목록 diff)
 *
 * 실패(종료코드 1) 기준: css-guard 또는 stylelint 에서 오류가 나면 실패.
 * 셀렉터 불일치/stale 은 휴리스틱이라 "참고"로만 출력하고 실패시키지 않는다.
 *
 * stale 검사의 라이브 파일목록(list.json)은 DesignSync(MCP) list_files 결과다.
 * node 는 MCP 를 못 부르므로, Claude 가 list_files 로 받은 경로 배열을 JSON 으로 저장해
 * --live 로 넘겨주면 이 스크립트가 디스크 번들과 비교한다.
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, basename } from "node:path";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = resolve(SCRIPT_DIR, "..");
const REPO_ROOT = resolve(FRONTEND_ROOT, "..");
const SRC_ROOT = join(FRONTEND_ROOT, "src");

const args = process.argv.slice(2);
const liveIdx = args.indexOf("--live");
const livePath = liveIdx >= 0 ? args[liveIdx + 1] : null;

let failed = false;
const sec = (t) => process.stdout.write(`\n\x1b[1m── ${t}\x1b[0m\n`);

/* ── 파일 수집 ─────────────────────────────────────────────────────────── */
function walk(dir, exts, out = []) {
  let entries;
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const p = join(dir, e.name);
    if (e.isDirectory()) {
      if (["node_modules", "dist", "lib"].includes(e.name)) continue;
      walk(p, exts, out);
    } else if (exts.some((x) => e.name.endsWith(x))) out.push(p);
  }
  return out;
}

/* ── 1) css-guard 전체 (구문 무결성 + 누락 변수) ─────────────────────────── */
sec("1. css-guard (구문 무결성 + 누락 변수) — 전체");
{
  const r = spawnSync("node", [join(SCRIPT_DIR, "css-guard.mjs"), "--all"], {
    cwd: FRONTEND_ROOT, encoding: "utf8",
  });
  if (r.stderr) process.stderr.write(r.stderr);
  if (r.status === 0) process.stdout.write("✅ 통과\n");
  else { failed = true; process.stdout.write("❌ 실패\n"); }
}

/* ── 2) stylelint (일반 CSS 품질/파싱) ──────────────────────────────────── */
sec("2. stylelint (일반 CSS 품질)");
{
  const r = spawnSync("npx", ["--no-install", "stylelint", "src/**/*.css"], {
    cwd: FRONTEND_ROOT, encoding: "utf8",
  });
  if (r.error || (r.status !== 0 && /not found|could not determine/i.test(r.stderr || ""))) {
    process.stdout.write("⚠️  stylelint 미설치 — 건너뜀 (npm i -D stylelint 후 사용)\n");
  } else {
    if (r.stdout) process.stdout.write(r.stdout);
    if (r.stderr) process.stderr.write(r.stderr);
    if (r.status === 0) process.stdout.write("✅ 통과\n");
    else { failed = true; process.stdout.write("❌ 실패\n"); }
  }
}

/* ── 3) 셀렉터 불일치 리포트 (참고, 실패 아님) ───────────────────────────── */
sec("3. 셀렉터 불일치 (참고 · 오탐 가능, 실패시키지 않음)");
{
  const cssClasses = new Set();
  for (const f of walk(SRC_ROOT, [".css"])) {
    const s = readFileSync(f, "utf8");
    // 주석 제거 후 .class 토큰 추출 (대략적)
    const noComment = s.replace(/\/\*[\s\S]*?\*\//g, " ");
    for (const m of noComment.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)) cssClasses.add(m[1]);
  }
  const usedTokens = new Set();
  for (const f of walk(SRC_ROOT, [".tsx", ".ts"])) {
    const s = readFileSync(f, "utf8");
    // className="a b c" / `a ${x} b` / 'a b' 안의 식별자 토큰을 거칠게 수집
    for (const m of s.matchAll(/className\s*=\s*[{"'`]([\s\S]*?)["'`}]/g)) {
      for (const t of m[1].split(/[\s"'`{}()?:&|+,]+/)) if (/^-?[A-Za-z_][\w-]*$/.test(t)) usedTokens.add(t);
    }
    // 보조: 문자열 리터럴 전체에서 클래스 같은 토큰도 수집(동적 className 대비)
    for (const m of s.matchAll(/["'`]([^"'`]*)["'`]/g)) {
      for (const t of m[1].split(/[\s]+/)) if (/^-?[A-Za-z_][\w-]*$/.test(t)) usedTokens.add(t);
    }
  }
  const orphans = [...cssClasses].filter((c) => !usedTokens.has(c)).sort();
  if (orphans.length === 0) process.stdout.write("✅ JSX 에서 안 쓰이는 CSS 클래스 없음\n");
  else {
    process.stdout.write(`ℹ️  JSX(className)에서 참조를 못 찾은 CSS 클래스 ${orphans.length}개 (동적 클래스/오탐 가능):\n`);
    process.stdout.write("   " + orphans.slice(0, 40).join(", ") + (orphans.length > 40 ? " …" : "") + "\n");
  }
}

/* ── 4) stale 번들 검사 (참고, 실패 아님) ────────────────────────────────── */
sec("4. stale 번들 (라이브 파일목록 diff · 참고)");
{
  const bundleDir = join(REPO_ROOT, ".design-handoff");
  if (!livePath) {
    process.stdout.write("⏭  --live <list.json> 미지정 — 건너뜀.\n");
    process.stdout.write("   Claude 가 DesignSync list_files 결과(경로 배열)를 JSON 으로 저장해\n");
    process.stdout.write("   `npm run validate-handoff -- --live live-files.json` 로 넘기면 비교한다.\n");
  } else if (!existsSync(bundleDir)) {
    process.stdout.write(`⏭  디스크 번들(${bundleDir}) 없음 — 건너뜀.\n`);
  } else {
    let live;
    try { live = JSON.parse(readFileSync(resolve(livePath), "utf8")); } catch (e) {
      process.stdout.write(`⚠️  --live 파일을 못 읽음: ${e.message}\n`); live = null;
    }
    if (Array.isArray(live)) {
      const diskNames = new Set(walk(bundleDir, [""]).map((p) => basename(p)));
      const liveNames = live.map((p) => basename(String(p)));
      const missing = [...new Set(liveNames.filter((n) => !diskNames.has(n)))].sort();
      if (missing.length === 0) process.stdout.write("✅ 라이브 파일이 모두 디스크 번들에 존재(파일명 기준)\n");
      else {
        process.stdout.write(`⚠️  라이브에 있으나 디스크 번들에 없는 파일 ${missing.length}개 — 번들이 stale 일 수 있음:\n`);
        process.stdout.write("   " + missing.slice(0, 40).join(", ") + (missing.length > 40 ? " …" : "") + "\n");
      }
    }
  }
}

/* ── 결과 ───────────────────────────────────────────────────────────────── */
process.stdout.write("\n" + "─".repeat(50) + "\n");
if (failed) { process.stdout.write("\x1b[31m검증 실패\x1b[0m — 위 ❌ 항목을 고칠 것.\n"); process.exit(1); }
process.stdout.write("\x1b[32m검증 통과\x1b[0m (참고 항목은 사람이 확인).\n");
process.exit(0);

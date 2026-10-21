#!/usr/bin/env python3
"""APK 설치 전 읽기 전용 비교. 설치, 제거, 데이터 초기화는 실행하지 않는다."""
# usage-stats: harness android-install-preflight
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode:
        # 도구 출력에는 기기 정보가 있을 수 있으므로 통째로 출력하지 않는다.
        raise ValueError(f"{Path(command[0]).name} 조회 실패")
    return result.stdout


def tool(name, sdk_subdir):
    found = shutil.which(name)
    if found:
        return found
    roots = [os.environ.get("ANDROID_SDK_ROOT"), os.environ.get("ANDROID_HOME"), str(Path.home()/"Library/Android/sdk")]
    for root in filter(None, roots):
        candidates = list(Path(root).glob(f"{sdk_subdir}/{name}"))
        if candidates:
            return str(sorted(candidates, key=lambda p: [int(x) for x in re.findall(r"\d+", str(p))])[-1])
    raise ValueError(f"{name} 도구를 찾지 못했습니다.")


def apk_metadata(aapt, signer, apk):
    info = run([aapt, "dump", "badging", str(apk)])
    package = re.search(r"^package: name='([^']+)' versionCode='(\d+)' versionName='([^']*)'", info, re.M)
    if not package:
        raise ValueError("APK 패키지와 버전을 읽지 못했습니다.")
    certificates = re.findall(r"Signer #\d+ certificate SHA-256 digest:\s*([a-fA-F0-9:]+)",
                              run([signer, "verify", "--print-certs", str(apk)]))
    if not certificates:
        raise ValueError("APK 서명 인증서를 확인하지 못했습니다.")
    return {"package":package[1], "version_code":int(package[2]), "version_name":package[3],
            "signer_sha256":sorted(x.replace(":", "").lower() for x in certificates)}


def require_lease(serial):
    if not serial.startswith("emulator-"):
        return
    owner = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    directory = Path(os.environ.get("CODEX_ANDROID_LEASE_DIR", str(Path.home()/".codex/android-emulator-leases")))
    for path in directory.glob("*.json"):
        lease = json.loads(path.read_text())
        if owner and lease.get("owner") == owner and lease.get("serial") == serial:
            return
    raise ValueError("대상 에뮬레이터 serial에 연결된 현재 세션 임대가 필요합니다.")


def installed_metadata(adb, serial, package, aapt, signer):
    def query(*args):
        return run([adb, "-s", serial, *args])
    packages = query("shell", "pm", "list", "packages", "--user", "current", package)
    if f"package:{package}" not in packages.splitlines():
        return None
    paths = query("shell", "pm", "path", "--user", "current", package)
    bases = [line.removeprefix("package:").strip() for line in paths.splitlines()
             if line.startswith("package:") and line.strip().endswith("/base.apk")]
    if len(bases) != 1:
        raise ValueError("설치된 base APK를 하나로 식별하지 못했습니다.")
    with tempfile.TemporaryDirectory(prefix="apk-preflight-") as directory:
        path = Path(directory)/"installed.apk"
        query("pull", bases[0], str(path))
        return apk_metadata(aapt, signer, path)


def compare(target, installed, expected_package):
    reasons = []
    if target["package"] != expected_package:
        reasons.append("target_package_mismatch")
    if installed:
        if installed["package"] != expected_package:
            reasons.append("installed_package_mismatch")
        if target["version_code"] < installed["version_code"]:
            reasons.append("version_downgrade")
        if target["signer_sha256"] != installed["signer_sha256"]:
            reasons.append("signer_mismatch_or_unverified_rotation")
    return {"allowed":not reasons, "installation":"update" if installed else "new",
            "reasons":reasons, "target":target, "installed":installed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--source-sha", help="빌드 기록과 함께 제공하는 선언값. APK 출처의 독립 검증은 아님")
    args = parser.parse_args()
    recorder = Path.home()/".agents/skills/usage-stats/scripts/usage_stats.py"
    if recorder.exists():
        subprocess.run([sys.executable, str(recorder), "record", "harness", "android-install-preflight"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    try:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", args.package):
            raise ValueError("패키지명이 유효하지 않습니다.")
        require_lease(args.serial)
        artifact_hash = hashlib.sha256(args.apk.read_bytes()).hexdigest()
        aapt, signer, adb = tool("aapt", "build-tools/*"), tool("apksigner", "build-tools/*"), tool("adb", "platform-tools")
        target = apk_metadata(aapt, signer, args.apk)
        # 잘못된 APK면 기기에 접근하기 전에 종료한다.
        if target["package"] != args.package:
            result = compare(target, None, args.package)
        else:
            result = compare(target, installed_metadata(adb, args.serial, args.package, aapt, signer), args.package)
        if artifact_hash != hashlib.sha256(args.apk.read_bytes()).hexdigest():
            result["allowed"] = False
            result["reasons"].append("apk_changed_during_inspection")
        result.update(serial=args.serial, apk_sha256=artifact_hash, declared_source_sha=args.source_sha)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["allowed"] else 2
    except (ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps({"allowed":False,"reasons":["inspection_failed"],"serial":args.serial}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())

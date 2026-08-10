#!/usr/bin/env bash
set -euo pipefail

project_root="${1:-$PWD}"

if [[ -x "$project_root/gradlew" ]]; then
  android_root="$project_root"
elif [[ -x "$project_root/android/gradlew" ]]; then
  android_root="$project_root/android"
else
  echo "error: gradlew not found under $project_root" >&2
  exit 1
fi

cd "$android_root"

if [[ ! -f app/build.gradle.kts && ! -f app/build.gradle ]]; then
  echo "error: app module not found under $android_root" >&2
  exit 1
fi

./gradlew :app:testDebugUnitTest :app:bundleRelease

aab="app/build/outputs/bundle/release/app-release.aab"
manifest="app/build/intermediates/bundle_manifest/release/processApplicationManifestReleaseForBundle/AndroidManifest.xml"

[[ -s "$aab" ]] || { echo "error: AAB not found: $aab" >&2; exit 1; }
[[ -f "$manifest" ]] || { echo "error: bundle manifest not found: $manifest" >&2; exit 1; }

jarsigner -verify "$aab" >/dev/null

application_id="$(sed -n 's/.*package="\([^"]*\)".*/\1/p' "$manifest" | head -n 1)"
version_code="$(sed -n 's/.*android:versionCode="\([^"]*\)".*/\1/p' "$manifest" | head -n 1)"
version_name="$(sed -n 's/.*android:versionName="\([^"]*\)".*/\1/p' "$manifest" | head -n 1)"
icon_name="$(sed -n 's/.*android:icon="@mipmap\/\([^"]*\)".*/\1/p' "$manifest" | head -n 1)"

[[ -n "$application_id" && -n "$version_code" && -n "$version_name" ]] || {
  echo "error: application ID or version missing from bundle manifest" >&2
  exit 1
}

[[ -n "$icon_name" ]] || { echo "error: launcher icon missing from bundle manifest" >&2; exit 1; }
aab_entries="$(unzip -Z1 "$aab")"
grep -Eq "^base/res/mipmap[^/]*/${icon_name}\\." <<<"$aab_entries"

release_dir="app/release"
artifact="$release_dir/${application_id##*.}-${version_name}-code${version_code}.aab"
mkdir -p "$release_dir"
cp "$aab" "$artifact"

if command -v shasum >/dev/null 2>&1; then
  checksum="$(shasum -a 256 "$artifact" | awk '{print $1}')"
else
  checksum="$(sha256sum "$artifact" | awk '{print $1}')"
fi

echo "applicationId=$application_id"
echo "versionCode=$version_code"
echo "versionName=$version_name"
echo "signature=verified"
echo "launcherIcon=verified"
echo "sha256=$checksum"
echo "artifact=$android_root/$artifact"

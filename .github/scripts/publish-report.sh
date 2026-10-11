#!/usr/bin/env bash
# Publishes a report folder into a sub-folder of the gh-pages branch and
# rebuilds the landing page (index.html) that links every published report.
# Other sub-folders are left untouched, so each workflow/environment keeps
# its own latest report on the same GitHub Pages site.
#
# Usage: publish-report.sh <report_dir> <dest_dir> <label>
# Needs GITHUB_TOKEN with contents: write; the GITHUB_* vars come from Actions.
set -euo pipefail

src="$1"
dest="$2"
label="$3"

repo_url="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
work="$(mktemp -d)"

if git ls-remote --exit-code --heads "$repo_url" gh-pages >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch gh-pages "$repo_url" "$work"
else
  git init --quiet -b gh-pages "$work"
  git -C "$work" remote add origin "$repo_url"
fi

rm -rf "${work:?}/$dest"
mkdir -p "$work/$dest"
cp -R "$src"/. "$work/$dest"/
touch "$work/.nojekyll"
printf '%s|%s|%s\n' "$label" "$(date -u '+%Y-%m-%d %H:%M UTC')" "$run_url" > "$work/$dest/.published"

{
  cat <<'HTML'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Test Reports</title>
<style>
  :root { color-scheme: light dark; --bg: #fff; --fg: #1f2328; --muted: #59636e; --line: #d1d9e0; --link: #0969da; }
  @media (prefers-color-scheme: dark) { :root { --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1; --line: #3d444d; --link: #4493f8; } }
  body { margin: 0; padding: 32px 16px; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 24px; margin: 0 0 4px; }
  p { color: var(--muted); margin: 0 0 24px; }
  ul { list-style: none; padding: 0; margin: 0; border-top: 1px solid var(--line); }
  li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 16px; padding: 14px 0; border-bottom: 1px solid var(--line); }
  a { color: var(--link); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .name { font-weight: 600; }
  .meta { color: var(--muted); font-size: 14px; }
</style>
</head>
<body>
<main>
<h1>API Test Reports</h1>
<p>Latest reportingLabs report per workflow and environment.</p>
<ul>
HTML
  find "$work" -name .published -not -path '*/.git/*' | sort | while read -r f; do
    dir="${f#"$work"/}"
    dir="${dir%/.published}"
    IFS='|' read -r l t r < "$f"
    echo "<li><a class=\"name\" href=\"$dir/\">$l</a><span class=\"meta\">$t · <a href=\"$r\">workflow run</a></span></li>"
  done
  cat <<'HTML'
</ul>
</main>
</body>
</html>
HTML
} > "$work/index.html"

cd "$work"
git add -A
git -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit --quiet -m "Publish $label report (run $GITHUB_RUN_ID)"
git push --quiet origin gh-pages
echo "Published to: https://${GITHUB_REPOSITORY_OWNER}.github.io/${GITHUB_REPOSITORY#*/}/$dest/"

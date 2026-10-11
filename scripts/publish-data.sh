#!/bin/sh
# Export the static-site data and publish it as a GitHub Release (doc/Plan.md, Phase 9).
# The Pages workflow (.github/workflows/pages.yml) builds the site from the newest
# release whose tag starts with "data-". Needs: docker, gh (logged in), a GitHub remote.
#
#   scripts/publish-data.sh            # export the baseline campaign and publish
#   scripts/publish-data.sh --dry-run  # export and pack only
set -eu
cd "$(dirname "$0")/.."

tag="data-$(date -u +%Y%m%d-%H%M)"
site=data/site
rm -rf "$site"
docker compose --profile serve run --rm --no-deps -e GIT_COMMIT="$(git rev-parse --short HEAD)" api \
  python -m hclust_api.export --out /data/site/data --outputs /data/site/outputs.tar.xz
tar -czf "$site/site-data.tar.gz" -C "$site" data
ls -lh "$site/site-data.tar.gz" "$site/outputs.tar.xz"

if [ "${1:-}" = "--dry-run" ]; then
  echo "dry run: not publishing $tag"
  exit 0
fi
gh release create "$tag" "$site/site-data.tar.gz" "$site/outputs.tar.xz" \
  --title "Results snapshot $tag" \
  --notes "Static-site data exported from commit $(git rev-parse --short HEAD) (site-data.tar.gz) and the raw ORCA input/output of every job the site links to (outputs.tar.xz, as outputs/<job id>/job.inp|job.out)."
gh workflow run pages.yml
echo "published $tag; the Pages workflow is rebuilding the site"

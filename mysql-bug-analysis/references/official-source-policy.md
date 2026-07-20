# Official Source Policy

## Final-evidence priority

1. MySQL official BUG system.
2. MySQL official Reference Manual and Release Notes.
3. MySQL official `mysql-server` repository, tags, commits, diffs, and tests.
4. Oracle support material supplied by the user under their access rights.
5. Official upstream dependency documentation or source when the defect is outside MySQL.
6. Secondary technical material only as an investigation lead.

## Rules

- Search current official sources before stating status, affected range, or fixed release.
- Save official pages or structured extracts under `evidence/official/`; record URL and retrieval date.
- Separate reported version, verified version, affected range, fixed release, commit branch, and locally tested version.
- Do not treat a directory name, package version, blog, forum answer, or vendor repost as the final fixed-version authority.
- When official sources conflict, present the conflict and test the relevant tags; do not choose silently.
- For an unpublished or inaccessible BUG, say so and base conclusions on supplied artifacts and version-pinned source.

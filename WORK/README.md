# WORK — finished, retrievable products

`WORK/` is the repository destination for products made by Arena toolbox runs.
It supersedes the earlier placeholder `products/` location for new work.

For every product, create a descriptive subdirectory containing:

- the downloadable artifact (for example, a source ZIP, APK, or Windows build);
- a short `README.md` with purpose, version, targets, run/install steps, and
  limitations;
- compact provenance and validation reports, including hashes where useful;
- the immutable commit-pinned GitHub raw URL used as the Arena download link.

Do **not** store disposable engines, SDKs, JDKs, export templates, dependency
folders, caches, signing keys, or secrets here. If an artifact is too large for
Git, use approved artifact storage and save its retrieval URL and integrity
information in the product README.

Before deleting an Arena workspace, push the product, retrieve it from GitHub,
and verify the stored bytes. The user-facing completion message must state the
artifact path and give a direct download link.

# Per-rubric extracts

This folder is a **promotion target** for individual rubrics that
grow past ~500 words on their own (per the splitting policy in
`../quality_rubrics.md`). Today: empty.

If/when a rubric is promoted here, the parent doc keeps a
one-paragraph summary + a link, and this directory hosts the
extended treatment.

Reasons to promote a rubric here:

- The rubric grows enough that scrolling past it in the main doc
  is friction (~500 words).
- A single audience needs to reference it independently (e.g., a
  code reviewer linked to the Code Quality rubric directly).
- Multiple maintainers want to own different rubrics with their
  own git history.

When you promote a rubric to this folder:

1. Move the section from `docs/quality_rubrics.md` to `docs/rubrics/<rubric_name>.md`.
2. Replace the original section in `quality_rubrics.md` with a
   one-paragraph summary + `[Read the full rubric](rubrics/<name>.md)`.
3. Update the navigation table at the top of `quality_rubrics.md`.
4. Update the aggregate scorecard reference if needed.

The aggregate scorecard at the bottom of `quality_rubrics.md`
remains the single source of truth for current scores.

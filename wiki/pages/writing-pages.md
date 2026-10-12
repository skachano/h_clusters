# Writing pages

## Adding a page

1. Create `wiki/pages/<section>/<topic>.md` (lowercase, hyphens:
   `potential-energy-surface.md`).
2. Add it to `nav` in `wiki/mkdocs.yml`, under its section.
3. Link it from the section's `index.md`.

## Translations

Every page has a Japanese translation next to it: `page.md` (English) and
`page.ja.md` (Japanese). The `i18n` plugin in `mkdocs.yml` builds both
languages and adds the language switch; a page without a `.ja.md` falls back
to English.

- Write or change the English page first, then update its `.ja.md` in the
  same commit.
- New navigation titles need a Japanese entry under `nav_translations` in
  `mkdocs.yml`.
- Keep link anchors identical across languages: a Japanese heading that other
  pages link to gets the English anchor explicitly, e.g.
  `## 結合の切断 { #bond-breaking }`.
- Code, program output and chart labels stay in English.
- Japanese paragraphs are kept on one source line: Markdown turns a line
  break inside a paragraph into a space, which is visible between Japanese
  characters. Write wrapped if you like, then run
  `python3 wiki/tools/join_ja.py wiki/pages/**/*.ja.md` to join the lines.

## Page template

```markdown
# Potential energy surface

!!! info "Prerequisites"
    [Born–Oppenheimer approximation](born-oppenheimer.md)

One-paragraph summary: what it is and why it matters here.

## Idea

The concept in plain language, then the equations.

## Example

A worked example, preferably with numbers from this project.

## Where this appears in h_clusters

- Code: `worker/src/hclust/levels.py`
- Plan: `doc/Plan.md` §2.1

## References

- Jensen, *Introduction to Computational Chemistry*, §12.1
```

## Syntax

**Math** uses LaTeX. Inline: `$E = h\nu$` gives $E = h\nu$. Display:

```latex
$$
\hat{H}\Psi = E\Psi
$$
```

$$
\hat{H}\Psi = E\Psi
$$

**Callouts** (`!!! note`, `!!! warning`, `!!! example`; use `???` for a
collapsed block):

!!! warning "Self-interaction error"
    DFT lets an electron repel itself.

**Diagrams** use a fenced block with the language `mermaid`.

**Links** between pages are relative Markdown links to the `.md` file, e.g.
`[Hartree–Fock](../methods/hartree-fock.md)`. A strict build reports broken
links.

**Links into the web app** start with `app:` followed by the app's route
without the campaign: `[H₃⁺](app:s/3/1/1)` opens the species page of H₃⁺
(size, charge, multiplicity), `app:trends` the trends, `app:` the grid. Add
`c/<campaign>/` for a campaign other than baseline:
`app:c/demo/s/5/1/1`. Japanese pages open the app in Japanese. The hook
`wiki/hooks/app_links.py` turns these into real addresses: the local dev
server, or the app on GitHub Pages. A species route that is not a state of
the app fails the strict build; other routes are not checked, so open them
once in the preview.

Every mention of a species links to its page in the app.
After writing a page, run

```sh
python3 wiki/tools/link_species.py wiki/pages/**/*.md
```

It adds the missing links (ground state, or the spin state named next to the
formula: "triplet H₃⁺"). A formula of several units links as a whole to the
species they add up to: H₃⁺·H₂ and (H₂)₂ open H₅⁺ and H₄. It leaves alone
headings, code, math, families with a variable count like H⁻(H₂)ₖ, and the
atom H and proton H⁺, which are not in the app. A pair or reaction written
with + is linked by hand, whole, to the species it makes:
`[H₃⁺ + H₂ → H₅⁺](app:s/5/1/1)`. A "Web app:" bullet under "Where this
appears in h_clusters" points to the view that shows the page's topic.

## Preview and check

```sh
docker compose --profile docs up docs        # live preview, http://localhost:8001
docker compose run --rm docs build --strict  # fail on broken links or nav errors
```

The docs image (`wiki/Dockerfile`) adds the i18n plugin to MkDocs Material;
`docker compose build docs` rebuilds it after a version change.

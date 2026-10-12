/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" in the GitHub Pages build: data comes from exported JSON, not the API (doc/Plan.md, Phase 9). */
  readonly VITE_STATIC?: string;
  /** Static build: the release asset holding the raw ORCA files. */
  readonly VITE_OUTPUTS_URL?: string;
  /** Where the wiki lives, if not <base>/wiki/ (static) or port 8001 of this host (dev). */
  readonly VITE_WIKI_URL?: string;
}

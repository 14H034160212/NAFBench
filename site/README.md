# NAF-Bench demo — Cloudflare Pages deployment

A fully **static** site (HTML + one JS data file + PNGs). No backend, no build
step, no environment variables — the solver labels and model answers are
precomputed and baked into `data.js`, so it works on any static host.

```
site/
  index.html     the interactive page
  data.js        precomputed data (window.NAFBENCH = {...})
  img/*.png      figures
```

## Deploy to Cloudflare Pages

**Option A — dashboard (no build):**
1. Cloudflare dashboard → Workers & Pages → Create → Pages → *Upload assets*
   (or *Connect to Git* and point at this repo).
2. If connecting to Git: set **Build command: (none)** and
   **Build output directory: `site`**. (If you upload assets directly, just drag
   the `site/` folder.)
3. Deploy. The site is served at `https://<project>.pages.dev`.

**Option B — Wrangler CLI:**
```bash
npm i -g wrangler
wrangler pages deploy site --project-name nafbench-demo
```

## Notes
- To refresh the data after new experiments, regenerate from the repo root:
  `python build_site.py` (rewrites `site/data.js` and copies `data/*.png` →
  `site/img/`), then redeploy.
- Everything is client-side; nothing is logged or sent anywhere.
- Access control (so only Kerry / the team can view): Cloudflare Pages →
  project → **Settings → Access policy** (Cloudflare Access) lets you restrict by
  email — useful if you don't want it fully public.

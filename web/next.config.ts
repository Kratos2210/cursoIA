import type { NextConfig } from "next";
import createMDX from "@next/mdx";
import { join } from "node:path";

const nextConfig: NextConfig = {
  // Allow .mdx as a first-class page/route extension alongside TS.
  pageExtensions: ["ts", "tsx", "mdx"],
  // The lesson route moved from /modulo/[slug] to /concepto/[slug]. Keep any
  // external links (shared URLs, indexed pages) alive with a permanent 301.
  async redirects() {
    return [
      { source: "/modulo/:slug", destination: "/concepto/:slug", permanent: true },
    ];
  },
};

// @next/mdx resolves plugin-path strings with require.resolve relative to the
// MDX file's directory, so a "./lib/…" relative path never resolves. Give it an
// absolute path (still a string → serializable under Turbopack). next build runs
// with cwd = project root.
const codeTitlePlugin = join(process.cwd(), "lib", "rehype-code-title.mjs");

// Plugins are passed as string tuples so the config stays serializable and
// works under Turbopack (dev) and webpack (build) alike. Shiki runs at build
// time with dual themes exposed as CSS variables (defaultColor:false) so the
// site's light/dark toggle drives code colors with zero client JS.
const withMDX = createMDX({
  options: {
    remarkPlugins: [["remark-gfm"]],
    rehypePlugins: [
      // Local plugin: lift the fence title into a <figure><figcaption> BEFORE
      // shiki runs (shiki would otherwise discard the meta). Path string keeps
      // the config serializable under Turbopack.
      [codeTitlePlugin],
      // Stable ids on h2/h3 so intra-page anchors and the "En esta página" rail
      // (components/app/OnThisPage) can link to sections.
      ["rehype-slug"],
      [
        "@shikijs/rehype",
        {
          themes: { light: "github-light", dark: "github-dark" },
          defaultColor: false,
        },
      ],
    ],
  },
});

export default withMDX(nextConfig);

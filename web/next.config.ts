import type { NextConfig } from "next";
import createMDX from "@next/mdx";

const nextConfig: NextConfig = {
  // Allow .mdx as a first-class page/route extension alongside TS.
  pageExtensions: ["ts", "tsx", "mdx"],
};

// Plugins are passed as string tuples so the config stays serializable and
// works under Turbopack (dev) and webpack (build) alike. Shiki runs at build
// time with dual themes exposed as CSS variables (defaultColor:false) so the
// site's light/dark toggle drives code colors with zero client JS.
const withMDX = createMDX({
  options: {
    remarkPlugins: [["remark-gfm"]],
    rehypePlugins: [
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

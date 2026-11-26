import type { NextConfig } from "next";

const staticExport = process.env.RENDER_STATIC_EXPORT === "1";
const pageExtensions = ["tsx", "ts", "jsx", "js"];

const nextConfig: NextConfig = staticExport
  ? {
      output: "export",
      trailingSlash: true,
      images: { unoptimized: true },
      pageExtensions,
    }
  : {
      // The Docker registry needs the Next.js server at request time.
      pageExtensions: ["registry.ts", ...pageExtensions],
    };

export default nextConfig;

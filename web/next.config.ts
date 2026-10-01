import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cloud Run runs this as a container: standalone output ships the server and
  // only the packages it actually uses, instead of the whole node_modules tree.
  output: "standalone",
};

export default nextConfig;

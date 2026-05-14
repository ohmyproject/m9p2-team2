/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["@xenova/transformers", "onnxruntime-node"],
  },
};

module.exports = nextConfig;

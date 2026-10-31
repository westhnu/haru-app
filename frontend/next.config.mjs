/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Amplify Hosting Compute는 콘솔 env를 빌드타임만 노출하고 SSR Lambda 런타임엔 안 내려준다.
  // 서버 라우트에서 쓰는 키들을 빌드 시점에 process.env 로 베이크인.
  env: {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    OPENAI_MODEL: process.env.OPENAI_MODEL,
    VERIFY_MODEL: process.env.VERIFY_MODEL,
    TAVILY_API_KEY: process.env.TAVILY_API_KEY,
    DART_API_KEY: process.env.DART_API_KEY,
    KIS_APP_KEY: process.env.KIS_APP_KEY,
    KIS_APP_SECRET: process.env.KIS_APP_SECRET,
    KIS_APP_KEY_PROD: process.env.KIS_APP_KEY_PROD,
    KIS_APP_SECRET_PROD: process.env.KIS_APP_SECRET_PROD,
    KIS_ENV: process.env.KIS_ENV,
    CRON_SECRET: process.env.CRON_SECRET,
    STORAGE: process.env.STORAGE,
    S3_BUCKET: process.env.S3_BUCKET,
    TWELEVE_KEY: process.env.TWELEVE_KEY,
  },
  // FastAPI 백엔드 프록시. 신규 경로(/workbook·/checklist·/journal·/glossary)는 이걸로
  // FastAPI를 거쳐 Bedrock Guardrail + core.guardrail 이중 방어를 통과한다 (KI-018).
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Amplify Hosting Compute는 콘솔 env를 빌드타임만 노출하고 SSR Lambda 런타임엔 안 내려준다.
  // 서버 라우트에서 쓰는 키들을 빌드 시점에 process.env 로 베이크인.
  env: {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    OPENAI_MODEL: process.env.OPENAI_MODEL,
    GEMINI_API_KEY: process.env.GEMINI_API_KEY,
    GOOGLE_API_KEY: process.env.GOOGLE_API_KEY,
    GEMINI_MODEL: process.env.GEMINI_MODEL,
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
};

export default nextConfig;

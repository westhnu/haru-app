// 빌드 시점에 인라인되는 공개 플래그 (비밀 아님, KI-019와 무관).
// "1"일 때만 로컬 FastAPI 백엔드(/backend 프록시)에 기대는 화면을 노출한다.
// 운영 Amplify는 미설정 = off → 백엔드 없이도 기존 화면이 깨지지 않는다.
export const HARU_BACKEND_ENABLED = process.env.NEXT_PUBLIC_HARU_BACKEND === "1";

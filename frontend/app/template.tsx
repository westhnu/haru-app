// template.tsx 는 layout 과 달리 라우트 전환 시 매번 새로 마운트된다.
// 가벼운 fade-up 애니메이션을 모든 페이지에 일관 적용 → 페이지 전환이 부드러워짐.
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="animate-fade-up">{children}</div>;
}

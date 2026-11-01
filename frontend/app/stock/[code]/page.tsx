import StockDetail, { type StockTab } from "@/components/StockDetail";

const TABS: readonly StockTab[] = ["info", "financial", "workbook"];

export default function StockPage({
  params,
  searchParams,
}: {
  params: { code: string };
  searchParams: { name?: string; tab?: string };
}) {
  // /workbook 목록에서 ?tab=workbook 으로 들어오면 워크북 탭을 바로 연다.
  const initialTab = TABS.find((t) => t === searchParams.tab) ?? "info";
  return (
    <StockDetail
      code={decodeURIComponent(params.code)}
      name={searchParams.name}
      initialTab={initialTab}
    />
  );
}

import StockDetail from "@/components/StockDetail";

export default function StockPage({
  params,
  searchParams,
}: {
  params: { code: string };
  searchParams: { name?: string };
}) {
  return (
    <StockDetail code={decodeURIComponent(params.code)} name={searchParams.name} />
  );
}

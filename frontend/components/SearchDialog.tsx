"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Book, ChevronRight, Search, X } from "lucide-react";
import { HARU_BACKEND_ENABLED } from "@/lib/featureFlags";
import krxCodesRaw from "@/lib/krx-codes.json";

// 자주 찾는 해외 종목 — TwelveData free tier 로 조회 가능한 주요 티커.
// 검색 결과에 함께 노출해서 NVDA / AAPL 등 빠른 진입.
const US_TICKERS: { name: string; symbol: string; exchange: string }[] = [
  { name: "엔비디아", symbol: "NVDA", exchange: "NASDAQ" },
  { name: "애플", symbol: "AAPL", exchange: "NASDAQ" },
  { name: "마이크로소프트", symbol: "MSFT", exchange: "NASDAQ" },
  { name: "구글 (알파벳 A)", symbol: "GOOGL", exchange: "NASDAQ" },
  { name: "아마존", symbol: "AMZN", exchange: "NASDAQ" },
  { name: "메타 플랫폼", symbol: "META", exchange: "NASDAQ" },
  { name: "테슬라", symbol: "TSLA", exchange: "NASDAQ" },
  { name: "넷플릭스", symbol: "NFLX", exchange: "NASDAQ" },
  { name: "AMD", symbol: "AMD", exchange: "NASDAQ" },
  { name: "인텔", symbol: "INTC", exchange: "NASDAQ" },
  { name: "브로드컴", symbol: "AVGO", exchange: "NASDAQ" },
  { name: "TSMC", symbol: "TSM", exchange: "NYSE" },
  { name: "코카콜라", symbol: "KO", exchange: "NYSE" },
  { name: "JP모건체이스", symbol: "JPM", exchange: "NYSE" },
  { name: "비자", symbol: "V", exchange: "NYSE" },
];

const krxMap = krxCodesRaw as Record<string, string>;

type Hit = {
  name: string;
  code: string; // 6자리 KR 코드 또는 US 티커
  market: string; // KOSPI/KOSDAQ/NASDAQ 등
};

// 검색 매칭: name 부분문자열 + 코드/심볼 prefix
function search(q: string, limit = 25): Hit[] {
  const query = q.trim().toLowerCase();
  if (!query) return [];
  const hits: Hit[] = [];

  // KRX (한국 종목)
  for (const [name, code] of Object.entries(krxMap)) {
    if (hits.length >= limit) break;
    if (
      name.toLowerCase().includes(query) ||
      code.startsWith(query)
    ) {
      hits.push({ name, code, market: "" });
    }
  }
  // US 티커
  for (const t of US_TICKERS) {
    if (hits.length >= limit) break;
    if (
      t.name.toLowerCase().includes(query) ||
      t.symbol.toLowerCase().includes(query)
    ) {
      hits.push({ name: t.name, code: t.symbol, market: t.exchange });
    }
  }
  return hits;
}

export default function SearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // 다이얼로그 열림 시 즉시 포커스
  useEffect(() => {
    if (open) {
      // 다음 tick에 포커스 (입력창 mount 후)
      setTimeout(() => inputRef.current?.focus(), 10);
    } else {
      setQ("");
    }
  }, [open]);

  // ESC 로 닫기
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const results = useMemo(() => search(q), [q]);

  // body scroll lock
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal
      aria-label="종목 검색"
      className="fixed inset-0 z-50 flex items-end sm:items-start sm:justify-center sm:pt-24"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />

      <div className="relative z-10 mx-auto w-full max-w-container-sm md:max-w-container-md overflow-hidden rounded-t-[28px] border border-border bg-surface shadow-card sm:rounded-[28px]">
        {/* 검색 입력 */}
        <div className="flex items-center gap-3 border-b border-border-subtle px-5 py-4">
          <Search className="h-5 w-5 shrink-0 text-fg-subtle" />
          <input
            ref={inputRef}
            type="text"
            inputMode="search"
            autoComplete="off"
            placeholder="종목을 검색해 보세요 (예: 삼성전자, NVDA, 005930)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="min-w-0 flex-1 bg-transparent text-base font-semibold text-fg placeholder:font-medium placeholder:text-fg-subtle focus:outline-none"
          />
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-fg-subtle transition hover:bg-border-subtle hover:text-fg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* 결과 영역 */}
        <div className="max-h-[60vh] overflow-y-auto px-2 py-2">
          {/* 용어 사전 — 플래그 on에서 BottomNav "용어" 탭을 대신하는 진입점 */}
          {HARU_BACKEND_ENABLED && (
            <Link
              href={q.trim() ? `/glossary?q=${encodeURIComponent(q.trim())}` : "/glossary"}
              onClick={handleClose}
              className="mb-1 flex items-center gap-3 rounded-2xl bg-surface-muted px-3 py-3 transition hover:bg-border-subtle"
            >
              <Book className="h-4 w-4 shrink-0 text-brand" />
              <span className="min-w-0 flex-1 truncate text-sm font-bold text-fg">
                {q.trim() ? `용어 사전에서 "${q.trim()}" 찾기` : "용어 사전으로 이동"}
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-fg-subtle" />
            </Link>
          )}
          {!q && (
            <p className="px-4 py-6 text-center text-sm font-semibold text-fg-subtle">
              국내 종목 2,700개 이상과 주요 미국 종목을 찾을 수 있어요.
            </p>
          )}
          {q && results.length === 0 && (
            <p className="px-4 py-6 text-center text-sm font-semibold text-fg-muted">
              검색 결과가 없어요
            </p>
          )}
          {results.map((r) => (
            <Link
              key={`${r.code}-${r.name}`}
              href={`/stock/${encodeURIComponent(r.code)}?name=${encodeURIComponent(r.name)}`}
              onClick={handleClose}
              className="flex items-center justify-between gap-3 rounded-2xl px-3 py-3 transition hover:bg-surface-muted"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-fg">
                  {r.name}
                </p>
                <p className="mt-0.5 text-xs font-bold tabular-nums text-fg-subtle">
                  {r.code}
                  {r.market && (
                    <span className="ml-1.5 font-semibold text-fg-subtle">
                      · {r.market}
                    </span>
                  )}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

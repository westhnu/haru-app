"use client";

import { useState } from "react";
import type { PricePoint } from "@/lib/stocktypes";

/** 인터랙티브 SVG 영역 차트. 마우스/터치 호버 시 날짜·가격 툴팁 + 크로스헤어.
 *  상승=빨강, 하락=파랑(국내 관례). */
export default function PriceChart({
  prices,
  up,
}: {
  prices: PricePoint[];
  up: boolean;
}) {
  const W = 440;
  const H = 180;
  const PAD = 6;
  const [idx, setIdx] = useState<number | null>(null);

  if (prices.length < 2) {
    return (
      <div className="flex h-[180px] items-center justify-center text-[13px] font-semibold text-slate-400 dark:text-slate-500">
        표시할 시세가 없어요
      </div>
    );
  }

  const vals = prices.map((p) => p.close);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const n = prices.length;

  const x = (i: number) => PAD + (i / (n - 1)) * (W - PAD * 2);
  const y = (v: number) => PAD + (1 - (v - min) / span) * (H - PAD * 2);

  const line = prices.map((p, i) => `${x(i)},${y(p.close)}`).join(" ");
  const area = `${PAD},${H - PAD} ${line} ${W - PAD},${H - PAD}`;

  const color = up ? "#e11d48" : "#2563eb";
  const gid = up ? "gUp" : "gDown";

  const fmtDate = (d: string) => d.slice(5).replace("-", ".");
  const handle = (clientX: number, rect: DOMRect) => {
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    setIdx(Math.round(ratio * (n - 1)));
  };

  const active = idx !== null ? prices[idx] : null;
  const activePct = idx !== null ? (x(idx) / W) * 100 : 0;

  return (
    <div className="select-none">
      <div
        className="relative"
        onMouseMove={(e) =>
          handle(e.clientX, e.currentTarget.getBoundingClientRect())
        }
        onMouseLeave={() => setIdx(null)}
        onTouchStart={(e) =>
          handle(e.touches[0].clientX, e.currentTarget.getBoundingClientRect())
        }
        onTouchMove={(e) =>
          handle(e.touches[0].clientX, e.currentTarget.getBoundingClientRect())
        }
        onTouchEnd={() => setIdx(null)}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full touch-none"
          preserveAspectRatio="none"
          role="img"
          aria-label="가격 차트"
        >
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.18" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon points={area} fill={`url(#${gid})`} />
          <polyline
            points={line}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {active && idx !== null && (
            <>
              <line
                x1={x(idx)}
                y1={PAD}
                x2={x(idx)}
                y2={H - PAD}
                stroke="#94a3b8"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle cx={x(idx)} cy={y(active.close)} r="3.5" fill={color} />
              <circle
                cx={x(idx)}
                cy={y(active.close)}
                r="7"
                fill={color}
                fillOpacity="0.18"
              />
            </>
          )}
        </svg>

        {active && (
          <div
            className="pointer-events-none absolute -top-1 z-10 -translate-x-1/2 rounded-xl bg-slate-900 px-2.5 py-1.5 text-center shadow-card"
            style={{ left: `${Math.min(85, Math.max(15, activePct))}%` }}
          >
            <div className="text-[10px] font-semibold text-white/60">
              {active.date}
            </div>
            <div className="text-[12px] font-black text-white">
              {active.close.toLocaleString()}원
            </div>
          </div>
        )}
      </div>

      {/* x축 날짜 표기 (시작·중간·끝) */}
      <div className="mt-2 flex items-center justify-between text-[11px] font-semibold text-slate-400 dark:text-slate-500">
        <span>{fmtDate(prices[0].date)}</span>
        <span>{fmtDate(prices[Math.floor((n - 1) / 2)].date)}</span>
        <span>{fmtDate(prices[n - 1].date)}</span>
      </div>
    </div>
  );
}

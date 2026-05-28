"use client";

import { useCallback, useRef, useState } from "react";
import { annotate, type GlossaryEntry } from "@/lib/glossary";

type Align = "left" | "center" | "right";

/** 어려운 용어에 점선 밑줄 + 호버/탭 툴팁으로 뜻을 보여준다.
 *  툴팁이 viewport 를 벗어나지 않도록 단어 위치에 맞춰 정렬을 자동 결정.
 */
export default function GlossaryText({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const segs = annotate(text);
  return (
    <span className={className}>
      {segs.map((s) =>
        s.entry ? (
          <Term key={s.key} word={s.text} entry={s.entry} />
        ) : (
          <span key={s.key}>{s.text}</span>
        )
      )}
    </span>
  );
}

function Term({ word, entry }: { word: string; entry: GlossaryEntry }) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [align, setAlign] = useState<Align>("left");

  // hover/focus 시점에 단어 위치를 재면서 정렬 결정
  // (스크롤·resize 후에도 매번 최신 좌표 사용)
  const measure = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const centerRatio = (rect.left + rect.width / 2) / vw;
    if (centerRatio < 0.33) setAlign("left");
    else if (centerRatio > 0.66) setAlign("right");
    else setAlign("center");
  }, []);

  // 정렬별 absolute 위치 클래스
  const positionCls =
    align === "left"
      ? "left-0"
      : align === "right"
        ? "right-0"
        : "left-1/2 -translate-x-1/2";

  return (
    <span
      className="group relative inline-block"
      onMouseEnter={measure}
      onTouchStart={measure}
    >
      <button
        ref={triggerRef}
        type="button"
        onFocus={measure}
        className="cursor-help border-b border-dashed border-slate-400 font-bold text-slate-900 outline-none"
      >
        {word}
      </button>
      <span
        role="tooltip"
        className={`invisible absolute ${positionCls} top-full z-40 mt-2 w-64 max-w-[calc(100vw-32px)] rounded-2xl border border-slate-200 bg-white p-3.5 text-left opacity-0 shadow-card transition-opacity duration-150 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100`}
      >
        <span className="block text-[13px] font-black text-slate-900">
          {entry.name || word}
          {entry.en && (
            <span className="ml-1 text-[11px] font-medium text-slate-400">
              {entry.en}
            </span>
          )}
        </span>
        <span className="mt-1 block text-[12px] font-medium leading-5 text-slate-600">
          {entry.desc}
        </span>
      </span>
    </span>
  );
}

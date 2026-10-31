"use client";

import { useCallback, useRef, useState } from "react";
import { annotate, type GlossaryEntry } from "@/lib/glossary";
import TermDetailDialog from "@/components/TermDetailDialog";

type Align = "left" | "center" | "right";

/** 어려운 용어에 점선 밑줄 + 호버/탭 툴팁으로 뜻을 보여준다.
 *  툴팁이 viewport 를 벗어나지 않도록 단어 위치에 맞춰 정렬을 자동 결정.
 *  showAiDetail(기본 false)을 켜면 툴팁 안에 "자세히" 버튼이 생기고, 누르면
 *  Bedrock KB RAG 답변을 바텀시트(TermDetailDialog)로 보여준다.
 */
export default function GlossaryText({
  text,
  className,
  showAiDetail = false,
}: {
  text: string;
  className?: string;
  showAiDetail?: boolean;
}) {
  const segs = annotate(text);
  return (
    <span className={className}>
      {segs.map((s) =>
        s.entry ? (
          <Term key={s.key} word={s.text} entry={s.entry} showAiDetail={showAiDetail} />
        ) : (
          <span key={s.key}>{s.text}</span>
        )
      )}
    </span>
  );
}

function Term({
  word,
  entry,
  showAiDetail,
}: {
  word: string;
  entry: GlossaryEntry;
  showAiDetail: boolean;
}) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [align, setAlign] = useState<Align>("left");
  const [dialogOpen, setDialogOpen] = useState(false);
  const closeDialog = useCallback(() => setDialogOpen(false), []);

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
  // "자세히" 버튼까지 마우스를 옮길 때 단어와 툴팁 사이 간격(mt-2)에서 hover가 끊기지 않도록
  // 투명 다리를 깐다. showAiDetail일 때만 적용해 기존 화면의 동작은 그대로 둔다.
  const bridgeCls = showAiDetail
    ? "before:absolute before:-top-2 before:left-0 before:right-0 before:h-2 before:content-['']"
    : "";

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
        className="cursor-help border-b border-dashed border-slate-400 font-bold text-slate-900 dark:text-slate-100 outline-none"
      >
        {word}
      </button>
      <span
        role="tooltip"
        className={`invisible absolute ${positionCls} ${bridgeCls} top-full z-40 mt-2 w-64 max-w-[calc(100vw-32px)] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 text-left opacity-0 shadow-card transition-opacity duration-150 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100`}
      >
        <span className="block text-[14px] font-black text-slate-900 dark:text-slate-100">
          {entry.name || word}
          {entry.en && (
            <span className="ml-1 text-[11px] font-medium tabular-nums text-slate-400 dark:text-slate-500">
              {entry.en}
            </span>
          )}
        </span>
        <span className="mt-1.5 block text-[13px] font-medium leading-[1.7] text-slate-700 dark:text-slate-300">
          {entry.desc}
        </span>
        {showAiDetail && (
          <button
            type="button"
            onClick={(e) => {
              // 툴팁·카드의 다른 클릭 핸들러로 번지지 않게 막는다.
              e.preventDefault();
              e.stopPropagation();
              // 포커스를 풀어 group-focus-within 툴팁이 시트 뒤에 남지 않게 한다.
              e.currentTarget.blur();
              setDialogOpen(true);
            }}
            className="mt-2.5 inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-[12px] font-bold text-blue-700 transition hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
          >
            자세히
          </button>
        )}
      </span>
      {showAiDetail && (
        <TermDetailDialog term={word} open={dialogOpen} onClose={closeDialog} />
      )}
    </span>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 페이지 최상단에서 아래로 당기면 onRefresh 를 호출하는 모바일 풀-투-리프레시.
 *
 * - window.scrollY === 0 일 때만 시작 (스크롤 중간에 잘못 트리거 방지)
 * - 60 px 이상 당겨야 트리거
 * - 진행률(0~1)을 반환해 UI 가 인디케이터를 표시할 수 있음
 */
export function usePullToRefresh(onRefresh: () => void | Promise<void>) {
  const startY = useRef<number | null>(null);
  const [progress, setProgress] = useState(0); // 0~1+
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const THRESHOLD = 60; // px
    const MAX = 120;

    const onTouchStart = (e: TouchEvent) => {
      if (window.scrollY > 0) return;
      startY.current = e.touches[0].clientY;
    };
    const onTouchMove = (e: TouchEvent) => {
      if (startY.current == null) return;
      const dy = e.touches[0].clientY - startY.current;
      if (dy <= 0) {
        setProgress(0);
        return;
      }
      // 저항감 — sqrt 로 점점 완만
      const pulled = Math.min(MAX, Math.sqrt(dy) * 9);
      setProgress(pulled / THRESHOLD);
    };
    const onTouchEnd = async () => {
      if (startY.current == null) {
        setProgress(0);
        return;
      }
      const triggered = progress >= 1;
      startY.current = null;
      setProgress(0);
      if (triggered && !refreshing) {
        setRefreshing(true);
        try {
          await onRefresh();
        } finally {
          setRefreshing(false);
        }
      }
    };

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [onRefresh, progress, refreshing]);

  return { progress, refreshing };
}

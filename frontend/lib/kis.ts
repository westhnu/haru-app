import type { Indicator, IndicatorTone, PricePoint } from "./stocktypes";

// ── 한국투자증권(KIS) Open API 클라이언트 (시세 조회) ──────────────
// 시세·차트 조회는 실전 도메인 + 실전(PROD) 키로 호출한다.
// (모의투자 vps 환경에서도 조회는 실전 키를 쓰는 것이 KIS 권장 패턴)

const REAL = "https://openapi.koreainvestment.com:9443";
const VTS = "https://openapivts.koreainvestment.com:29443";

function appKey(): string {
  return (process.env.KIS_APP_KEY_PROD || process.env.KIS_APP_KEY || "").trim();
}
function appSecret(): string {
  return (
    process.env.KIS_APP_SECRET_PROD ||
    process.env.KIS_APP_SECRET ||
    ""
  ).trim();
}
function baseUrl(): string {
  // PROD 키가 있으면 실전 도메인, 없으면 KIS_ENV 따름
  if (process.env.KIS_APP_KEY_PROD) return REAL;
  return process.env.KIS_ENV === "prod" ? REAL : VTS;
}

export function kisConfigured(): boolean {
  return !!appKey() && !!appSecret();
}

// ── 토큰 캐시 (모듈 메모리) ──
let cachedToken: { token: string; expiresAt: number } | null = null;

async function getToken(): Promise<string | null> {
  if (cachedToken && cachedToken.expiresAt > Date.now() + 60_000) {
    return cachedToken.token;
  }
  const res = await fetch(`${baseUrl()}/oauth2/tokenP`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      grant_type: "client_credentials",
      appkey: appKey(),
      appsecret: appSecret(),
    }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`KIS 토큰 발급 실패 (${res.status})`);
  const data = (await res.json()) as {
    access_token?: string;
    expires_in?: number;
  };
  if (!data.access_token) throw new Error("KIS 토큰 응답 비정상");
  cachedToken = {
    token: data.access_token,
    expiresAt: Date.now() + (data.expires_in ?? 86400) * 1000,
  };
  return cachedToken.token;
}

function headers(token: string, trId: string): Record<string, string> {
  return {
    "content-type": "application/json; charset=utf-8",
    authorization: `Bearer ${token}`,
    appkey: appKey(),
    appsecret: appSecret(),
    tr_id: trId,
    custtype: "P",
  };
}

const num = (v: unknown): number => {
  const n = Number(String(v ?? "").replace(/,/g, ""));
  return Number.isFinite(n) ? n : 0;
};

export interface KisQuote {
  price: number;
  changePct: number;
  per: number;
  pbr: number;
  eps: number;
  bps: number;
  marketCapEok: number; // 시가총액(억원)
  volume: number; // 누적 거래량
  w52High: number;
  w52Low: number;
  name?: string;
}

/** 현재가·기본지표 (inquire-price, FHKST01010100) */
export async function kisQuote(code: string): Promise<KisQuote | null> {
  const token = await getToken();
  if (!token) return null;
  const url =
    `${baseUrl()}/uapi/domestic-stock/v1/quotations/inquire-price` +
    `?fid_cond_mrkt_div_code=J&fid_input_iscd=${encodeURIComponent(code)}`;
  const res = await fetch(url, {
    headers: headers(token, "FHKST01010100"),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`KIS 현재가 응답 (${res.status})`);
  const data = (await res.json()) as { rt_cd?: string; output?: Record<string, string> };
  if (data.rt_cd !== "0" || !data.output) return null;
  const o = data.output;
  return {
    price: num(o.stck_prpr),
    changePct: num(o.prdy_ctrt),
    per: num(o.per),
    pbr: num(o.pbr),
    eps: num(o.eps),
    bps: num(o.bps),
    marketCapEok: num(o.hts_avls),
    volume: num(o.acml_vol),
    w52High: num(o.w52_hgpr),
    w52Low: num(o.w52_lwpr),
    name: o.hts_kor_isnm || undefined,
  };
}

function fmtCap(eok: number): string {
  if (!eok) return "—";
  const jo = Math.floor(eok / 10000);
  const r = Math.round(eok % 10000);
  const parts: string[] = [];
  if (jo > 0) parts.push(`${jo.toLocaleString()}조`);
  if (r > 0 || jo > 0) parts.push(`${r.toLocaleString()}억`);
  return parts.join(" ") || `${eok.toLocaleString()}억`;
}

/** 현재가 응답으로 투자 참고 지표 + 양호/보통/주의 평가 생성 */
export function indicatorsFromQuote(q: KisQuote): Indicator[] {
  const perTone: IndicatorTone =
    q.per <= 0 ? "caution" : q.per <= 15 ? "good" : q.per <= 25 ? "neutral" : "caution";
  const pbrTone: IndicatorTone =
    q.pbr <= 0 ? "neutral" : q.pbr <= 1.5 ? "good" : q.pbr <= 3 ? "neutral" : "caution";
  return [
    { label: "시가총액", value: fmtCap(q.marketCapEok), tone: "neutral" },
    {
      label: "PER",
      value: q.per > 0 ? `${q.per}배` : "적자",
      hint: "주가가 이익의 몇 배인지",
      tone: perTone,
      context:
        q.per <= 0
          ? "이익 마이너스(적자)"
          : q.per <= 15
            ? "코스피 평균(10~15배) 이하"
            : q.per <= 25
              ? "평균보다 다소 높음"
              : "고평가 구간",
    },
    {
      label: "PBR",
      value: q.pbr > 0 ? `${q.pbr}배` : "—",
      hint: "주가가 순자산의 몇 배인지",
      tone: pbrTone,
      context:
        q.pbr <= 0
          ? "—"
          : q.pbr <= 1.5
            ? "순자산 대비 부담 적음"
            : q.pbr <= 3
              ? "보통 수준"
              : "고평가 구간",
    },
    { label: "EPS", value: `${q.eps.toLocaleString()}원`, hint: "주당 순이익", tone: "neutral" },
    { label: "BPS", value: `${q.bps.toLocaleString()}원`, hint: "주당 순자산", tone: "neutral" },
    {
      label: "52주 최고/최저",
      value: `${q.w52High.toLocaleString()} / ${q.w52Low.toLocaleString()}`,
      tone: "neutral",
    },
  ];
}

export interface KisSupply {
  date: string;
  foreign: number; // 외국인 순매수 수량 (+순매수/-순매도)
  institution: number; // 기관계
  individual: number; // 개인
}

/** 투자자별 매매동향 (inquire-investor, FHKST01010900) — 최근일 순매수 수량 */
export async function kisInvestor(code: string): Promise<KisSupply | null> {
  const token = await getToken();
  if (!token) return null;
  const url =
    `${baseUrl()}/uapi/domestic-stock/v1/quotations/inquire-investor` +
    `?fid_cond_mrkt_div_code=J&fid_input_iscd=${encodeURIComponent(code)}`;
  const res = await fetch(url, {
    headers: headers(token, "FHKST01010900"),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`KIS 수급 응답 (${res.status})`);
  const data = (await res.json()) as {
    rt_cd?: string;
    output?: {
      stck_bsop_date: string;
      prsn_ntby_qty: string;
      frgn_ntby_qty: string;
      orgn_ntby_qty: string;
    }[];
  };
  if (data.rt_cd !== "0" || !data.output || data.output.length === 0) return null;
  // KIS 는 장중(09:00~15:30 KST)엔 당일 누적치가 0으로 나오는 경우가 있다.
  // output[0]가 0,0,0이면 다음 비영(非零) 행을 fallback으로 사용 → 보통 직전 장 마감일.
  const isZero = (r: { frgn_ntby_qty: string; orgn_ntby_qty: string; prsn_ntby_qty: string }) =>
    num(r.frgn_ntby_qty) === 0 && num(r.orgn_ntby_qty) === 0 && num(r.prsn_ntby_qty) === 0;
  const row = data.output.find((r) => !isZero(r)) ?? data.output[0];
  return {
    date: row.stck_bsop_date
      ? `${row.stck_bsop_date.slice(0, 4)}-${row.stck_bsop_date.slice(4, 6)}-${row.stck_bsop_date.slice(6, 8)}`
      : "",
    foreign: num(row.frgn_ntby_qty),
    institution: num(row.orgn_ntby_qty),
    individual: num(row.prsn_ntby_qty),
  };
}

function ymd(d: Date): string {
  const s = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
  return s.replace(/-/g, "");
}

/** 일봉 시계열 (inquire-daily-itemchartprice, FHKST03010100) */
export async function kisDaily(
  code: string,
  days = 100
): Promise<PricePoint[]> {
  const token = await getToken();
  if (!token) return [];
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - Math.ceil(days * 1.6) - 10); // 주말·휴일 여유
  const url =
    `${baseUrl()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` +
    `?fid_cond_mrkt_div_code=J&fid_input_iscd=${encodeURIComponent(code)}` +
    `&fid_input_date_1=${ymd(start)}&fid_input_date_2=${ymd(end)}` +
    `&fid_period_div_code=D&fid_org_adj_prc=0`;
  const res = await fetch(url, {
    headers: headers(token, "FHKST03010100"),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`KIS 일봉 응답 (${res.status})`);
  const data = (await res.json()) as {
    rt_cd?: string;
    output2?: { stck_bsop_date: string; stck_clpr: string; acml_vol: string }[];
  };
  if (data.rt_cd !== "0" || !data.output2) return [];
  const rows = data.output2
    .filter((r) => r.stck_bsop_date && r.stck_clpr)
    .map((r) => ({
      date: `${r.stck_bsop_date.slice(0, 4)}-${r.stck_bsop_date.slice(4, 6)}-${r.stck_bsop_date.slice(6, 8)}`,
      close: num(r.stck_clpr),
      volume: num(r.acml_vol),
    }))
    .reverse(); // KIS는 최신순 → 과거순으로
  return rows.slice(-days);
}

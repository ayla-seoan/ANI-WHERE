// 가벼운 막대 그래프 (앱 st.bar_chart 를 옮긴 것, 차트 라이브러리 없이 CSS 로 그린다).
// 가로(horizontal) · 세로, 한 계열 또는 여러 계열(나란히, stack=False). 눈금은 0 부터 '보기 좋은' 간격.

export type Series = { name: string; color: string };
export type BarRow = { label: string; values: number[] };

function ticksFor(max: number): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const top = Math.ceil(max / step - 1e-9) * step;
  const out: number[] = [];
  for (let v = 0; v <= top + step / 2; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}
const fmt = (v: number) => (Number.isInteger(v) ? String(v) : String(Math.round(v * 10) / 10));

function Legend({ series }: { series: Series[] }) {
  if (series.length < 2) return null;
  return (
    <div className="ch-legend">
      {series.map((s) => (
        <span key={s.name}>
          <i style={{ background: s.color }} />
          {s.name}
        </span>
      ))}
    </div>
  );
}

/** 가로 막대: 항목 이름은 왼쪽, 막대는 오른쪽으로 */
export function HBar({
  rows,
  series,
  height,
  xLabel,
}: {
  rows: BarRow[];
  series: Series[];
  height?: number;
  xLabel?: string;
}) {
  const max = Math.max(0, ...rows.flatMap((r) => r.values));
  const ticks = ticksFor(max);
  const top = ticks[ticks.length - 1] || 1;
  return (
    <div className="ch ch-h" style={height ? { minHeight: height } : undefined}>
      <div className="ch-hbody">
        {rows.map((r) => (
          <div className="ch-hrow" key={r.label}>
            <div className="ch-hlab">{r.label}</div>
            <div className="ch-htrack">
              {ticks.map((t) => (
                <i className="ch-vgrid" key={t} style={{ left: `${(t / top) * 100}%` }} />
              ))}
              <div className="ch-hbars">
                {r.values.map((v, i) => (
                  <div
                    key={series[i]?.name ?? i}
                    className="ch-hbar"
                    style={{ width: `${(Math.max(0, v) / top) * 100}%`, background: series[i]?.color }}
                    aria-label={`${r.label} ${series[i]?.name ?? ""} ${fmt(v)}`}
                  />
                ))}
              </div>
            </div>
          </div>
        ))}
        <div className="ch-hrow ch-axis">
          <div className="ch-hlab" />
          <div className="ch-htrack ch-xticks">
            {ticks.map((t) => (
              <span key={t} style={{ left: `${(t / top) * 100}%` }}>
                {fmt(t)}
              </span>
            ))}
          </div>
        </div>
        {xLabel && <div className="ch-xlabel">{xLabel}</div>}
      </div>
      <Legend series={series} />
    </div>
  );
}

/** 세로 막대: 항목 이름은 아래 (많으면 세워서) */
export function VBar({ rows, series, height = 200 }: { rows: BarRow[]; series: Series[]; height?: number }) {
  const max = Math.max(0, ...rows.flatMap((r) => r.values));
  const ticks = ticksFor(max);
  const top = ticks[ticks.length - 1] || 1;
  const longest = Math.max(0, ...rows.map((r) => [...r.label].length));
  const crowded = rows.length > 12 || (rows.length > 8 && longest > 5);
  const crowdedM = !crowded && rows.length > 5 && longest > 4; // 좁은 화면에서만 세운다
  const plot = Math.max(80, height - (crowded ? 70 : 34));
  return (
    <div className="ch ch-v">
      <div className="ch-vbody">
        <div className="ch-yticks" style={{ height: plot }}>
          {ticks.map((t) => (
            <span key={t} style={{ bottom: `${(t / top) * 100}%` }}>
              {fmt(t)}
            </span>
          ))}
        </div>
        <div className="ch-vmain">
          <div className="ch-vplot" style={{ height: plot }}>
            {ticks.map((t) => (
              <i className="ch-hgrid" key={t} style={{ bottom: `${(t / top) * 100}%` }} />
            ))}
            {rows.map((r) => (
              <div className="ch-vcol" key={r.label}>
                {r.values.map((v, i) => (
                  <div
                    key={series[i]?.name ?? i}
                    className="ch-vbar"
                    style={{ height: `${(Math.max(0, v) / top) * 100}%`, background: series[i]?.color }}
                    aria-label={`${r.label} ${series[i]?.name ?? ""} ${fmt(v)}`}
                  />
                ))}
              </div>
            ))}
          </div>
          <div className={`ch-xlabs${crowded ? " tilt" : crowdedM ? " tilt-m" : ""}`}>
            {rows.map((r) => (
              <span key={r.label}>{r.label}</span>
            ))}
          </div>
        </div>
      </div>
      <Legend series={series} />
    </div>
  );
}

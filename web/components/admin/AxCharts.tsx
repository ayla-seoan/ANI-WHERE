// 관리자 A안 막대 (README 5절): 위쪽만 4px 둥글게 · 이중 축 없음 · 색만으로 구분하지 않게 범례 + 막대 위 숫자.
// 한 그림 안의 막대는 모두 같은 단위 · 같은 눈금이다 (단위가 다른 숫자는 그림을 나눈다).

export type AxSeries = { name: string; cls: string };
export type AxGroup = { label: string; values: (number | null)[] };

const fmt = (v: number) => (Number.isInteger(v) ? String(v) : String(Math.round(v * 10) / 10));

export function AxLegend({ series }: { series: AxSeries[] }) {
  return (
    <span className="ax-legend">
      {series.map((s) => (
        <span key={s.name}>
          <i className={`ax-sw ${s.cls}`} aria-hidden />
          {s.name}
        </span>
      ))}
    </span>
  );
}

/** 묶음 세로 막대. top 을 주면 그 값이 꼭대기 (예: 100%) */
export function AxGroupBars({
  groups,
  series,
  unit,
  top,
  title,
}: {
  groups: AxGroup[];
  series: AxSeries[];
  unit: string;
  top?: number;
  title: string;
}) {
  const max = top ?? Math.max(1, ...groups.flatMap((g) => g.values.map((v) => v ?? 0)));
  const aria = groups
    .map((g) => `${g.label}: ${g.values.map((v, i) => `${series[i]?.name} ${v === null ? "없음" : fmt(v) + unit}`).join(", ")}`)
    .join(" / ");
  return (
    <figure className="ax-gb" aria-label={title}>
      <figcaption className="ax-card-h">
        <h2>{title}</h2>
        <AxLegend series={series} />
      </figcaption>
      <div className="ax-gb-plot" role="img" aria-label={aria}>
        <span className="ax-gb-y" aria-hidden>
          <span style={{ bottom: "100%" }}>
            {fmt(max)}
            {unit}
          </span>
          <span style={{ bottom: "50%" }}>
            {fmt(max / 2)}
            {unit}
          </span>
          <span style={{ bottom: "0%" }}>0</span>
        </span>
        <span className="ax-gb-grid" aria-hidden>
          <i style={{ bottom: "100%" }} />
          <i style={{ bottom: "50%" }} />
        </span>
        <span className="ax-gb-cols" style={{ gridTemplateColumns: `repeat(${groups.length}, minmax(0, 1fr))` }}>
          {groups.map((g) => (
            <span key={g.label} className="ax-gb-col">
              {g.values.map((v, i) => (
                <span key={i} className="ax-gb-bar">
                  <b>{v === null ? "-" : fmt(v)}</b>
                  <i className={series[i]?.cls} style={{ height: `${v === null ? 0 : Math.min(100, (v / max) * 100)}%` }} />
                </span>
              ))}
            </span>
          ))}
        </span>
      </div>
      <div className="ax-gb-x" style={{ gridTemplateColumns: `repeat(${groups.length}, minmax(0, 1fr))` }} aria-hidden>
        {groups.map((g) => (
          <span key={g.label}>{g.label}</span>
        ))}
      </div>
    </figure>
  );
}

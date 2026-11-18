import { IcError, IcInfo } from "./AdminIcons";

// 앱(Streamlit)의 st.dataframe · st.metric · st.info/warning · st.caption · st.expander 를 옮긴 작은 조각들.

type Cell = string | number | null | undefined;

/** st.dataframe: 표는 상자 안에서만 가로·세로로 스크롤된다 (화면 전체가 옆으로 밀리지 않게) */
export function Table({
  columns,
  rows,
  height,
  numeric = [],
}: {
  columns: string[];
  rows: Record<string, Cell>[];
  height?: number;
  numeric?: string[];
}) {
  return (
    <div className="dt-box" style={height ? { maxHeight: height } : undefined}>
      <table className="dt">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} className={numeric.includes(c) ? "num" : undefined}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => {
                const v = r[c];
                const isNum = typeof v === "number" || numeric.includes(c);
                return (
                  <td key={c} className={isNum ? "num" : undefined}>
                    {v === null ? <span className="dt-none">None</span> : v === undefined ? "" : String(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** st.metric: 이름 · 값 · (변화). color 'inverse' 면 줄어든 것이 초록 */
export function Metric({
  label,
  value,
  delta,
  color = "normal",
  border = false,
}: {
  label: string;
  value: string | number;
  delta?: string | null;
  color?: "normal" | "inverse" | "off";
  border?: boolean;
}) {
  const down = !!delta && delta.trim().startsWith("-");
  const tone = !delta || color === "off" ? "off" : (down ? color === "inverse" : color === "normal") ? "up" : "down";
  return (
    <div className={`mt${border ? " bd" : ""}`}>
      <div className="mt-l">{label}</div>
      <div className="mt-v">{value}</div>
      {delta && (
        <div className={`mt-d ${tone}`}>
          <svg viewBox="0 0 24 24" aria-hidden className={down ? "dn" : undefined}>
            <path d="M12 19V5M5.5 11.5L12 5l6.5 6.5" />
          </svg>
          {delta}
        </div>
      )}
    </div>
  );
}

/** st.info (민트) · st.warning (노랑) */
export function Note({
  kind = "info",
  icon,
  children,
}: {
  kind?: "info" | "warn";
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={`st-note ${kind}`} role={kind === "warn" ? "alert" : undefined}>
      {icon ?? (kind === "warn" ? <IcError /> : <IcInfo />)}
      <div>{children}</div>
    </div>
  );
}

export const Caption = ({ children }: { children: React.ReactNode }) => <p className="st-cap">{children}</p>;

/** st.expander (접힌 상자) */
export function Expander({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="st-exp">
      <summary>{label}</summary>
      <div className="st-exp-body">{children}</div>
    </details>
  );
}

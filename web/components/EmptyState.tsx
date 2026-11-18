import Link from "next/link";
import { AddIcon } from "./Icons";

export default function EmptyState({
  title = "조건에 맞는 팝업이 없어요",
  hint = "검색어나 지역 조건을 줄여 보세요.",
  onReset,
}: {
  title?: string;
  hint?: string;
  onReset?: () => void;
}) {
  return (
    <div className="empty" role="status">
      <h2>{title}</h2>
      <p>
        {hint}
        <br />
        없는 팝업이면 오른쪽 아래 + 로 직접 등록할 수 있어요.
      </p>
      <div className="actions">
        {onReset && (
          <button type="button" className="btn ghost" onClick={onReset}>
            조건 초기화
          </button>
        )}
        <Link className="btn" href="/add">
          <AddIcon />
          직접 등록
        </Link>
      </div>
    </div>
  );
}

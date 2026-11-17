import { APP_URL } from "@/lib/popup";
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
        찾는 팝업이 아직 없다면 앱에서 직접 등록할 수 있어요.
      </p>
      <div className="actions">
        {onReset && (
          <button type="button" className="btn ghost" onClick={onReset}>
            조건 초기화
          </button>
        )}
        <a className="btn" href={APP_URL} target="_blank" rel="noopener noreferrer">
          <AddIcon />
          앱에서 직접 등록
        </a>
      </div>
    </div>
  );
}

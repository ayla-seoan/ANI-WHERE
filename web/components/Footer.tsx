import { APP_URL } from "@/lib/popup";

// 앱(Streamlit) 바닥글과 같은 모양: 가운데 · 작은 회색 글씨. 데이터 출처는 늘 표시한다 (프로젝트 원칙).
export default function Footer({ sourceLabel, note }: { sourceLabel: string; note: string }) {
  const year = new Date().getFullYear();
  return (
    <footer className="aw-foot">
      <div>© {year} ANI:WHERE</div>
      <div>
        운영: ANI:WHERE · {sourceLabel} · 10분마다 새로 고침{note ? ` · ${note}` : ""}
      </div>
      <div className="aw-foot-links">
        <a href={`${APP_URL}/privacy`} target="_blank" rel="noopener noreferrer">
          개인정보처리방침 · 이용약관
        </a>
        <a href={`${APP_URL}/guide`} target="_blank" rel="noopener noreferrer">
          사용자 튜토리얼
        </a>
        <a href={APP_URL} target="_blank" rel="noopener noreferrer">
          리뷰·북마크·등록은 ANI:WHERE 앱에서
        </a>
      </div>
    </footer>
  );
}

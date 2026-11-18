import { APP_URL } from "@/lib/popup";

// 앱 오른쪽 '물어보기' 창 자리. 공개 웹은 읽기 전용이라 AI 대화는 앱(Streamlit)에서 하고, 여기서는 같은 모양의 안내 + 예시만 둔다.
const CHIPS = ["지금 진행 중인 서울 팝업", "곧 끝나는 팝업", "이번 주말 성수 팝업", "팝업 추천해줘"];

export default function AskPanel() {
  return (
    <aside className="ask-panel" aria-label="ANI:WHERE에게 물어보기">
      <div className="ask-title">ANI:WHERE에게 물어보기</div>
      <div className="ask-msg">
        <img src="/icons/icon-192.png" alt="" width={36} height={36} />
        <div>
          <div className="ask-who">ANI:WHERE</div>
          <div className="ask-bubble">
            안녕하세요 궁금하신 팝업에서 찾아 드릴게요!
            <br />
            <b>작품 · 지역 · 날짜</b>로 물어보면 더 정확하게 찾을 수 있어요!
          </div>
        </div>
      </div>
      <div className="ask-foot">
        <div className="ask-chips">
          {CHIPS.map((c) => (
            <a key={c} href={`${APP_URL}/ask`} target="_blank" rel="noopener noreferrer" className="ask-chip">
              {c}
            </a>
          ))}
        </div>
        <a href={`${APP_URL}/ask`} target="_blank" rel="noopener noreferrer" className="ask-go">
          ANI:WHERE 앱에서 물어보기
        </a>
      </div>
    </aside>
  );
}

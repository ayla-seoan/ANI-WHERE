import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "오프라인", robots: { index: false } };
export const dynamic = "force-static";

// 서비스 워커가 미리 저장해 두었다가, 인터넷이 끊기고 그 화면이 저장돼 있지 않을 때 대신 보여 준다.
export default function Offline() {
  return (
    <div className="center-box">
      <img src="/icons/icon-192.png" alt="" width={96} height={96} />
      <h1>인터넷에 연결되어 있지 않아요</h1>
      <p>
        한 번 열어 본 팝업은 연결 없이도 다시 볼 수 있어요.
        <br />
        연결되면 다시 시도해 주세요.
      </p>
      <div className="actions">
        <Link className="btn" href="/">
          처음 화면 다시 열기
        </Link>
      </div>
    </div>
  );
}

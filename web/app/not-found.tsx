import Link from "next/link";

export default function NotFound() {
  return (
    <div className="center-box">
      <img src="/icons/icon-192.png" alt="" width={96} height={96} />
      <h1>찾는 팝업이 없어요</h1>
      <p>
        끝나서 내려갔거나 주소가 바뀌었을 수 있어요.
        <br />
        목록에서 다시 찾아보거나, 없는 팝업이면 직접 등록해 주세요.
      </p>
      <div className="actions">
        <Link className="btn" href="/">
          팝업 찾기
        </Link>
        <Link className="btn ghost" href="/add">
          등록하기
        </Link>
      </div>
    </div>
  );
}

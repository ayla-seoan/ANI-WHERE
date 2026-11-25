// 홈 A안 섹션 제목 줄: 왼쪽 포인트색 아이콘 + 제목(19px/800, 모바일 17px), 오른쪽에 칩 · 링크 (children)
export default function SecHead({
  id,
  title,
  icon,
  help,
  children,
}: {
  id: string;
  title: string;
  icon: React.ReactNode;
  help?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="ah-hh">
      <h2 className="ah-h" id={id}>
        {icon}
        {title}
        {help}
      </h2>
      {children}
    </div>
  );
}

// 아주 작은 마크다운 → HTML 변환 (개인정보처리방침 · 디자인 시스템 문서용). 새 의존성을 들이지 않으려고 직접 둔다.
// 문서는 저장소 안의 우리 파일(docs/*.md)뿐이라, 쓰는 문법만 다룬다:
//   # 제목 · 문단 · **굵게** · `코드` · [글](주소) · - 목록 · 1. 목록 · > 인용 · --- · | 표 |
// 글자는 모두 HTML 이스케이프한다 (문서 속 <b> 같은 태그는 그대로 글자로 보인다 — Streamlit st.markdown 기본과 같게).

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function inline(src: string): string {
  // `코드` 는 먼저 떼어 두고 나머지만 꾸민다
  return src
    .split(/(`[^`]+`)/)
    .map((part) => {
      if (/^`[^`]+`$/.test(part)) return `<code>${esc(part.slice(1, -1))}</code>`;
      let t = esc(part);
      t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|\.?\/[^)\s]*|#[^)\s]*)\)/g, '<a href="$2">$1</a>');
      return t;
    })
    .join("");
}

function cells(line: string): string[] {
  const t = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return t.split("|").map((c) => c.trim());
}

const isSep = (l: string) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(l);

export function markdown(src: string): string {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      const n = h[1].length;
      out.push(`<h${n}>${inline(h[2].trim())}</h${n}>`);
      i++;
      continue;
    }
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      out.push("<hr>");
      i++;
      continue;
    }
    if (line.trim().startsWith("|") && i + 1 < lines.length && isSep(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const body: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) body.push(cells(lines[i++]));
      const th = head.some(Boolean) ? `<thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead>` : "";
      const tb = body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("");
      out.push(`<div class="md-table"><table>${th}<tbody>${tb}</tbody></table></div>`);
      continue;
    }
    if (line.startsWith(">")) {
      const buf: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${markdown(buf.join("\n"))}</blockquote>`);
      continue;
    }
    const ul = /^\s*[-*]\s+/;
    const ol = /^\s*\d+\.\s+/;
    if (ul.test(line) || ol.test(line)) {
      const ordered = ol.test(line);
      const re = ordered ? ol : ul;
      const items: string[] = [];
      while (i < lines.length && lines[i].trim()) {
        const l = lines[i];
        if (re.test(l)) items.push(l.replace(re, ""));
        else if (items.length && !/^(#|\||>)/.test(l.trim())) items[items.length - 1] += " " + l.trim(); // 이어지는 줄
        else break;
        i++;
      }
      const tag = ordered ? "ol" : "ul";
      out.push(`<${tag}>${items.map((t) => `<li>${inline(t)}</li>`).join("")}</${tag}>`);
      continue;
    }
    // 문단: 빈 줄이나 다른 블록이 나올 때까지
    const buf: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,6}\s|>|\s*[-*]\s+|\s*\d+\.\s+|\s*-{3,}\s*$)/.test(lines[i]) &&
      !(lines[i].trim().startsWith("|") && i + 1 < lines.length && isSep(lines[i + 1]))
    )
      buf.push(lines[i++].trim());
    if (buf.length) out.push(`<p>${inline(buf.join(" "))}</p>`);
    else i++;
  }
  return out.join("\n");
}

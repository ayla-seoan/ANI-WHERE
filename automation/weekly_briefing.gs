/**
 * ANI:WHERE 주간 팝업 브리핑 (Google Apps Script)
 *
 * 매주 월요일 11:00 (Notion 가져오기 10:00 이 끝난 뒤) GitHub 의 data/cafes.json 을 읽어
 *   - 이번 주에 시작하는 팝업
 *   - 이번 주에 끝나는 팝업 (놓치기 전에)
 *   - 정보가 비어 '확인 필요' 인 팝업 (운영자가 고칠 것)
 * 을 정리해 **스크립트 주인 본인에게만** 메일로 보내고, 같은 내용을 시트에 한 줄씩 쌓는다.
 *
 * 왜 본인에게만? 앱은 이메일을 저장하지 않는다 (CLAUDE.md 민감정보 규칙).
 * 받는 사람 주소를 어디에도 적지 않고 Session.getEffectiveUser() 로 그때그때 읽는다.
 *
 * 사실 확인 단계: 메일 내용은 데이터에 있는 값만 쓴다. 빈 값은 지어내지 않고 '확인 필요' 로 따로 모은다.
 * 설치 방법은 automation/README.md.
 */

const DATA_URL = 'https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/data/cafes.json';
const APP_URL = 'https://ani-where.streamlit.app';
const SHEET_NAME = '주간 브리핑 기록';
const TZ = 'Asia/Seoul';

/** 트리거가 부르는 함수 */
function weeklyBriefing() {
  const rows = fetchRows_();
  const popups = latestRows_(rows);
  const today = todayKst_();
  const weekEnd = addDays_(today, 6);

  const starting = popups.filter(p => p.start && p.start >= today && p.start <= weekEnd);
  const ending = popups.filter(p => p.end && p.end >= today && p.end <= weekEnd);
  const missing = popups.filter(p => p.end && p.end >= today && p.missing.length);

  const subject = `[ANI:WHERE] ${fmt_(today)} 주간 팝업 브리핑 — 시작 ${starting.length} · 마감 ${ending.length}`;
  const html = render_(today, weekEnd, starting, ending, missing);

  const me = Session.getEffectiveUser().getEmail();   // 저장하지 않고 실행할 때만 읽는다
  if (!me) throw new Error('받는 사람(스크립트 주인)을 알 수 없습니다. 권한을 다시 승인해 주세요.');
  MailApp.sendEmail({ to: me, subject: subject, htmlBody: html });
  log_(today, starting.length, ending.length, missing.length, popups.length);
}

/** 처음 한 번: 매주 월요일 11시 트리거 만들기 (이미 있으면 다시 만들지 않는다) */
function installTrigger() {
  const exists = ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === 'weeklyBriefing');
  if (exists) return;
  ScriptApp.newTrigger('weeklyBriefing').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(11)
    .inTimezone(TZ).create();
}

// ---------------------------------------------------------------- 데이터
function fetchRows_() {
  const res = UrlFetchApp.fetch(DATA_URL, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error(`데이터를 못 읽었습니다 (HTTP ${res.getResponseCode()}). 저장소가 공개인지 확인하세요.`);
  }
  const rows = JSON.parse(res.getContentText('UTF-8'));
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('데이터가 비어 있습니다.');
  return rows;
}

/** append-only 저장소: entry_id 별 가장 큰 revision 이 지금 상태. 삭제·종료로 내린 것은 뺀다 */
function latestRows_(rows) {
  const latest = {};
  rows.forEach(r => {
    const id = String(r.entry_id);
    if (!latest[id] || Number(r.revision) >= Number(latest[id].revision)) latest[id] = r;
  });
  return Object.values(latest)
    .filter(r => r.status !== 'deleted')
    .map(r => ({
      id: String(r.entry_id),
      work: String(r.work || '').trim(),
      name: String(r.cafe_name || '').trim(),
      address: String(r.address || '').trim(),
      start: parseDay_(r.start_date),
      end: parseDay_(r.end_date),
      missing: ['start_date', 'end_date', 'address', 'links', 'images']
        .filter(k => !String(r[k] || '').trim())
        .map(k => ({ start_date: '시작일', end_date: '종료일', address: '주소', links: '참고 링크', images: '포스터' })[k]),
    }));
}

// ---------------------------------------------------------------- 메일
function render_(today, weekEnd, starting, ending, missing) {
  const item = p => `<li><b>${esc_(p.work || '작품 미상')}</b> · ${esc_(p.name)} ` +
    `<span style="color:#6B7672">(${p.start ? fmt_(p.start) : '?'} ~ ${p.end ? fmt_(p.end) : '?'}, ${esc_(area_(p.address))})</span></li>`;
  const block = (title, list, empty) => `<h3 style="margin:18px 0 6px">${title} (${list.length})</h3>` +
    (list.length ? `<ul>${list.slice(0, 20).map(item).join('')}</ul>` +
      (list.length > 20 ? `<p>…외 ${list.length - 20}곳은 앱에서 확인하세요.</p>` : '') : `<p style="color:#6B7672">${empty}</p>`);
  const fix = missing.slice(0, 15).map(p => `<li>${esc_(p.work)} · ${esc_(p.name)} — 비어 있음: ${p.missing.join(', ')}</li>`).join('');
  return `<div style="font-family:sans-serif;line-height:1.6;color:#26302D">
    <h2 style="color:#2E9C82">ANI:WHERE 주간 팝업 브리핑</h2>
    <p>${fmt_(today)} ~ ${fmt_(weekEnd)}</p>
    ${block('이번 주 시작', starting, '이번 주에 새로 시작하는 팝업이 없어요.')}
    ${block('이번 주 마감 — 놓치지 마세요', ending, '이번 주에 끝나는 팝업이 없어요.')}
    <h3 style="margin:18px 0 6px">확인 필요 (${missing.length})</h3>
    ${missing.length ? `<ul>${fix}</ul>` : '<p style="color:#6B7672">빠진 정보가 없어요.</p>'}
    <p><a href="${APP_URL}">앱에서 지도로 보기</a></p>
    <p style="color:#9AA5A1;font-size:12px">이 메일은 앱 데이터에 있는 값만으로 만들었습니다. 날짜·장소는 공식 공지에서 한 번 더 확인하세요.</p>
  </div>`;
}

function log_(today, starting, ending, missing, total) {
  const ss = SpreadsheetApp.getActiveSpreadsheet() || null;
  if (!ss) return;            // 시트에 붙이지 않은 단독 스크립트면 기록은 건너뛴다
  const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) sheet.appendRow(['보낸 날', '시작', '마감', '확인 필요', '진행·예정 팝업']);
  sheet.appendRow([fmt_(today), starting, ending, missing, total]);
}

// ---------------------------------------------------------------- 도우미
function todayKst_() { return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd'); }
function parseDay_(v) { const s = String(v || '').slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ''; }
function addDays_(day, n) {
  const d = new Date(day + 'T00:00:00+09:00'); d.setDate(d.getDate() + n);
  return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
}
function fmt_(day) { return day.slice(5).replace('-', '/'); }
function area_(addr) { return (addr || '').split(/\s+/).slice(0, 2).join(' ') || '지역 미상'; }
function esc_(s) { return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]); }

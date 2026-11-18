/**
 * ANI:WHERE 사용해 보기 설문 (구글 폼) — 참여자가 직접 ANI:WHERE 를 써 보고 스스로 내는 설문 (11/18 다시 설계).
 * 폼은 두 개: 1차(로그인 · 물어보기 없던 첫 버전) · 2차(지금 버전). 질문 1~4 는 같아서 1차 → 2차 를 바로 비교한다.
 *
 * 쓰는 법: https://script.google.com → 프로젝트 → 이 파일 내용을 통째로 붙여넣기 → 저장
 *        → 함수 rebuildSurveyForm ▶ 실행 (2차 폼) · buildV1SurveyForm ▶ 실행 (1차 폼) → '실행 로그' 의 주소를 확인.
 *
 * 응답은 한 스프레드시트에 모은다: 2차 = '설문지 응답 시트1' 탭, 1차 = '1차 응답' 탭. n8n 이 둘 다 읽어 '정리' 탭에 버전과 함께 쌓는다.
 *   - rebuildSurveyForm: 지금 있는 2차 폼(FORM_ID)의 문항 · 응답을 지우고 새로 만든다 (폼 · 시트 주소는 그대로). '정리' 탭도 비운다
 *   - buildV1SurveyForm: 1차 폼을 처음엔 새로 만들고(번호를 스크립트 속성 V1_FORM_ID 에 기억), 다음부터는 같은 폼을 다시 만든다
 *
 * 설계 (A/B): A = 참여자가 평소 쓰던 방법(SNS · 커뮤니티 · 검색), B = ANI:WHERE (1차 / 2차).
 *   같은 사람이 평소 방법으로 걸리던 시간과 ANI:WHERE 로 직접 해 본 시간 · 성공 여부 · 어려움을 답한다.
 *   '평소 불편한 점' 문항은 문제 정의의 근거로 쓴다.
 * 개인정보: 이메일을 모으지 않는다. 받는 것은 ANI:WHERE 닉네임(응답을 묶는 데만)과 답뿐. 이름 · 연락처 문항 없음.
 */
var FORM_ID = '1P1TZjlF-YR-80fa4s2-ABUFRJfiSU0b4aQo_raosceg';     // 2차 폼
var SHEET_ID = '1OHB1_wSWowI-lVi-AOWXICUz-wH32Y1uG9YH_McnkrA';    // 응답 시트 (1차 · 2차 같이)
var TAB = { '2차': '설문지 응답 시트1', '1차': '1차 응답' };        // n8n '폼 응답 들어옴' 노드들이 읽는 탭 이름

var TASKS = {
  '2차': [
    ['질문 1', '이번 주말 서울에서 열리는 팝업 하나를 찾아 자세히 보기(상세 화면)를 열어 보세요.'],
    ['질문 2', '보고 싶은 작품의 팝업을 찾아 북마크해 보세요. (로그인이 필요해요)'],
    ['질문 3', '방금 북마크한 팝업이 "내 캘린더"에 들어갔는지 확인해 보세요.'],
    ['질문 4', '그 팝업에 가기 전에 확인할 공식 공지(참고 웹사이트)를 열어 보세요.']
  ],
  '1차': [
    ['질문 1', '이번 주말 서울에서 열리는 팝업 하나를 찾아 자세히 보기(상세 화면)를 열어 보세요.'],
    ['질문 2', '보고 싶은 작품의 팝업을 찾아 팔로우(북마크)해 보세요. (1차는 로그인 없이 돼요)'],
    ['질문 3', '방금 팔로우한 팝업이 "내 캘린더"(지도보기 오른쪽)에 들어갔는지 확인해 보세요.'],
    ['질문 4', '그 팝업에 가기 전에 확인할 공식 공지(참고 웹사이트)를 열어 보세요.']
  ]
};
var TIDY_HEADER = ['닉네임', '버전', '과제', '결과', '걸린시간초', '막힌 지점', '방문빈도', '정보출처', '불편한점',
                   '평소걸린시간초', '비교', '만족도', '다시쓸의향', '바라는점', '받은시각'];

/** 2차 폼 (지금 버전) 다시 만들기 */
function rebuildSurveyForm() {
  var form = FormApp.openById(FORM_ID);
  var ss = SpreadsheetApp.openById(SHEET_ID);
  resetForm_(form, ss, TAB['2차']);
  fillForm_(form, '2차');
  linkForm_(form, ss, TAB['2차']);
  var tidy = ss.getSheetByName('정리') || ss.insertSheet('정리');
  tidy.clear();
  tidy.getRange(1, 1, 1, TIDY_HEADER.length).setValues([TIDY_HEADER]).setFontWeight('bold');
  tidy.setFrozenRows(1);
  logUrls_('2차', form, ss);
}

/** 1차 폼 (로그인 · 물어보기 없던 첫 버전) 만들기 / 다시 만들기 */
function buildV1SurveyForm() {
  var props = PropertiesService.getScriptProperties();
  var form = null;
  var id = props.getProperty('V1_FORM_ID');
  if (id) { try { form = FormApp.openById(id); } catch (e) { form = null; } }
  if (!form) {
    form = FormApp.create('ANI:WHERE 사용해 보기 설문 — 1차');
    props.setProperty('V1_FORM_ID', form.getId());
  }
  var ss = SpreadsheetApp.openById(SHEET_ID);
  resetForm_(form, ss, TAB['1차']);
  fillForm_(form, '1차');
  linkForm_(form, ss, TAB['1차']);
  logUrls_('1차', form, ss);
}

function resetForm_(form, ss, tabName) {
  form.getItems().forEach(function (it) { form.deleteItem(it); });
  form.deleteAllResponses();
  try { if (form.getDestinationId()) form.removeDestination(); } catch (e) {}
  var old = ss.getSheetByName(tabName);
  if (old && ss.getSheets().length > 1) ss.deleteSheet(old);
}

function fillForm_(form, ver) {
  var v1 = ver === '1차';
  form.setTitle('ANI:WHERE 사용해 보기 설문 — ' + ver + ' (5분)');
  form.setDescription(v1
    ? '애니 팝업 · 콜라보 카페를 찾는 ANI:WHERE 의 1차 버전을 직접 써 보고 답해 주세요.\n' +
      '1차 버전에는 로그인과 물어보기(AI 대화창)가 없어요. 리스트 · 필터 · 지도 · 팔로우 · 내 캘린더만 써 주세요.\n\n' +
      '이름 · 연락처 · 이메일은 받지 않아요. 닉네임은 1차 · 2차 응답을 묶는 데만 쓰고, 결과는 서비스를 고치는 데만 써요.'
    : '애니 팝업 · 콜라보 카페 · 굿즈 행사를 찾는 ANI:WHERE 를 직접 써 보고 답해 주세요.\n' +
      '주소: https://ani-where.streamlit.app (로그인 · 물어보기 · 홈 추천 모두 써도 돼요)\n\n' +
      '이름 · 연락처 · 이메일은 받지 않아요. ANI:WHERE 닉네임은 응답을 정리하는 데만 쓰고, 결과는 서비스를 고치는 데만 써요.');
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setProgressBar(true);

  // 1. 나에 대해
  form.addTextItem().setTitle('닉네임').setRequired(true).setHelpText(v1
    ? '1차에는 로그인이 없어요. 2차(지금 ANI:WHERE)에서 로그인할 때 쓰는 닉네임을 적어 주세요 (1차 · 2차 응답을 묶어요)'
    : 'ANI:WHERE 에 가입한 닉네임 (가입 전이면 지금 가입하고 그 닉네임을 적어 주세요)');
  form.addMultipleChoiceItem().setTitle('방문 빈도').setRequired(true)
    .setHelpText('애니 팝업 · 콜라보 카페에 얼마나 자주 가나요?')
    .setChoiceValues(['한 달에 2번 이상', '한 달에 1번쯤', '몇 달에 1번', '거의 안 가요']);

  // 2. 평소에는 (A · 문제 정의)
  form.addPageBreakItem().setTitle('평소에는 어떻게 찾나요?').setHelpText('ANI:WHERE 를 쓰기 전, 평소 방법을 떠올려 주세요.');
  form.addCheckboxItem().setTitle('정보 출처').setHelpText('평소 팝업 정보를 어디서 찾나요? (여러 개 골라도 돼요)')
    .setChoiceValues(['X(트위터)', '인스타그램', '디시인사이드 · 커뮤니티', '네이버 블로그 · 검색', '팝업 모음 사이트 · 앱', '친구 · 지인'])
    .showOtherOption(true);
  form.addCheckboxItem().setTitle('불편한 점').setHelpText('팝업을 찾을 때 불편했던 점을 모두 골라 주세요')
    .setChoiceValues(['정보가 여러 곳에 흩어져 있어요', '기간 · 장소가 정확하지 않아요', '끝난 걸 늦게 알아요',
                      '내 주변 팝업을 찾기 어려워요', '특전 · 굿즈 정보가 부족해요', '가기 전에 공식 공지를 찾기 어려워요'])
    .showOtherOption(true);
  form.addMultipleChoiceItem().setTitle('평소 걸린 시간').setRequired(true)
    .setHelpText('평소 방법으로 "이번 주말 서울에서 열리는 팝업 하나" 를 찾으면 보통 얼마나 걸리나요?')
    .setChoiceValues(['1분 안에', '1~3분', '3~5분', '5~10분', '10분 넘게']);

  // 3. ANI:WHERE 로 해 보기 (B)
  TASKS[ver].forEach(function (t) {
    form.addPageBreakItem().setTitle(t[0] + '. ' + t[1])
      .setHelpText(v1 ? 'ANI:WHERE 1차 버전에서 직접 해 보고 답해 주세요.' : 'ANI:WHERE 에서 직접 해 보고 답해 주세요.');
    form.addMultipleChoiceItem().setTitle(t[0] + ' 결과').setRequired(true)
      .setChoiceValues(['해냈어요', '어렵게 해냈어요', '못 했어요']);
    form.addMultipleChoiceItem().setTitle(t[0] + ' 걸린 시간')
      .setChoiceValues(['30초 안에', '30초~1분', '1~2분', '2~3분', '3분 넘게']);
    form.addTextItem().setTitle(t[0] + ' 막힌 곳').setHelpText('헷갈리거나 막힌 곳이 있었다면 적어 주세요 (없으면 비워 두세요)');
  });

  // 4. 마무리
  form.addPageBreakItem().setTitle('마지막으로');
  form.addScaleItem().setTitle('비교').setHelpText('평소 방법과 비교하면 ANI:WHERE ' + (v1 ? '1차 버전' : '') + '는 어땠나요?')
    .setBounds(1, 5).setLabels('훨씬 불편했어요', '훨씬 편했어요').setRequired(true);
  form.addScaleItem().setTitle('만족도').setBounds(1, 5).setLabels('불만족', '아주 만족').setRequired(true);
  form.addMultipleChoiceItem().setTitle('다시 쓸 의향').setChoiceValues(['있어요', '모르겠어요', '없어요']).setRequired(true);
  form.addParagraphTextItem().setTitle('바라는 점').setHelpText('있었으면 하는 기능이나 고칠 점을 자유롭게 적어 주세요');
}

/** 폼 → 응답 시트 연결 + 새로 생긴 응답 탭 이름 맞추기 */
function linkForm_(form, ss, tabName) {
  var before = ss.getSheets().map(function (sh) { return sh.getSheetId(); });
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  ss = SpreadsheetApp.openById(ss.getId());
  var added = ss.getSheets().filter(function (sh) { return before.indexOf(sh.getSheetId()) < 0; });
  if (added.length) added[0].setName(tabName);
}

function logUrls_(ver, form, ss) {
  Logger.log(ver + ' ① 폼 고치기: ' + form.getEditUrl());
  Logger.log(ver + ' ② 폼 내기(참여자에게 보낼 주소): ' + form.getPublishedUrl());
  Logger.log(ver + ' ③ 응답 시트: ' + ss.getUrl());
}

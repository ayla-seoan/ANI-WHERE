/**
 * ANI:WHERE 사용자 테스트 기록 폼을 한 번에 만든다 (11/18).
 *
 * 쓰는 법: https://script.google.com → 새 프로젝트 → 이 파일 내용을 통째로 붙여넣기 → 저장
 *        → 위쪽 함수에서 createSurveyForm 고르고 ▶ 실행 → 권한 허용 → 아래 '실행 로그' 의 주소 3개를 쓴다.
 *
 * 만드는 것
 *  - 구글 폼 'ANI:WHERE 사용자 테스트 기록' (문항 이름은 automation/n8n/survey-form.md 와 글자까지 같게)
 *  - 응답이 쌓이는 구글 시트 + 응답 탭 이름을 '설문지 응답 시트1' 로 맞춤 (n8n 워크플로가 이 이름을 읽음)
 *  - '정리' 탭 + 첫 줄 제목 (참가자 · 버전 · 과업 · 성공 · 소요초 · 막힌 지점 · 메모 · 받은시각)
 *
 * 개인정보: 이메일 주소를 모으지 않고, 이름 · 나이 · 연락처 문항이 없다. 참가자는 P1, P2 … 번호로만.
 * 여러 번 실행하면 폼과 시트가 새로 하나씩 더 생긴다 (기존 것은 지우지 않는다).
 */
function createSurveyForm() {
  var form = FormApp.create('ANI:WHERE 사용자 테스트 기록');
  form.setDescription(
    '진행자가 참가자 한 명이 끝날 때마다 한 번 냅니다. 참가자는 이름 대신 P1, P2 … 번호로만 적어 주세요.\n' +
    '도와주지 않고 휴대폰 스톱워치로 잽니다. 3분(180초)이 넘으면 실패로 처리돼요.');
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setProgressBar(true);

  form.addTextItem().setTitle('참가자 번호').setHelpText('P1 처럼 번호만 (이름 X)').setRequired(true)
    .setValidation(FormApp.createTextValidation().setHelpText('P 와 숫자로 적어 주세요 (예: P1)')
      .requireTextMatchesPattern('^[Pp][0-9]+$').build());
  form.addMultipleChoiceItem().setTitle('회차').setRequired(true)
    .setChoiceValues(['1차', '2차'])
    .setHelpText('1차 = 11/25 (물어보기 없이 목록·필터·지도만) · 2차 = 11/30 (배포 주소 그대로)');

  var tasks = [
    ['T1', '이번 주말 서울에서 열려 있는 팝업 하나를 찾아 상세 화면 열기'],
    ['T2', '주술회전 팝업이 있는지 찾고, 있으면 북마크하기'],
    ['T3', '방금 북마크한 팝업이 내 캘린더에 들어갔는지 확인하기'],
    ['T4', '그 팝업에 가기 전에 공식 공지(참고 웹사이트 첫 링크) 열기']
  ];
  var number = FormApp.createTextValidation().setHelpText('초를 숫자로만 적어 주세요 (예: 45)').requireNumber().build();
  tasks.forEach(function (t) {
    form.addSectionHeaderItem().setTitle(t[0] + ' · ' + t[1]);
    form.addMultipleChoiceItem().setTitle(t[0] + ' 성공').setChoiceValues(['Y', 'N']);
    form.addTextItem().setTitle(t[0] + ' 소요초').setValidation(number);
    form.addTextItem().setTitle(t[0] + ' 막힌 지점').setHelpText('멈칫한 곳 · 잘못 누른 버튼 (없으면 비움)');
  });

  form.addSectionHeaderItem().setTitle('끝나고 참가자에게 물어보기');
  form.addParagraphTextItem().setTitle('가장 헷갈렸던 곳');
  form.addScaleItem().setTitle('만족도').setBounds(1, 5).setLabels('불편했다', '편했다');
  form.addMultipleChoiceItem().setTitle('다시 쓸 의향').setChoiceValues(['있다', '모르겠다', '없다']);

  // 응답 시트 + '정리' 탭
  var ss = SpreadsheetApp.create('ANI:WHERE 사용자 테스트 응답');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  ss = SpreadsheetApp.openById(ss.getId());
  var responses = null;
  ss.getSheets().forEach(function (sh) {
    if (sh.getFormUrl && sh.getFormUrl()) responses = sh;
  });
  if (!responses) responses = ss.getSheets()[ss.getSheets().length - 1];
  responses.setName('설문지 응답 시트1');                  // n8n '폼 응답 들어옴' 노드가 읽는 이름
  var blank = ss.getSheetByName('시트1') || ss.getSheetByName('Sheet1');
  var tidy = blank && blank.getName() !== '설문지 응답 시트1' ? blank.setName('정리') : ss.insertSheet('정리');
  tidy.getRange(1, 1, 1, 8).setValues([['참가자', '버전', '과업', '성공', '소요초', '막힌 지점', '메모', '받은시각']])
    .setFontWeight('bold');
  tidy.setFrozenRows(1);

  Logger.log('① 폼 고치기(진행자용): ' + form.getEditUrl());
  Logger.log('② 폼 내기(테스트 때 여는 주소): ' + form.getPublishedUrl());
  Logger.log('③ 응답 시트 (n8n 에 붙여넣을 주소): ' + ss.getUrl());
  Logger.log('탭: 설문지 응답 시트1 (폼 응답) · 정리 (n8n 이 쌓음)');
}

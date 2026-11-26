// 자동 생성 파일 — 손으로 고치지 말 것. 원본: docs/privacy-policy.md · docs/guide.md · static/guide/guide.css · docs/design/** · static/design/*.css
// 다시 만들기: cd web && node scripts/sync_docs.mjs

export const PRIVACY_MD: string = "# 개인정보처리방침\n\nANI:WHERE(이하 '서비스')는 「개인정보 보호법」에 따라 이용자의 개인정보를 보호하고, 관련 고충을 신속하게 처리하기 위해 다음과 같이 개인정보처리방침을 둡니다. 개인정보보호위원회 표준 개인정보처리방침의 항목 순서를 따랐습니다.\n\n> 이 서비스는 부트캠프 2차 프로젝트로 만든 개인 서비스입니다. 필요한 최소한의 정보만 받고, 이메일·전화번호·실명·생일은 받지 않습니다.\n\n## 1. 개인정보의 처리 목적\n\n| 목적 | 내용 |\n| --- | --- |\n| 회원 식별·로그인 | 같은 사람인지 알아보고 로그인 상태를 유지 |\n| 리뷰·수정 작성자 표시 | 리뷰·수정 이력에 닉네임(과 선택한 경우 프로필 사진)을 표시 |\n| 북마크·내 캘린더·알림 | 북마크한 팝업의 오픈·종료 알림, 삭제 요청 처리 결과 알림 |\n| 서비스 운영 통계 | 일별 접속 회원 수 (관리자 대시보드) |\n\n## 2. 처리하는 개인정보 항목\n\n| 구분 | 항목 | 수집 방법 |\n| --- | --- | --- |\n| 필수 (카카오·네이버 가입) | 로그인 수단, 카카오·네이버 계정 번호를 **되돌릴 수 없게 바꾼 값**(해시), 닉네임, 약관 동의 시각 | 가입 화면 |\n| 필수 (아이디 가입) | 아이디, **일방향 암호화한** 비밀번호, 닉네임, 약관 동의 시각 | 가입 화면 |\n| 선택 | 프로필 사진 (카카오·네이버 프로필 사진 주소, 또는 직접 올린 사진) | 가입 화면 선택 동의, 마이페이지 |\n| 자동 생성 | 접속한 날짜(회원 번호와 함께), 로그인 유지 쿠키, 알림 읽음 쿠키 | 서비스 이용 중 |\n| 자동 생성 (손님) | 접속 IP 를 **되돌릴 수 없게 바꾼 값** (손님 북마크 구분용, IP 원문은 저장하지 않음) | 서비스 이용 중 |\n\n받지 않는 정보: 이메일, 전화번호, 실명, 생일, 성별, 카카오·네이버 계정 번호 원래 값.\n\n서비스를 쓰는 동안 생기는 정보:\n- **위치 (선택)**: 브라우저에서 위치를 허용한 경우에만, '내 주변 팝업' · '지금 내 위치 어디야?' 에 씁니다. **저장하지 않고** 화면을 닫으면 사라집니다. 동네 이름을 알아내려고 좌표를 카카오에 보냅니다 (5번).\n- **리뷰에 붙인 사진**: 올릴 때 사진 속 **위치(GPS) · 기기 · 촬영 시각 정보를 자동으로 지운 뒤** 저장합니다. 사진은 주소를 아는 사람이 볼 수 있으니 다른 사람 얼굴 · 영수증 · 연락처가 보이는 사진은 올리지 말아 주세요.\n리뷰·공지·삭제 사유에 전화번호·이메일·계좌번호·주민번호·카드번호가 들어 있으면 저장하지 않습니다.\n\n## 3. 보유 기간과 파기\n\n| 항목 | 보유 기간 | 파기 방법 |\n| --- | --- | --- |\n| 회원 정보 (닉네임·사진·아이디·비밀번호) | **탈퇴할 때까지** | 탈퇴 즉시 지난 기록까지 지움 (닉네임·사진은 빈 값으로, 아이디·비밀번호 해시는 삭제) |\n| 접속한 날짜 | 1년 (탈퇴하면 즉시) | 기간이 지나면 삭제 |\n| 쓴 리뷰·수정 이력 | 서비스 운영 기간 | 탈퇴하면 작성자를 '탈퇴한 회원'으로 바꿈 (내용은 다른 이용자를 위해 남음). 지우고 싶은 글은 탈퇴 전에 삭제 요청 |\n| 기간이 끝난(또는 운영자가 내린) 팝업에 단 리뷰 · 북마크 | 팝업이 내려간 주가 끝날 때까지 | 다음 주 월요일에 팝업과 함께 리뷰 · 북마크 · 리뷰 사진을 모두 삭제 |\n| 리뷰에 붙인 사진 | 그 리뷰를 지울 때까지 | 리뷰를 지우면(내가 지우거나 관리자가 지우면) 사진 파일을 바로 삭제. 지운 리뷰의 글은 화면에서 사라지고, 되돌리기용 내부 기록에만 남아 관리자만 볼 수 있음 |\n| 쿠키 | 로그인 30일, 알림 읽음 60일 | 기간이 지나면 브라우저에서 사라짐, 로그아웃·탈퇴 시 바로 지움 |\n\n전자적 파일은 복구할 수 없는 방법으로 지웁니다.\n\n## 4. 제3자 제공\n\n개인정보를 제3자에게 제공하지 않습니다.\n\n## 5. 처리 위탁과 국외 이전\n\n서비스를 운영하려고 다음 업체의 서비스를 씁니다.\n\n| 업체 | 하는 일 | 저장 위치 | 옮겨 가는 정보 |\n| --- | --- | --- | --- |\n| Supabase | 데이터베이스 (회원·리뷰·북마크) | 대한민국(서울) 리전 | 2번의 모든 항목 |\n| Streamlit (Snowflake) | 앱 서버 | 미국 | 서비스를 쓰는 동안 오가는 정보, 직접 올린 사진 파일 |\n| Vercel | 공개 웹 서버 (읽기 전용) | 미국 | 접속 기록 (개인정보 저장 없음) |\n| OpenAI | '물어보기' 답 만들기 | 미국 | 질문 글 (전화번호·이메일 등은 가린 뒤 보냄, 회원 정보는 보내지 않음) |\n| 카카오 · 네이버 | 간편 로그인 인증 | 대한민국 | 로그인할 때 인증 정보 (서비스는 해시값만 저장) |\n| 카카오 (지도 · 로컬) | 지도 표시, 주소 → 좌표, 내 위치 → 동네 이름 | 대한민국 | 팝업 주소, 위치를 허용한 경우 내 좌표 (저장하지 않음, 회원 정보는 보내지 않음) |\n| 네이버클라우드 (NAVER API HUB) | 블로그 후기 검색 | 대한민국 | 없음 (팝업 작품명·매장명만 보냄, 회원 정보는 보내지 않음) |\n\n국외 이전은 서비스를 쓰는 시점에 인터넷으로 옮겨지며, 거부하려면 서비스를 쓰지 않거나 탈퇴하면 됩니다.\n\n## 6. 이용자의 권리와 행사 방법\n\n- **열람·정정:** 마이페이지(오른쪽 위 내 닉네임)에서 닉네임·프로필 사진을 보고 고칠 수 있습니다.\n- **삭제·처리 정지:** 마이페이지의 **탈퇴하기**로 언제든 지울 수 있습니다. 프로필 사진은 '기본 사진 설정'을 누르면 바로 지워집니다.\n- **동의 철회:** 선택 동의(프로필 사진)는 마이페이지에서 '기본 사진 설정'을 눌러 철회할 수 있습니다.\n\n## 7. 만 14세 미만 아동\n\n**만 14세 이상만 가입할 수 있습니다.** 만 14세 미만의 개인정보를 처리하려면 법정대리인 동의가 필요하지만, 이 서비스는 그 확인 절차를 아직 갖추지 않아 만 14세 미만의 가입을 받지 않습니다. 가입 화면에서 만 14세 이상인지 확인합니다.\n\n## 8. 안전성 확보 조치\n\n- 비밀번호는 **일방향 암호화(bcrypt)** 해서 저장하고, 원래 비밀번호는 어디에도 남기지 않습니다.\n- 카카오·네이버 계정 번호와 손님 IP 는 소금 친 해시로 바꿔 원래 값을 알 수 없게 저장합니다.\n- 모든 통신은 HTTPS 로 암호화합니다. 데이터베이스는 행 단위 보안(RLS)으로 고치기·지우기를 막습니다.\n- 관리자 권한은 지정한 1명에게만 있습니다.\n- 글에 개인정보(전화번호·이메일 등)가 들어 있으면 저장하지 않습니다.\n- 올린 사진은 위치(GPS) · 기기 · 촬영 시각 정보를 지운 뒤 저장하고, 리뷰를 지우면 사진 파일도 지웁니다.\n\n## 9. 쿠키\n\n| 쿠키 | 목적 | 기간 |\n| --- | --- | --- |\n| `aw_session` | 로그인 유지 (서명한 회원 번호) | 30일 |\n| `aw_ntf_read` | 읽은 알림 표시 | 60일 |\n\n브라우저 설정에서 쿠키를 거부할 수 있으며, 거부하면 로그인이 유지되지 않습니다.\n\n## 10. 개인정보 보호책임자\n\n| | |\n| --- | --- |\n| 책임자 | 김서안 (ANI:WHERE 운영자) |\n| 연락처 | tjtek888@gmail.com |\n\n개인정보 침해 상담: 개인정보침해신고센터(privacy.kisa.or.kr, 국번 없이 118), 개인정보분쟁조정위원회(www.kopico.go.kr, 1833-6972)\n\n## 11. 시행일\n\n이 개인정보처리방침은 2026년 11월 18일부터 적용합니다.\n\n---\n\n# 이용약관 (요약)\n\n1. **서비스:** 애니메이션 팝업·콜라보 카페 정보를 지도와 목록으로 보여 주고, 회원이 리뷰·북마크·정보 수정을 할 수 있게 합니다.\n2. **가입:** 만 14세 이상만 가입할 수 있습니다. 다른 사람인 척하거나 욕설·음란한 닉네임은 쓸 수 없습니다.\n3. **게시물:** 리뷰·수정한 정보에 대한 책임은 쓴 사람에게 있습니다. 욕설·광고·남의 개인정보·저작권을 침해하는 글은 관리자가 지울 수 있습니다. 다른 회원의 글은 '삭제 요청'으로 신고할 수 있습니다.\n4. **정보의 정확성:** 팝업 정보는 자동 수집과 이용자 입력으로 모읍니다. 방문 전 공식 공지를 꼭 확인해 주세요. '기간 확인 필요'·'링크 확인 필요' 표시가 있는 정보는 특히 확인이 필요합니다.\n5. **탈퇴:** 마이페이지에서 언제든 탈퇴할 수 있고, 개인정보는 개인정보처리방침 3번에 따라 지웁니다.\n";

export const GUIDE_HTML: string = "<div class=\"g-hero\">\n<div class=\"g-hero-t\">ANI:WHERE 사용자 튜토리얼</div>\n<div class=\"g-hero-s\">애니 팝업 · 콜라보 카페 · 굿즈 행사를 <b>찾고</b>, <b>북마크</b>하고, <b>놓치지 않게</b> 도와주는 곳이에요.<br>처음이라도 괜찮아요. 그림을 보면서 하나씩 따라 해 보세요!</div>\n</div>\n\n<div class=\"g-h2\">처음 왔다면 딱 3단계만!</div>\n<div class=\"g-sub\">옆으로 넘겨 보세요 (‹ › 버튼을 누르거나, 손가락 · 마우스로 밀어도 돼요)</div>\n<div class=\"g-slides-wrap\">\n<div class=\"g-slides\">\n<div class=\"g-slide\"><img src=\"/guide/home.webp\" alt=\"홈 화면\"><div class=\"g-slide-t\"><b>1</b> 홈에서 둘러보기</div><div class=\"g-slide-s\">지금 인기 있는 팝업, 새로 생긴 팝업, 곧 끝나는 팝업이 한눈에 보여요.</div></div>\n<div class=\"g-slide\"><img src=\"/guide/card.webp\" alt=\"팝업 카드\"><div class=\"g-slide-t\"><b>2</b> 마음에 들면 북마크</div><div class=\"g-slide-s\">포스터 오른쪽 아래 <b>북마크 버튼</b>을 꾹! 누르면 내 목록에 저장돼요.</div></div>\n<div class=\"g-slide\"><img src=\"/guide/calendar.webp\" alt=\"내 캘린더\"><div class=\"g-slide-t\"><b>3</b> 내 캘린더에서 챙기기</div><div class=\"g-slide-s\">북마크한 팝업이 달력에 쏙. 열리기 전 · 끝나기 전에 알림도 와요.</div></div>\n</div>\n</div>\n\n<div class=\"g-h2\">어떤 걸 알고 싶나요?</div>\n<div class=\"g-nav\">\n<a href=\"#home\"><span class=\"mi\">home</span>홈</a>\n<a href=\"#map\"><span class=\"mi\">map</span>지도로 보기</a>\n<a href=\"#list\"><span class=\"mi\">format_list_bulleted</span>리스트로 보기</a>\n<a href=\"#detail\"><span class=\"mi\">article</span>팝업 자세히 보기 · 리뷰</a>\n<a href=\"#bookmark\"><span class=\"mi\">bookmark_add</span>북마크</a>\n<a href=\"#cal\"><span class=\"mi\">calendar_month</span>내 캘린더 · 알림</a>\n<a href=\"#rank\"><span class=\"mi\">verified</span>후기 도장 랭크</a>\n<a href=\"#add\"><span class=\"mi\">add_circle</span>팝업 등록하기</a>\n<a href=\"#edit\"><span class=\"mi\">edit</span>정보 고치기</a>\n<a href=\"#delete\"><span class=\"mi\">delete</span>삭제 요청하기</a>\n<a href=\"#login\"><span class=\"mi\">login</span>로그인 · 회원가입</a>\n<a href=\"#mypage\"><span class=\"mi\">account_circle</span>마이페이지</a>\n<a href=\"#ask\"><span class=\"mi\">forum</span>물어보기</a>\n<a href=\"#mobile\"><span class=\"mi\">smartphone</span>휴대폰으로 쓰기</a>\n</div>\n\n<a id=\"home\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">home</span>홈</div>\n<div class=\"g-lead\">왼쪽 위 <b>ANI:WHERE 로고</b>를 누르거나, 메뉴의 <b>홈</b>을 누르면 와요. 처음 들어오면 언제나 홈부터 보여요. 맨 위 메뉴는 <b>홈 · 지도로 보기 · 리스트로 보기 · 내 캘린더</b> 네 가지이고, 지금 보고 있는 메뉴가 흰 알약 모양으로 표시돼요.</div>\n<img class=\"g-img\" src=\"/guide/home.webp\" alt=\"홈 화면\">\n<table class=\"g-table\">\n<tr><th>칸 이름</th><th>무엇을 보여 주나요?</th></tr>\n<tr><td><b>북마크 팝업</b></td><td>내가 북마크한 팝업이 동그라미로 모여요. 동그라미 아래쪽에는 지역이 보이고, 누르면 그 팝업으로 가요. 로그인하기 전에는 이 자리에 <b>특전 있는 작품들</b>이 보여요.</td></tr>\n<tr><td><b>실시간 인기 급상승 랭킹</b></td><td>최근 7일 동안 북마크와 리뷰가 많이 늘어난 팝업 1~5위예요 (북마크 1개 = 2점, 리뷰 · 답글 1개 = 1점. 같으면 전체 기간 점수, 그다음 오픈이 빠른 순. 앱과 웹이 같은 순서예요). 오른쪽 순위를 누르면 큰 배너가 바뀌고, 배너를 누르면 그 팝업으로 가요.</td></tr>\n<tr><td><b>따끈따끈 신규 등록 팝업</b></td><td>새로 올라온 팝업이에요. 카드를 옆으로 넘겨 보고, 오른쪽 위 지역 버튼으로 골라 볼 수 있어요. 줄 맨 끝의 <b>더보기</b> 카드를 누르면 리스트로 가요.</td></tr>\n<tr><td><b>곧 끝나는 팝업</b></td><td>어제부터 일주일 동안, 그날 끝나는 팝업을 날짜 칸 7개로 보여 줘요. 목요일이라면 수요일부터 다음 주 화요일까지예요. 오늘 칸은 민트색이에요. 많은 날은 <b>+N건 더보기</b>를 누르면 다 보여요.</td></tr>\n<tr><td><b>사전예약 팝업</b></td><td>아직 열기 전이고, 미리 예약해야 들어갈 수 있는 팝업이에요. <b>팝업이 열리는 날</b> 순서대로 한 줄(타임라인)에 놓여요. 이 칸만 보라색이에요.</td></tr>\n<tr><td><b>꿀팁 가득! 실시간 후기 모음</b></td><td>사람들이 남긴 최신 후기예요. 사진이 있는 후기가 먼저 나와요. 한 줄에 카드 3장씩 보여요.</td></tr>\n</table>\n<div class=\"g-row\">\n<img src=\"/guide/home_rank.webp\" alt=\"랭킹 배너\">\n<div><div class=\"g-h3\">랭킹 배너 쓰는 법</div>\n<ol class=\"g-steps\"><li>‹ › 버튼을 누르면 다음 순위로 넘어가요.</li><li>가만히 두면 5초마다 저절로 넘어가요.</li><li>오른쪽 목록에서 <b>3</b>을 누르면 3위 배너로 바로 바뀌어요.</li><li>배너를 누르면 그 팝업의 자세한 정보가 열려요.</li></ol></div>\n</div>\n<div class=\"g-h3\">사전예약 팝업 — 열리는 날을 놓치지 않기</div>\n<img class=\"g-img\" src=\"/guide/home_reserve.webp\" alt=\"사전예약 팝업 타임라인\">\n<ol class=\"g-steps\"><li>카드 위 보라색 글씨(<b>11.28 (토) 팝업 오픈</b>)가 그 팝업이 열리는 날이에요. 왼쪽일수록 빨리 열려요.</li><li>카드를 누르면 자세한 정보가 열려요. 예약하는 곳은 그 안의 <b>참고 웹사이트</b>에서 확인해요.</li><li>카드 아래 <b>북마크하고 오픈 알림 받기</b>를 누르면 북마크되고, 열리기 3일 전부터 알림이 와요. (회원만)</li><li>왼쪽 <b>사전예약 팝업만 보기</b>를 누르면 리스트에서 사전예약 팝업만 모아 볼 수 있어요.</li></ol>\n<div class=\"g-h3\">후기 모음 — 다녀온 사람들의 이야기</div>\n<img class=\"g-img\" src=\"/guide/home_reviews.webp\" alt=\"실시간 후기 모음\">\n<ol class=\"g-steps\"><li>오른쪽 위 <b>전체 · 다녀온 후기 · 기대평 · 기타</b>를 누르면 그 종류만 볼 수 있어요.</li><li>닉네임 옆 <b>Lv.2</b> 같은 작은 도장은 그 사람의 <a href=\"#rank\" target=\"_self\">후기 도장 랭크</a>예요.</li><li>카드 아래 팝업 이름을 누르면 그 팝업으로 가요.</li></ol>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>그림 속 닉네임 <b>튜토리얼</b>과 후기 글은 설명하려고 만든 시험용이에요. 실제 회원의 글이 아니에요.</div>\n</div>\n\n<a id=\"map\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">map</span>지도로 보기</div>\n<div class=\"g-lead\">메뉴의 <b>지도로 보기</b>를 누르면, 팝업이 어디에 있는지 지도에서 볼 수 있어요. 화면이 세 칸으로 나뉘어 있어요.</div>\n<img class=\"g-img\" src=\"/guide/map.webp\" alt=\"지도로 보기\">\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">event_note</span><b>왼쪽 · 데일리 팝업 노트</b><p>날짜 옆 ‹ › 로 날을 바꾸고, 그 아래 ‹ 지역 N › 으로 지역을 바꾸면 그날 그곳에서 열려 있는 팝업이 나와요. N 은 팝업 수예요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">location_on</span><b>가운데 · 지도</b><p>민트색 핀이 팝업이 있는 곳이에요. 핀 위에 마우스를 올리면 카드가, 누르면 목록이 떠요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">forum</span><b>오른쪽 · 물어보기</b><p>“이번 주말 홍대 팝업”처럼 말로 물어보면 찾아 줘요.</p></div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>위치 사용을 허락하면 <b>내 주변</b>부터 보여 줘요. 지도 왼쪽 위 + − 로 크게 · 작게 볼 수 있어요.</div>\n</div>\n\n<a id=\"list\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">format_list_bulleted</span>리스트로 보기</div>\n<div class=\"g-lead\">팝업을 포스터 카드로 쭉 모아 봐요. 카드를 누르면 자세한 정보가 열려요. 카드 위에 마우스를 올리면 <b>캐릭터 · 주소 · 특전</b>이 포스터 위에 살짝 보여요.</div>\n<img class=\"g-img\" src=\"/guide/list.webp\" alt=\"리스트로 보기\">\n<div class=\"g-h3\">카드 위 작은 글씨는 무슨 뜻일까요?</div>\n<table class=\"g-table\">\n<tr><th>보이는 글씨</th><th>뜻</th></tr>\n<tr><td><span class=\"g-badge green\">진행 중</span></td><td>지금 열려 있어요. 가 볼 수 있어요!</td></tr>\n<tr><td><span class=\"g-badge blue\">D-5</span></td><td>5일 뒤에 열려요.</td></tr>\n<tr><td><span class=\"g-badge red\">마감임박</span></td><td>3일 안에 끝나요. 서둘러요!</td></tr>\n<tr><td><span class=\"g-badge purple\">사전예약 D-5</span></td><td>예약해야 들어갈 수 있고, 5일 뒤에 열려요. (홈의 사전예약 칸)</td></tr>\n<tr><td><span class=\"g-badge gray\">종료</span></td><td>이미 끝났어요.</td></tr>\n</table>\n<div class=\"g-sub\">포스터 왼쪽 위가 상태, 오른쪽 위가 지역(마포 · 부산 …), 오른쪽 아래가 북마크 버튼이에요.</div>\n<div class=\"g-row\">\n<img src=\"/guide/search.webp\" alt=\"검색 필터\">\n<div><div class=\"g-h3\">원하는 팝업만 골라 보기</div>\n<ol class=\"g-steps\"><li>메뉴 오른쪽 <b>돋보기</b>를 눌러요. (지도로 보기 · 리스트로 보기에서만 보여요)</li><li>말풍선처럼 펼쳐진 칸에 작품 이름, 캐릭터, 진행 여부, 날짜를 넣어요.</li><li>목록 위 <b>북마크</b>, <b>지역 고르기</b>, <b>정렬</b>로 더 좁힐 수 있어요.</li><li>지금 걸려 있는 조건은 목록 위에 작은 알약으로 보여요. 알약의 × 를 누르면 그 조건만 풀려요.</li><li>아무것도 안 나오면, 어떤 조건을 빼면 몇 곳이 나오는지 알려 줘요.</li></ol></div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>처음에는 24곳만 보여요. 맨 아래 <b>N건 더보기</b>를 누르면 더 나와요.</div>\n</div>\n\n<a id=\"detail\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">article</span>팝업 자세히 보기 · 리뷰</div>\n<div class=\"g-lead\">카드를 누르면 열리는 화면이에요. <b>위쪽</b>에는 사진과 정보가 나란히 있고, <b>아래쪽</b>에는 화면 폭을 다 쓰는 탭 세 개(<b>리뷰 · 블로그 후기 · 수정하기</b>)가 있어요.</div>\n<img class=\"g-img\" src=\"/guide/detail.webp\" alt=\"팝업 자세히 보기\">\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">image</span><b>위 왼쪽 · 사진</b><p>포스터와 올라온 사진이에요. 누르면 크게 볼 수 있어요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">info</span><b>위 오른쪽 · 정보</b><p>상태 · 지역, 이름, 위치(지도에서 확인하기), 일정, 혜택, 참고 웹사이트, 팝업 소개. 이름 옆에 공유와 북마크 버튼이 있어요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">tab</span><b>아래 · 탭 세 개</b><p>리뷰(쓰기 · 읽기), 블로그 후기(네이버 블로그 글 모음), 수정하기(정보 고치기).</p></div>\n</div>\n<div class=\"g-h3\">리뷰 쓰고 읽기</div>\n<img class=\"g-img\" src=\"/guide/detail_review.webp\" alt=\"리뷰 탭\">\n<ol class=\"g-steps\"><li><b>리뷰</b> 탭의 <b>왼쪽</b>이 리뷰 쓰는 칸이에요. (회원만 쓸 수 있어요)</li><li>먼저 종류를 골라요: <b>다녀온 후기</b>(다녀왔어요) · <b>기대평</b>(가 보고 싶어요) · <b>기타</b>.</li><li>다녀온 후기라면 별을 눌러 점수를 줘요. 별점만 골라도 등록돼요.</li><li>글을 쓰고, 사진도 4장까지 붙일 수 있어요. 얼굴 · 영수증 · 연락처가 보이는 사진은 올리지 말아 주세요.</li><li><b>리뷰 등록</b>을 누르면 끝! 이 팝업에 처음 쓰는 다녀온 후기라면 버튼 이름이 <b>등록하고 도장 받기</b>예요.</li></ol>\n<div class=\"g-sub\"><b>오른쪽</b>에는 평균 별점과 점수 분포(5점 ~ 1점), 사진 모아 보기, 사람들이 쓴 리뷰가 있어요. <b>전체 · 사진 후기만 · 다녀온 후기 · 기대평 · 기타</b>로 골라 보고, 정렬도 바꿀 수 있어요. 내가 쓴 리뷰는 오른쪽 <b>⋯</b> 에서 고치거나 지울 수 있고, 다른 사람 리뷰에는 <b>답글 쓰기</b>를 할 수 있어요. 전화번호 · 이메일 같은 개인정보가 들어간 글은 등록되지 않아요.</div>\n<div class=\"g-row\">\n<img src=\"/guide/similar.webp\" alt=\"이 근처 다른 팝업\">\n<div><div class=\"g-h3\">맨 아래 · 다른 팝업도 보기</div><p>탭 아래에는 같은 작품의 <b>비슷한 팝업</b>과 <b>이 근처 다른 팝업</b>이 한 줄로 나와요. 간 김에 들를 곳을 찾기 좋아요.</p></div>\n</div>\n</div>\n\n<a id=\"bookmark\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">bookmark_add</span>북마크 · 북마크 팝업</div>\n<div class=\"g-lead\">북마크는 “이거 가고 싶어!” 하고 표시해 두는 거예요. 북마크는 <b>회원마다 따로</b> 저장돼요.</div>\n<div class=\"g-row\">\n<img src=\"/guide/card.webp\" alt=\"카드의 북마크 버튼\" class=\"g-small\">\n<div><div class=\"g-h3\">하나씩 북마크하기</div><ol class=\"g-steps\"><li>포스터 오른쪽 아래(또는 자세히 보기의 이름 옆) <b>북마크 버튼</b>을 눌러요.</li><li>버튼이 민트색으로 바뀌면 저장된 거예요.</li><li>한 번 더 누르면 풀려요.</li></ol></div>\n</div>\n<div class=\"g-row\">\n<img src=\"/guide/fav_dialog.webp\" alt=\"최애 추가하기 창\">\n<div><div class=\"g-h3\">여러 개를 한 번에 — 최애 추가하기</div><ol class=\"g-steps\"><li>홈의 <b>북마크 팝업</b>에서 <b>+ 최애 추가하기</b>를 눌러요.</li><li>마음에 드는 팝업 포스터를 눌러 골라요. (체크 표시가 생겨요)</li><li><b>저장하기</b>를 누르면 끝!</li></ol></div>\n</div>\n<img class=\"g-img g-narrow\" src=\"/guide/home_fav.webp\" alt=\"북마크 팝업\">\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>로그인하지 않았을 때 북마크를 누르면 로그인 화면으로 가요.</div>\n</div>\n\n<a id=\"cal\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">calendar_month</span>내 캘린더 · 알림</div>\n<div class=\"g-lead\">회원만 쓸 수 있어요. 메뉴의 <b>내 캘린더</b>를 누르세요. 계절마다 꽃잎 · 잎사귀 · 단풍 · 눈이 내려요!</div>\n<img class=\"g-img\" src=\"/guide/calendar.webp\" alt=\"내 캘린더\">\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">calendar_month</span><b>왼쪽 · 달력과 곧 있는 팝업</b><p>작은 달력에 북마크한 팝업이 날짜 막대로 보여요. ‹ › 로 달을 넘기고 이번달로 돌아와요. 그 아래 곧 있는 팝업은 열리거나 끝나는 날이 가까운 순서예요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">bookmarks</span><b>가운데 · 내 목록 (넓게)</b><p>탭 세 개: 북마크 · 다녀온 팝업 · 최근 본(10개). 카드를 누르면 그 팝업으로 가고, 북마크 버튼으로 바로 풀 수도 있어요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">notifications</span><b>오른쪽 · 알림과 추천</b><p>알림 받은 내역(최근 3일)과, 위치를 허락하면 나오는 내 주변 추천 팝업이에요.</p></div>\n</div>\n<div class=\"g-row\">\n<img src=\"/guide/visited.webp\" alt=\"다녀온 팝업 탭\">\n<div><div class=\"g-h3\">다녀온 팝업 탭 — 도장 모으기</div><ol class=\"g-steps\"><li>가운데에서 <b>다녀온 팝업</b> 탭을 눌러요.</li><li>맨 위에 <b>내 후기 도장</b>(지금 랭크, 다음 랭크까지 남은 수)이 보여요.</li><li>그 아래는 내가 <b>다녀온 후기</b>를 남긴 팝업이에요. 포스터 모서리에 도장이 찍혀 있고, 내가 쓴 글도 같이 보여요.</li></ol><p>도장이 어떻게 쌓이는지는 <a href=\"#rank\" target=\"_self\">후기 도장 랭크</a>에서 알려 드려요.</p></div>\n</div>\n<div class=\"g-h3\">알림은 언제 오나요?</div>\n<div class=\"g-timeline\">\n<div class=\"g-tl-row\"><div class=\"g-tl-lab\">열리기 전</div><div class=\"g-tl-bar\"><span>D-3</span><span>D-2</span><span>D-1</span><span class=\"hit\">오픈!</span></div></div>\n<div class=\"g-tl-row\"><div class=\"g-tl-lab\">끝나기 전</div><div class=\"g-tl-bar\"><span>D-3</span><span>D-2</span><span>D-1</span><span class=\"hit end\">종료!</span></div></div>\n</div>\n<div class=\"g-sub\">북마크한 팝업이 열리기 3일 전부터, 끝나기 3일 전부터 메뉴의 <b>종 모양</b>에 빨간 점이 생겨요. 관리자 공지와 삭제 요청 결과도 여기로 와요.</div>\n</div>\n\n<a id=\"rank\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">verified</span>후기 도장 랭크</div>\n<div class=\"g-lead\">팝업에 다녀와서 <b>다녀온 후기</b>를 남기면 도장이 하나 찍혀요. 도장이 쌓이면 랭크가 올라가고, <b>도장 색이 바뀌어요</b>.</div>\n<img class=\"g-img\" src=\"/guide/rank.webp\" alt=\"후기 도장 랭크 안내\">\n<table class=\"g-table\">\n<tr><th>랭크</th><th>다녀온 후기</th><th>도장 색</th></tr>\n<tr><td><span class=\"g-rk l1\"></span><b>Lv.1 새싹 팬</b></td><td>1개</td><td>연한 초록</td></tr>\n<tr><td><span class=\"g-rk l2\"></span><b>Lv.2 단골 팬</b></td><td>3개</td><td>진한 초록</td></tr>\n<tr><td><span class=\"g-rk l3\"></span><b>Lv.3 성지순례러</b></td><td>10개</td><td>파랑</td></tr>\n<tr><td><span class=\"g-rk l4\"></span><b>Lv.4 덕질 마스터</b></td><td>25개</td><td>보라</td></tr>\n<tr><td><span class=\"g-rk l5\"></span><b>Lv.5 전설의 덕후</b></td><td>50개</td><td>금색</td></tr>\n</table>\n<div class=\"g-h3\">도장은 이렇게 세요</div>\n<table class=\"g-table\">\n<tr><th>도장이 찍혀요</th><th>도장이 안 찍혀요</th></tr>\n<tr><td>다녀온 후기 (별점만 남겨도 1개)</td><td>기대평 · 기타 · 답글</td></tr>\n<tr><td>팝업 하나에 도장 1개</td><td>같은 팝업에 여러 번 쓴 후기 (그래도 1개)</td></tr>\n<tr><td>지금 남아 있는 후기</td><td>내가 지운 후기, 관리자가 지운 후기</td></tr>\n</table>\n<div class=\"g-h3\">도장은 어디에서 보이나요?</div>\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">rate_review</span><b>리뷰 닉네임 옆</b><p>리뷰와 홈의 후기 모음에서, 닉네임 옆에 작은 도장과 Lv.2 같은 글씨가 붙어요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">calendar_month</span><b>내 캘린더 · 다녀온 팝업</b><p>다녀온 팝업 카드의 포스터 모서리에 도장이 찍혀요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">account_circle</span><b>마이페이지</b><p>큰 도장과 함께, 다음 랭크까지 몇 개 남았는지 보여 줘요.</p></div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>마이페이지나 내 캘린더의 <b>랭크 안내 보기</b>를 누르면 위 그림 같은 안내 창이 떠요. 랭크가 올라도 달라지는 것은 <b>도장 색</b>뿐이에요. 탈퇴하면 도장도 함께 지워져요.</div>\n</div>\n\n<a id=\"add\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">add_circle</span>팝업 등록하기</div>\n<div class=\"g-lead\">아직 없는 팝업을 알려 주세요! 로그인한 뒤 화면 <b>오른쪽 아래 코랄색 + 버튼</b>을 누르면 돼요.</div>\n<img class=\"g-img\" src=\"/guide/add.webp\" alt=\"팝업 등록하기\">\n<div class=\"g-stepper\">\n<div><b>1</b>작품 · 캐릭터</div><div><b>2</b>카페 정보</div><div><b>3</b>이미지</div><div><b>4</b>기간</div><div><b>5</b>특전 · 굿즈</div><div><b>6</b>팝업 소개</div><div><b>7</b>등록 확인</div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>공지 글이 있다면 <b>공지로 간편등록</b>을 눌러 붙여 넣기만 해도 돼요. 매일 아침 자동으로 모으기도 하니, 먼저 검색해서 이미 있는지 확인해 보세요. 전화번호 · 이메일 같은 개인정보는 저장되지 않아요.</div>\n</div>\n\n<a id=\"edit\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">edit</span>정보 고치기</div>\n<div class=\"g-lead\">날짜가 바뀌었거나 주소가 틀렸다면 직접 고칠 수 있어요. 회원이면 누구나 모든 칸을 고칠 수 있어요.</div>\n<img class=\"g-img\" src=\"/guide/edit.webp\" alt=\"수정하기 탭\">\n<ol class=\"g-steps\"><li>고칠 팝업의 자세히 보기를 열어요.</li><li>아래쪽 탭에서 <b>수정하기</b>를 눌러요. (리뷰 · 블로그 후기 옆)</li><li>등록할 때와 같은 일곱 묶음(작품 · 캐릭터 → 카페 정보 → 이미지 → 기간 → 특전 · 굿즈 · 이벤트 → 참고 웹사이트 → 팝업 소개)이 한 화면에 다 나와요. 고칠 칸만 고쳐요.</li><li>칸을 고치면 오른쪽 <b>저장하면 이렇게 바뀌어요</b>에 예전 내용과 바뀐 내용이 나란히 보여요.</li><li>맨 아래 검은 줄에 <b>바뀐 칸 N곳</b>이 뜨면 <b>저장하기</b>를 눌러요. 마음이 바뀌면 <b>되돌리기</b>를 누르면 고치기 전으로 돌아가요.</li></ol>\n<div class=\"g-row\">\n<img src=\"/guide/edit_save.webp\" alt=\"저장 줄\">\n<div><div class=\"g-h3\">잘못 고쳤다면? — 수정 이력</div><p>고친 기록은 모두 남아요. 오른쪽 <b>수정 이력</b>에서 예전 기록을 골라 <b>되돌리기</b>를 누르면 그때 내용으로 돌아가요.</p><p>리뷰는 내가 쓴 것만 고칠 수 있어요. (리뷰 오른쪽 <b>⋯</b>)</p></div>\n</div>\n</div>\n\n<a id=\"delete\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">delete</span>삭제 요청하기</div>\n<div class=\"g-lead\">글은 바로 지워지지 않아요. 대신 <b>삭제 요청</b>을 보내면 관리자가 확인해요. 삭제 요청은 <b>수정하기</b> 탭 맨 아래, “끝난 팝업이거나 잘못 올라온 팝업인가요?” 옆에 있어요.</div>\n<div class=\"g-flow\">\n<div><span class=\"mi\">send</span>수정하기 탭 맨 아래 <b>삭제 요청</b> + 이유 적기</div><i class=\"mi\">arrow_forward</i>\n<div><span class=\"mi\">admin_panel_settings</span>관리자가 확인하고 <b>승인 / 거부</b></div><i class=\"mi\">arrow_forward</i>\n<div><span class=\"mi\">notifications</span>결과를 <b>종 알림</b>으로 받기</div>\n</div>\n</div>\n\n<a id=\"login\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">login</span>로그인 · 회원가입</div>\n<div class=\"g-row\">\n<img src=\"/guide/login.webp\" alt=\"로그인 화면\">\n<div><ol class=\"g-steps\"><li>메뉴 오른쪽 <b>로그인</b>을 눌러요.</li><li><b>카카오 · 네이버 로그인</b>을 누르거나, 위쪽 <b>회원가입</b>을 눌러 <b>아이디로 가입</b>해요.</li><li>필수 동의 3개에 체크하면 끝!</li></ol><p>로그인하면 <b>로그인</b> 글씨 자리가 내 <b>프로필 동그라미</b>로 바뀌어요.</p></div>\n</div>\n<table class=\"g-table\">\n<tr><th>받는 것</th><th>받지 않는 것</th></tr>\n<tr><td>닉네임(선택) · 필수 동의 3개 (만 14세 이상 · 이용약관 · 개인정보 수집 · 이용)</td><td>이메일 · 전화번호</td></tr>\n</table>\n<div class=\"g-sub\">로그아웃 · 닉네임 바꾸기 · 프로필 사진 · 탈퇴는 <a href=\"#mypage\" target=\"_self\">마이페이지</a>에 있어요. 자세한 내용은 <a href=\"./privacy\" target=\"_self\">개인정보처리방침</a>을 봐 주세요.</div>\n</div>\n\n<a id=\"mypage\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">account_circle</span>마이페이지</div>\n<div class=\"g-lead\">메뉴 오른쪽 끝의 <b>프로필 동그라미</b>를 누르면 마이페이지가 열려요. 내 정보와 내가 쓴 후기, 설정이 한곳에 모여 있어요.</div>\n<img class=\"g-img\" src=\"/guide/mypage.webp\" alt=\"마이페이지\">\n<table class=\"g-table\">\n<tr><th>칸 이름</th><th>무엇이 있나요?</th></tr>\n<tr><td><b>프로필</b></td><td>프로필 사진, 닉네임, 지금 랭크, 가입한 방법과 날짜. 그 아래 숫자 3개는 <b>북마크</b> · <b>후기 도장</b> · <b>쓴 후기</b> 수예요. <b>프로필 수정</b>을 누르면 설정 칸으로 가요.</td></tr>\n<tr><td><b>내 후기 도장</b></td><td>지금 랭크와 큰 도장, 다음 랭크까지 남은 수, 다섯 랭크 중 어디까지 왔는지. <b>랭크 안내 보기</b>를 누르면 안내 창이 떠요.</td></tr>\n<tr><td><b>내가 쓴 후기</b></td><td>내가 쓴 후기가 최신순으로 모여요. 누르면 그 팝업으로 가요. 도장을 받은 후기에는 오른쪽에 도장이 보여요.</td></tr>\n<tr><td><b>설정</b></td><td>닉네임 바꾸기 · 오픈 · 종료 알림 내역 · 프로필 사진(선택 동의) · 비밀번호 바꾸기. 그 아래에 <b>로그아웃</b> 버튼, 개인정보처리방침 · 이용약관, 사용자 튜토리얼, 맨 아래에 탈퇴하기</td></tr>\n</table>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span><b>탈퇴하기</b>는 설정 맨 아래에 작은 글씨로 있어요. 탈퇴하면 닉네임 · 사진 · 접속 기록 · 도장을 바로 지우고, 쓴 후기는 ‘탈퇴한 회원’으로 남아요.</div>\n</div>\n\n<a id=\"ask\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">forum</span>물어보기 (ANI:WHERE에게 물어보기)</div>\n<div class=\"g-row\">\n<img src=\"/guide/ask.webp\" alt=\"물어보기\" class=\"g-small\">\n<div><div class=\"g-lead\">친구에게 묻듯이 물어보세요. <b>작품 · 지역 · 날짜</b>를 넣으면 더 정확해요.</div>\n<div class=\"g-chips\"><span>치이카와 이번 달 서울 팝업 있어?</span><span>이번 주말 홍대 팝업</span><span>내 주변 가까운 팝업</span><span>곧 끝나는 팝업</span><span>내 북마크 보여줘</span><span>등록 어떻게 해?</span></div>\n<p>PC는 지도 · 리스트 오른쪽 창, 휴대폰은 오른쪽 아래 <b>토끼 얼굴 버튼</b>이에요.</p></div>\n</div>\n</div>\n\n<a id=\"mobile\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">smartphone</span>휴대폰으로 쓰기</div>\n<div class=\"g-phones\">\n<figure><img src=\"/guide/mobile_home.webp\" alt=\"휴대폰 홈\"><figcaption>메뉴는 맨 위 <b>홈 · 지도로 보기 · 리스트로 보기 · 내 캘린더</b>. 오른쪽 위 동그라미가 <b>마이페이지</b></figcaption></figure>\n<figure><img src=\"/guide/mobile_filter.webp\" alt=\"휴대폰 필터\"><figcaption>리스트에서 <b>필터 버튼</b>을 누르면 창이 열려요. 다 고르면 <b>팝업 N곳 표시</b></figcaption></figure>\n</div>\n</div>\n\n<div class=\"g-end\">궁금한 게 더 있으면 <b>물어보기</b>에 편하게 물어봐 주세요!</div>\n";

export const GUIDE_CSS: string = "/* 사용자 튜토리얼 (/guide) 꾸밈 — 11/18, 11/26 A안 화면에 맞춤. 내용은 docs/guide.md */\n.pg-guide { max-width: 980px !important; }\n.pg-guide img { max-width: 100%; }\n.g-hero { margin: 8px 0 26px; padding: 30px 30px 26px; border-radius: 22px; color: #fff;\n  background: linear-gradient(135deg, #14b8a6 0%, #0f8f82 60%, #0b6f66 100%); box-shadow: 0 10px 30px rgba(20,184,166,.25); }\n.g-hero-t { font-size: 2rem; font-weight: 900; letter-spacing: -.5px; }\n.g-hero-s { margin-top: 10px; font-size: 1.02rem; line-height: 1.7; opacity: .95; }\n.g-h2 { font-size: 1.45rem; font-weight: 900; margin: 6px 0 6px; display: flex; align-items: center; gap: 8px; }\n.g-h2 .mi { color: var(--accent); font-size: 1.6rem; }\n.g-h3 { font-size: 1.08rem; font-weight: 800; margin: 4px 0 8px; }\n.g-sub { color: #6B7672; font-size: .9rem; line-height: 1.7; margin: 4px 0 12px; }\n.g-lead { font-size: 1.02rem; line-height: 1.8; margin: 2px 0 14px; color: #2E3835; }\n.g-sec { margin: 34px 0 10px; padding-top: 26px; border-top: 1px solid #E6ECEA; }\n.g-img { width: 100%; border-radius: 16px; border: 1px solid #E3E9E7; box-shadow: 0 6px 22px rgba(0,0,0,.07); margin: 6px 0 16px; }\n.g-img.g-narrow { max-width: 620px; display: block; }\n/* 처음 3단계: 옆으로 넘기는 배너 */\n.g-slides { display: flex; gap: 16px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px 2px 14px; margin-bottom: 26px; }\n.g-slide { flex: 0 0 78%; scroll-snap-align: start; background: #F6F8F7; border-radius: 18px; padding: 14px; box-sizing: border-box; }\n.g-slide img { width: 100%; height: 260px; object-fit: contain; object-position: center; background: #fff; border-radius: 12px; border: 1px solid #E3E9E7; }\n.g-slide-t { margin-top: 12px; font-size: 1.1rem; font-weight: 900; display: flex; align-items: center; gap: 8px; }\n.g-slide-t b { display: inline-flex; width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: #fff;\n  align-items: center; justify-content: center; font-size: .95rem; }\n.g-slide-s { margin-top: 6px; color: #4B5653; line-height: 1.7; font-size: .93rem; }\n/* 바로가기 */\n.g-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 8px 0 10px; }\n.g-nav a { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-radius: 14px; background: #fff; border: 1px solid #E3E9E7;\n  color: #26302D !important; text-decoration: none !important; font-weight: 700; font-size: .92rem; transition: all .15s ease; }\n.g-nav a:hover { border-color: var(--accent); background: #F0FBF9; }\n.g-nav a .mi { color: var(--accent-deep); font-size: 1.3rem; }\n/* 그림 + 글 나란히 */\n.g-row { display: grid; grid-template-columns: 1.2fr 1fr; gap: 22px; align-items: center; margin: 14px 0; }\n.g-row img { width: 100%; border-radius: 14px; border: 1px solid #E3E9E7; box-shadow: 0 4px 16px rgba(0,0,0,.06); }\n.g-row img.g-small { max-width: 300px; justify-self: center; }\n.g-row p { line-height: 1.8; margin: 0 0 8px; }\n.g-steps { margin: 0; padding-left: 0 !important; list-style: none; counter-reset: s; }\n.g-steps li { counter-increment: s; position: relative; padding: 6px 0 6px 38px; line-height: 1.7; list-style: none; }\n.g-steps li::before { content: counter(s); position: absolute; left: 0; top: 6px; width: 26px; height: 26px; border-radius: 50%;\n  background: var(--accent-soft); color: var(--accent-deep); font-weight: 900; display: flex; align-items: center; justify-content: center; font-size: .85rem; }\n/* 알림 상자: 글이 칸으로 쪼개지지 않게 아이콘만 왼쪽에 띄우고, 글씨는 작게 (11/18 요청) */\n.g-tip { display: block; position: relative; background: #FFF8E6; border: 1px solid #F6E2A8; border-radius: 14px;\n  padding: 10px 14px 10px 40px; line-height: 1.7; font-size: .82rem; margin: 10px 0; color: #4B4636; }\n.g-tip .mi { position: absolute; left: 13px; top: 10px; color: #E2A100; font-size: 1.1rem; }\n.g-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 12px; }\n.g-card { background: #F6F8F7; border-radius: 14px; padding: 14px; }\n.g-card .mi { color: var(--accent); font-size: 1.5rem; display: block; margin-bottom: 4px; }\n.g-card b { display: block; font-size: .95rem; }\n.g-card p { margin: 6px 0 0; font-size: .88rem; line-height: 1.6; color: #4B5653; }\ntable.g-table { width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #E3E9E7; border-radius: 14px; overflow: hidden;\n  margin: 8px 0 14px; font-size: .92rem; }\ntable.g-table th { background: #EAF8F5; color: var(--accent-deep); text-align: left; padding: 10px 14px; font-weight: 800; }\ntable.g-table td { padding: 10px 14px; border-top: 1px solid #EEF2F1; line-height: 1.6; vertical-align: top; }\n.g-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-weight: 800; font-size: .8rem; white-space: nowrap; }\n.g-badge.green { color: #0B5E57; background: #E6FBF7; }\n.g-badge.blue { color: #2C5BC5; background: #EAF0FC; }\n.g-badge.red { color: #C0313F; background: #FDECEE; }\n.g-badge.purple { color: #fff; background: #6C5CE7; }\n.g-badge.gray { color: #5F6B68; background: #F4F6F5; }\n/* 후기 도장 랭크 표의 작은 도장 (색은 common/stamp.py 의 테두리 · 바탕) */\n.g-rk { display: inline-block; width: 20px; height: 20px; border-radius: 50%; border: 3px solid #5FBF9F; background: #F0FAF6;\n  box-sizing: border-box; vertical-align: -5px; margin-right: 8px; }\n.g-rk.l2 { border-color: #21B287; background: #E9F7F2; }\n.g-rk.l3 { border-color: #2C5BC5; background: #EAF0FC; }\n.g-rk.l4 { border-color: #7656C4; background: #F1ECFF; }\n.g-rk.l5 { border-color: #C99A00; background: #FFF6D6; }\n/* 알림 시점 그래프 */\n.g-timeline { background: #F6F8F7; border-radius: 14px; padding: 14px 16px; margin: 4px 0 8px; }\n.g-tl-row { display: flex; align-items: center; gap: 12px; margin: 6px 0; }\n.g-tl-lab { width: 76px; font-weight: 800; font-size: .88rem; }\n.g-tl-bar { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }\n.g-tl-bar span { text-align: center; padding: 8px 0; border-radius: 10px; background: #D8F1EC; color: var(--accent-deep); font-weight: 800; font-size: .85rem; }\n.g-tl-bar span.hit { background: var(--accent); color: #fff; }\n.g-tl-bar span.hit.end { background: #D93A4A; }\n/* 등록 7단계 */\n.g-stepper { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin: 0 0 10px; }\n.g-stepper div { text-align: center; font-size: .78rem; color: #4B5653; font-weight: 700; background: #F6F8F7; border-radius: 12px; padding: 10px 4px; }\n.g-stepper b { display: flex; margin: 0 auto 6px; width: 26px; height: 26px; border-radius: 50%; background: var(--accent); color: #fff;\n  align-items: center; justify-content: center; }\n/* 삭제 요청 흐름 */\n.g-flow { display: flex; align-items: center; gap: 8px; }\n.g-flow div { flex: 1; background: #F6F8F7; border-radius: 14px; padding: 14px; font-size: .9rem; line-height: 1.6; text-align: center; }\n.g-flow div .mi { display: block; color: var(--accent); font-size: 1.6rem; margin-bottom: 4px; }\n.g-flow > i.mi { color: #B3BCB9; font-style: normal; font-size: 1.4rem; }\n.g-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 10px; }\n.g-chips span { background: #fff; border: 1px solid #DDE5E3; border-radius: 999px; padding: 4px 12px; font-size: .85rem; }\n.g-phones { display: flex; gap: 22px; justify-content: center; flex-wrap: wrap; }\n.g-phones figure { margin: 0; width: 260px; text-align: center; }\n.g-phones img { width: 100%; border-radius: 26px; border: 6px solid #26302D; box-shadow: 0 10px 26px rgba(0,0,0,.15); }\n.g-phones figcaption { margin-top: 10px; font-size: .88rem; line-height: 1.6; color: #4B5653; }\n.g-end { margin: 36px 0 10px; text-align: center; font-size: 1.05rem; padding: 18px; border-radius: 16px; background: #EAF8F5; }\n@media (max-width: 640px) {\n  .g-hero { padding: 22px 18px; }\n  .g-hero-t { font-size: 1.45rem; }\n  .g-slide { flex-basis: 88%; }\n  .g-slide img { height: 180px; }\n  .g-nav { grid-template-columns: repeat(2, 1fr); }\n  .g-row { grid-template-columns: 1fr; }\n  .g-cols { grid-template-columns: 1fr; }\n  .g-stepper { grid-template-columns: repeat(4, 1fr); }\n  .g-flow { flex-direction: column; }\n  .g-flow > i.mi { transform: rotate(90deg); }\n  .g-tl-lab { width: 60px; font-size: .8rem; }\n}\n\n/* 3단계 배너 ‹ › (_DRAG_JS 가 붙인다): 사진 가운데 높이 */\n.g-slides-wrap { position: relative; }\n.g-slides { cursor: grab; scroll-behavior: smooth; scrollbar-width: none; }\n.g-slides::-webkit-scrollbar { display: none; }\n.aw-dragging { cursor: grabbing !important; scroll-behavior: auto !important; user-select: none; }\n.aw-arrow { position: absolute; z-index: 8; width: 36px; height: 36px; border-radius: 50%; border: 1px solid #DDE5E3;\n  background: rgba(255,255,255,.95); box-shadow: 0 2px 8px rgba(0,0,0,.12); color: #26302D; font-size: 22px; line-height: 32px;\n  text-align: center; cursor: pointer; padding: 0; display: none; }\n.aw-arrow:hover { border-color: var(--accent); color: var(--accent-deep); }\n.aw-arrow.l { left: -8px; } .aw-arrow.r { right: -8px; }\n.aw-arrow.show { display: block; }\n";

export const ICON_NAMES: string[] = ["account_circle","add","add_circle","admin_panel_settings","arrow_forward","article","bookmark_add","bookmark_added","bookmarks","calendar_month","check_circle","close","delete","edit","error","event_note","expand_more","format_list_bulleted","forum","home","image","info","lightbulb","location_on","login","map","notifications","person","rate_review","search","send","shield","smartphone","tab","verified"];

export type DesignToken = { name: string; value: string | Record<string, string>; usage?: string };
export type DesignStyle = { name: string; fontSize: string; lineHeight: string | number; fontWeight: string | number; sample?: string; usage?: string };
export type DesignTokens = {
  color: { tokens: DesignToken[] };
  type: { families: Record<string, string>; groups: { name: string; family: string; styles: DesignStyle[] }[] };
  spacing: { tokens: DesignToken[] };
  radius: { tokens: DesignToken[] };
  shadow: { tokens: DesignToken[] };
};

export const DESIGN: { tokens: DesignTokens; readme: string; css: string; components: Record<string, string> } = {
 "tokens": {
  "name": "ANI:WHERE",
  "version": 1,
  "meta": {
   "source": "app",
   "ref": "main@f3b24b7",
   "package": ".",
   "paths": {
    "tokens": [
     "app_cafemap.py (GLOBAL_CSS :root, MINT*, CITY_COLORS, GANTT_COLOR, LIST_CSS, STORY_CSS, HOME_CSS, A안 CSS)",
     "web/app/a-shell.css · a-home.css · a-browse.css · a-detail.css · a-member.css",
     "common/stamp.py (TIERS)"
    ],
    "fonts": [
     "app_cafemap.py GLOBAL_CSS @import (Jua · Pretendard · NanumSquareRound)"
    ],
    "assets": [
     "static/logo.png",
     "static/mascot.png",
     "static/ask_avatar.png",
     "static/default_poster.png"
    ],
    "docs": [
     "CLAUDE.md",
     "README.md",
     "docs/guide.md",
     "docs/design/handoff/README.md"
    ]
   },
   "synced": "2026-11-26"
  },
  "color": {
   "themes": [
    {
     "id": "light",
     "name": "Light"
    }
   ],
   "tokens": [
    {
     "name": "accent",
     "value": "#14b8a6",
     "usage": "포인트 색. 등록·저장 같은 주 버튼 바탕, 아이콘, 진행 중 상태, 선택된 칩 테두리. 흰 바탕 위 작은 글자로는 쓰지 않는다 (명암 2.5:1)."
    },
    {
     "name": "accent-deep",
     "value": "#0d9488",
     "usage": "포인트 글자. 물어보기 제목, 선택된 이름, 숫자 강조. 흰 바탕 위 3.7:1 이라 굵게(700 이상) 또는 18px 이상에서만."
    },
    {
     "name": "accent-soft",
     "value": "#e6fbf7",
     "usage": "포인트 옅은 바탕. 선택된 줄, 오늘 칸, 진행 중 칩 바탕."
    },
    {
     "name": "accent-ink",
     "value": "#0b5e57",
     "usage": "진행 중 배지 글자, 고른 칩 · 특전 칩 글자. accent-soft 위 7:1 이라 작은 글자도 된다."
    },
    {
     "name": "logo-green",
     "value": "#21b287",
     "usage": "새 로고의 초록 (A안). 로고 그림과 후기 도장 Lv.2 테두리에만 쓴다 — 화면 포인트는 accent 그대로."
    },
    {
     "name": "mint",
     "value": "#56c2a7",
     "usage": "브랜드 민트. 카드 테두리 계열·서울 지역 배지 바탕. 흰 글자를 올리면 2.3:1 이라 굵은 짧은 배지 글자에만 (원본 값 유지, 주의)."
    },
    {
     "name": "mint-deep",
     "value": "#2e9c82",
     "usage": "민트 글자 (예전 카드 작품 이름). A안 카드 제목은 mint-ink 를 쓴다. 지금은 표지 · 보관함 제목에."
    },
    {
     "name": "mint-ink",
     "value": "#0f6b5c",
     "usage": "카드 작품 이름 (Jua 17px: 리스트 카드 · 사전예약 카드 · 내 캘린더 카드), 후기 도장 Lv.1 · Lv.2 글자. 흰 바탕 위 6.4:1."
    },
    {
     "name": "mint-soft",
     "value": "#e6f6f0",
     "usage": "배지·선택 상태처럼 좁은 곳의 민트 바탕."
    },
    {
     "name": "mint-line",
     "value": "#9eddcc",
     "usage": "포스터 카드 테두리 (2.5px), 메뉴바 프로필 동그라미 테두리 (2px). mint 보다 살짝 밝게."
    },
    {
     "name": "ink",
     "value": "#26302d",
     "usage": "본문 글자, 제목. surface 위 13:1."
    },
    {
     "name": "ink-strong",
     "value": "#1f2a27",
     "usage": "토스트 글자, 큰 제목처럼 가장 진한 글자."
    },
    {
     "name": "ink-soft",
     "value": "#5f6b68",
     "usage": "본문 보조 글자 (A안: 카드 둘째 줄, 장소 · 기간, 시간, 안 고른 탭), 종료 배지 글자. surface 위 5.5:1 이라 13px 글자도 된다."
    },
    {
     "name": "muted",
     "value": "#7b8784",
     "usage": "예전 화면의 보조 글자 (기간, 장소). surface 위 3.9:1 — A안 화면은 더 진한 ink-soft 를 쓴다."
    },
    {
     "name": "subtle",
     "value": "#9aa5a1",
     "usage": "가장 옅은 글자 (바닥글, 요일 날짜). 읽어야 하는 내용에는 쓰지 않는다 (2.6:1)."
    },
    {
     "name": "line",
     "value": "#e3e9e7",
     "usage": "카드·표·입력칸 테두리."
    },
    {
     "name": "line-soft",
     "value": "#eef2f1",
     "usage": "목록 줄 사이 구분선, 캘린더 칸 경계."
    },
    {
     "name": "surface",
     "value": "#ffffff",
     "usage": "페이지 바탕. 앱은 흰 바탕 + 포인트만 민트."
    },
    {
     "name": "surface-soft",
     "value": "#f6f8f7",
     "usage": "칸 바탕 (랭킹 목록, 후기 본문 상자, 튜토리얼 카드)."
    },
    {
     "name": "gray-soft",
     "value": "#f4f6f5",
     "usage": "이미지가 없는 칸, 업로드 칸, 알약 탭 묶음 바탕, 종료 배지 바탕."
    },
    {
     "name": "gnb",
     "value": "#e9f7f2",
     "usage": "맨 위 메뉴바 바탕 (연민트, 아래 모서리 28px 둥글게). 고른 탭은 이 위에 흰 알약."
    },
    {
     "name": "coral",
     "value": "#ff6b6b",
     "usage": "등록하기 + 떠 있는 버튼, 새 알림 빨간 점, '새 알림' 글자. 한 화면에 한 곳만."
    },
    {
     "name": "blue",
     "value": "#2c5bc5",
     "usage": "오픈 예정 D-n 배지 글자, 기대평 칩 글자, 후기 도장 Lv.3 테두리 · 글자."
    },
    {
     "name": "blue-soft",
     "value": "#eaf0fc",
     "usage": "D-n 배지 · 기대평 칩 바탕, 후기 도장 Lv.3 바탕."
    },
    {
     "name": "red",
     "value": "#d93a4a",
     "usage": "예전 화면의 마감임박 글자 (Streamlit 의 일부 예전 규칙). A안 배지는 red-deep."
    },
    {
     "name": "red-deep",
     "value": "#c0313f",
     "usage": "마감임박 · 종료 D-n 배지 글자 (A안), 삭제 요청 · 탈퇴하기 글자. red-soft 위 4.9:1. 상태 · 되돌리기 어려운 일에만."
    },
    {
     "name": "red-soft",
     "value": "#fdecee",
     "usage": "마감임박 · 종료 D-n 배지 바탕."
    },
    {
     "name": "purple",
     "value": "#6c5ce7",
     "usage": "사전예약 전용. 사전예약 D-n 배지 바탕 (흰 글자 4.9:1), 타임라인 첫 점, '사전예약 팝업만 보기' 버튼, 알림 버튼 테두리."
    },
    {
     "name": "purple-deep",
     "value": "#5b3fae",
     "usage": "사전예약 글자 (날짜 알약, '북마크하고 오픈 알림 받기', 요약 숫자), 후기 도장 Lv.4 글자."
    },
    {
     "name": "purple-soft",
     "value": "#f1ecff",
     "usage": "사전예약 요약 칸 바탕, 알림 버튼에 커서를 올렸을 때, 후기 도장 Lv.4 바탕."
    },
    {
     "name": "purple-line",
     "value": "#ddd3fb",
     "usage": "사전예약 타임라인 가로줄 (3px), 날짜 알약 테두리 (1.5px)."
    },
    {
     "name": "orange",
     "value": "#f2a33a",
     "usage": "예전 홈 '종료 D-n' 배지 바탕, 관리자 통계 막대. 흰 글자는 굵게 12px 이상 (2.2:1, 원본 값 유지). A안 화면의 종료 임박은 red-deep on red-soft."
    },
    {
     "name": "star",
     "value": "#f4b63f",
     "usage": "별점 채운 별."
    },
    {
     "name": "star-ink",
     "value": "#9a6a00",
     "usage": "후기 카드의 별 글자(★★★★☆), '기타' 칩 글자. 흰 바탕 위 4.7:1."
    },
    {
     "name": "gantt-plan",
     "value": "#3672bd",
     "usage": "관리자 간트 차트 '예정' 막대."
    },
    {
     "name": "gantt-live",
     "value": "{accent}",
     "usage": "관리자 간트 차트 '진행' 막대."
    },
    {
     "name": "gantt-end",
     "value": "#a9b3b0",
     "usage": "관리자 간트 차트 '종료' 막대."
    },
    {
     "name": "today",
     "value": "#e5484d",
     "usage": "간트 차트 오늘 선·칸, 오늘 표시 글자."
    },
    {
     "name": "rank-1-ring",
     "value": "#5fbf9f",
     "usage": "후기 도장 Lv.1 새싹 팬 (다녀온 후기 1개) 테두리."
    },
    {
     "name": "rank-1-fill",
     "value": "#f0faf6",
     "usage": "후기 도장 Lv.1 바탕 (32px 이상 도장, 'Lv.1' 알약)."
    },
    {
     "name": "rank-1-ink",
     "value": "{mint-ink}",
     "usage": "후기 도장 Lv.1 글자 ('Lv.1', 둘레 글자)."
    },
    {
     "name": "rank-2-ring",
     "value": "{logo-green}",
     "usage": "후기 도장 Lv.2 단골 팬 (다녀온 후기 3개) 테두리."
    },
    {
     "name": "rank-2-fill",
     "value": "#e9f7f2",
     "usage": "후기 도장 Lv.2 바탕 (32px 이상 도장, 'Lv.2' 알약)."
    },
    {
     "name": "rank-2-ink",
     "value": "{mint-ink}",
     "usage": "후기 도장 Lv.2 글자 ('Lv.2', 둘레 글자)."
    },
    {
     "name": "rank-3-ring",
     "value": "{blue}",
     "usage": "후기 도장 Lv.3 성지순례러 (다녀온 후기 10개) 테두리."
    },
    {
     "name": "rank-3-fill",
     "value": "{blue-soft}",
     "usage": "후기 도장 Lv.3 바탕 (32px 이상 도장, 'Lv.3' 알약)."
    },
    {
     "name": "rank-3-ink",
     "value": "{blue}",
     "usage": "후기 도장 Lv.3 글자 ('Lv.3', 둘레 글자)."
    },
    {
     "name": "rank-4-ring",
     "value": "#7656c4",
     "usage": "후기 도장 Lv.4 덕질 마스터 (다녀온 후기 25개) 테두리."
    },
    {
     "name": "rank-4-fill",
     "value": "{purple-soft}",
     "usage": "후기 도장 Lv.4 바탕 (32px 이상 도장, 'Lv.4' 알약)."
    },
    {
     "name": "rank-4-ink",
     "value": "{purple-deep}",
     "usage": "후기 도장 Lv.4 글자 ('Lv.4', 둘레 글자)."
    },
    {
     "name": "rank-5-ring",
     "value": "#c99a00",
     "usage": "후기 도장 Lv.5 전설의 덕후 (다녀온 후기 50개) 테두리."
    },
    {
     "name": "rank-5-fill",
     "value": "#fff6d6",
     "usage": "후기 도장 Lv.5 바탕 (32px 이상 도장, 'Lv.5' 알약)."
    },
    {
     "name": "rank-5-ink",
     "value": "#7a5a00",
     "usage": "후기 도장 Lv.5 글자 ('Lv.5', 둘레 글자)."
    },
    {
     "name": "city-seoul",
     "value": "{mint}",
     "usage": "지역 배지: 서울 (시마다 다른 색, 포스터 위에서는 진하게 채움)."
    },
    {
     "name": "city-busan",
     "value": "#3b82c4",
     "usage": "지역 배지: 부산."
    },
    {
     "name": "city-incheon",
     "value": "#8b6cd1",
     "usage": "지역 배지: 인천."
    },
    {
     "name": "city-daegu",
     "value": "#e0884a",
     "usage": "지역 배지: 대구."
    },
    {
     "name": "city-daejeon",
     "value": "#d9a400",
     "usage": "지역 배지: 대전."
    },
    {
     "name": "city-gwangju",
     "value": "#4ca36a",
     "usage": "지역 배지: 광주."
    },
    {
     "name": "city-ulsan",
     "value": "#2ba3b5",
     "usage": "지역 배지: 울산."
    },
    {
     "name": "city-jeju",
     "value": "#f2789b",
     "usage": "지역 배지: 제주."
    },
    {
     "name": "city-sejong",
     "value": "#7f8c3a",
     "usage": "지역 배지: 세종."
    },
    {
     "name": "city-suwon",
     "value": "#e06c6c",
     "usage": "지역 배지: 수원."
    },
    {
     "name": "city-goyang",
     "value": "#5a7bd8",
     "usage": "지역 배지: 고양."
    },
    {
     "name": "city-seongnam",
     "value": "#b0639e",
     "usage": "지역 배지: 성남. 목록에 없는 시는 이름으로 8가지 보조 색 중 하나."
    }
   ]
  },
  "type": {
   "fonts": [],
   "families": {
    "display": "\"Jua\", \"Pretendard\", sans-serif",
    "body": "\"NanumSquareRound\", \"Pretendard\", -apple-system, \"Apple SD Gothic Neo\", \"Malgun Gothic\", sans-serif",
    "icon": "\"Material Symbols Rounded\""
   },
   "groups": [
    {
     "name": "Display",
     "family": "display",
     "styles": [
      {
       "name": "page-title",
       "fontSize": "32px",
       "lineHeight": "1.15",
       "fontWeight": 400,
       "sample": "관리자 대시보드",
       "usage": "화면 제목 (관리자, 보관함)."
      },
      {
       "name": "section-title",
       "fontSize": "22px",
       "lineHeight": "1.3",
       "fontWeight": 400,
       "sample": "방문 전 확인",
       "usage": "상세 칸 제목, 빈 화면 제목."
      },
      {
       "name": "card-title",
       "fontSize": "17px",
       "lineHeight": "1.25",
       "fontWeight": 400,
       "sample": "치이카와 팝업 스토어",
       "usage": "카드 작품 이름 (리스트 · 사전예약 · 내 캘린더). 색은 mint-ink."
      }
     ]
    },
    {
     "name": "Text",
     "family": "body",
     "styles": [
      {
       "name": "home-heading",
       "fontSize": "19px",
       "lineHeight": "1.3",
       "fontWeight": 800,
       "sample": "따끈따끈 신규 등록 팝업",
       "usage": "홈 칸 제목 (앞에 포인트 색 아이콘)."
      },
      {
       "name": "body",
       "fontSize": "15px",
       "lineHeight": "1.6",
       "fontWeight": 400,
       "sample": "북마크한 팝업은 오픈·종료 3일 전부터 알려 드려요.",
       "usage": "본문, 안내 문장."
      },
      {
       "name": "nav-tab",
       "fontSize": "15px",
       "lineHeight": "1.2",
       "fontWeight": 600,
       "sample": "리스트로 보기",
       "usage": "메뉴바 탭. 고른 탭은 800 + 흰 알약 (밑줄 없음)."
      },
      {
       "name": "small",
       "fontSize": "13px",
       "lineHeight": "1.5",
       "fontWeight": 400,
       "sample": "애니메이트 카페 홍대점 · 12.11 ~ 01.10",
       "usage": "카드 둘째 줄, 장소·기간. 색은 ink-soft."
      },
      {
       "name": "badge",
       "fontSize": "12px",
       "lineHeight": "1.2",
       "fontWeight": 800,
       "sample": "마감임박",
       "usage": "상태 배지, 지역 배지."
      },
      {
       "name": "caption",
       "fontSize": "12px",
       "lineHeight": "1.6",
       "fontWeight": 400,
       "sample": "© 2026 ANI:WHERE",
       "usage": "바닥글, 도움말."
      }
     ]
    }
   ]
  },
  "spacing": {
   "tokens": [
    {
     "name": "space-1",
     "value": "4px",
     "usage": "아이콘과 글자 사이."
    },
    {
     "name": "space-2",
     "value": "8px",
     "usage": "칩 사이, 동그라미(스토리) 사이."
    },
    {
     "name": "space-3",
     "value": "12px",
     "usage": "카드 사이(추천 줄), 배너 안쪽 글 사이."
    },
    {
     "name": "space-4",
     "value": "16px",
     "usage": "카드 안 여백, 화면 옆 여백(모바일)."
    },
    {
     "name": "space-5",
     "value": "22px",
     "usage": "홈 칸 제목 위."
    },
    {
     "name": "space-6",
     "value": "28px",
     "usage": "상세 아래 추천 줄 위, 큰 묶음 사이."
    }
   ]
  },
  "size": {
   "tokens": [
    {
     "name": "page-max",
     "value": "1232px",
     "usage": "페이지 폭 (가운데 정렬, 양옆 24px · 모바일 16px). 지도로 보기만 화면 폭 전체."
    },
    {
     "name": "gnb-height",
     "value": "76px",
     "usage": "메뉴바 최소 높이. 로고 52px (모바일 44px)."
    },
    {
     "name": "btn-sm",
     "value": "40px",
     "usage": "작은 알약 버튼 (사전예약 '오픈 알림 받기', 달력 ‹ ›)."
    },
    {
     "name": "btn-round",
     "value": "44px",
     "usage": "메뉴바 동그란 버튼 (검색 · 알림 · 프로필), 상세의 공유 · 북마크, 답글 버튼."
    },
    {
     "name": "btn-lg",
     "value": "46px",
     "usage": "주 버튼 (저장하기, 리뷰 등록, N건 더보기)."
    },
    {
     "name": "calendar-width",
     "value": "400px",
     "usage": "내 캘린더의 달력 칸 폭 (목록 칸이 나머지를 넓게 쓴다)."
    },
    {
     "name": "stamp",
     "value": "20px · 32px · 40px · 96px",
     "usage": "후기 도장 크기: 리뷰 닉네임 옆 · 리뷰 쓰기 칸 · 다녀온 팝업 카드 · 마이페이지 대표."
    }
   ]
  },
  "radius": {
   "tokens": [
    {
     "name": "radius-sm",
     "value": "8px",
     "usage": "카드 위 북마크 버튼 (34px), 작은 칩, 입력칸 안 버튼."
    },
    {
     "name": "radius-md",
     "value": "12px",
     "usage": "포스터 카드, 리뷰 상자, 후기 카드 안 팝업 줄, 상세 북마크 버튼."
    },
    {
     "name": "radius-card",
     "value": "16px",
     "usage": "글이 든 카드 (사전예약 카드, 후기 카드, 내 캘린더 목록 카드, 지도 말풍선)."
    },
    {
     "name": "radius-lg",
     "value": "18px",
     "usage": "랭킹 배너, 랭킹 목록, 사전예약 칸, 상세의 리뷰 · 수정하기 칸 묶음, 튜토리얼 카드."
    },
    {
     "name": "radius-panel",
     "value": "22px",
     "usage": "마이페이지 칸 (프로필 · 내 후기 도장 · 설정), 랭크 안내 칸."
    },
    {
     "name": "radius-gnb",
     "value": "28px",
     "usage": "메뉴바 아래 두 모서리 (모바일 24px)."
    },
    {
     "name": "radius-pill",
     "value": "999px",
     "usage": "배지, 칩, 알약 탭, 알약 버튼, 스토리 동그라미, 후기 도장."
    }
   ]
  },
  "shadow": {
   "tokens": [
    {
     "name": "shadow-card",
     "value": "0 2px 10px rgba(0,0,0,0.06)",
     "usage": "후기 카드, 고른 랭킹 줄."
    },
    {
     "name": "shadow-float",
     "value": "0 4px 14px rgba(0,0,0,0.14)",
     "usage": "떠 있는 버튼(등록 +, 물어보기), 붙는 아이콘."
    },
    {
     "name": "shadow-banner",
     "value": "0 10px 30px rgba(0,0,0,0.4)",
     "usage": "랭킹 배너 안 포스터."
    }
   ]
  }
 },
 "readme": "# ANI:WHERE\n\n애니 팝업 · 콜라보 카페 · 굿즈 행사를 **찾고, 북마크하고, 놓치지 않게** 돕는 지도 서비스의 디자인 시스템.\n흰 바탕 위에 포인트만 우유빛 민트, 둥근 글꼴, 포스터가 주인공인 카드. 실제 화면 코드(앱 `app_cafemap.py`, 공개 웹 `web/app/a-*.css`)에서 값을 그대로 옮겼다.\n2026.11.25~26 에 확정 시안(A안)대로 두 서비스의 화면을 바꿨고, 이 문서는 **바뀐 뒤의 화면** 기준이다.\n\n## A안에서 바뀐 점 (2026.11.26 기준)\n\n- **로고 · 마스코트**: 새 로고(`logo.png`)와 토끼 마스코트(`mascot.png`). 예전 민트 로고 · 보조 로고는 화면에서 쓰지 않아 목록에서 뺐다.\n- **메뉴바**: 연민트 바탕 + 알약 탭(고른 탭 = 흰 알약). 검색 · 알림 · 프로필 · 로그인은 평소 투명, 커서를 올렸을 때만 흰 바탕.\n- **홈**: 칸마다 모양이 다르다 — 동그라미 줄(북마크 팝업, 예전 모양 그대로) · 랭킹 배너(그대로) · 신규 등록 가로 넘기기 + `더보기` 카드 · 곧 끝나는 팝업 7일 칸 · **사전예약 타임라인(보라)** · **후기 모음 3칸 열**.\n- **리스트 · 지도**: 포스터 아래에 글자를 두는 새 카드(마우스를 올리면 캐릭터 · 주소 · 특전), 걸린 필터 칩, 지도는 3단(데일리 팝업 노트 · 지도 · 물어보기).\n- **상세**: 위는 사진 + 정보 2단, 아래는 화면 폭 전체 탭 `리뷰 · 블로그 후기 · 수정하기`.\n- **내 캘린더 · 마이페이지**: 달력은 작게(400px) 목록은 넓게, 마이페이지가 새로 생겼다.\n- **후기 도장 랭크(새 기능)**: 다녀온 후기가 있는 팝업 수로 5단계. 색은 `rank-*` 토큰, 모양은 컴포넌트 RankStamp.\n- **새 토큰**: 보라 계열(`purple-deep` · `purple-soft` · `purple-line`), `logo-green`, `accent-ink`, `mint-ink`, `ink-soft`, `red-deep`, `star-ink`, `rank-1~5`, 모서리 `radius-card` · `radius-panel` · `radius-gnb`, 크기(`size`).\n- **새 컴포넌트 문서**: 알약 탭 · 메뉴바(PillTabs), 후기 도장(RankStamp), 사전예약 타임라인(PreTimeline), 후기 카드(ReviewCard). 배지 · 버튼 · 포스터 카드 · 동그라미 · 칩은 지금 화면에 맞게 고쳤다.\n\n## 말투 (콘텐츠 기본)\n\n- **친절한 존댓말, 짧게.** \"~해요 / ~예요\". 초등학생도 알아듣는 말로. 예: \"북마크한 팝업은 오픈·종료 3일 전부터 알려 드려요.\"\n- **사용자 쪽 말로 이름 짓기.** 기능 이름이 아니라 하는 일: `최애 추가하기`, `N건 더보기`, `팝업 N곳 표시`, `북마크하고 오픈 알림 받기`.\n- **안 될 때는 이유와 다음 할 일.** \"이 조건엔 행사가 없어요\" + `검색어 지우기 (12곳)` 버튼. 빈 표를 보여 주지 않는다.\n- **이모지 대신 아이콘.** 버튼·안내에는 Material Symbols Rounded (`:material/…:`, HTML 안에서는 `<span class=\"mi\">이름</span>`).\n- **숫자는 규칙으로 센 것만.** 물어보기 답의 건수·날짜는 `accent-deep` 굵게. AI 가 만든 글이면 'AI 산출', 규칙이면 '규칙 기반 대체' 를 기록에 남긴다.\n- **없는 것을 약속하지 않는다.** 후기 도장 랭크가 오르면 도장 색만 바뀐다 — 그 밖의 혜택을 화면에 쓰지 않는다. 사전예약 타임라인의 날짜는 팝업 오픈일이다(예약 오픈 시각은 데이터에 없다).\n- 버튼·링크에 마우스를 올리면 뜨는 설명(`title`)은 쓰지 않는다. 설명은 제목·입력칸 옆 `?` 로만.\n\n## 색\n\n| 역할 | 토큰 | 쓰는 곳 |\n| --- | --- | --- |\n| 바탕 | `surface`, `surface-soft`, `gray-soft` | 페이지는 흰색. 칸·상자는 `surface-soft`, 알약 탭 판은 `gray-soft` |\n| 글자 | `ink`, `ink-soft`, `muted`, `subtle` | 본문 `ink`, 장소·기간·시간 `ink-soft`, 바닥글 `subtle`. `muted` 는 예전 화면의 보조 글자 |\n| 포인트 | `accent`, `accent-deep`, `accent-soft`, `accent-ink` | 주 버튼·아이콘 `accent`, 포인트 글자 `accent-deep`, 고른 줄·오늘 칸 `accent-soft`, 그 위 글자 `accent-ink` |\n| 브랜드 민트 | `mint`, `mint-ink`, `mint-soft`, `mint-line`, `logo-green` | 포스터 카드 테두리 `mint-line`, 카드 작품 이름 `mint-ink`, 로고 초록 `logo-green` |\n| 메뉴바 | `gnb` | 맨 위 메뉴바 바탕 하나에만. 고른 탭은 흰 알약 |\n| 강조 하나 | `coral` | 등록하기 + 떠 있는 버튼, 새 알림 점. 한 화면에 한 곳 |\n| 상태 | `blue`/`blue-soft` 오픈 예정 · `red-deep`/`red-soft` 마감임박 · `ink-soft`/`gray-soft` 종료 | 상태에만 쓴다. 장식으로 쓰지 않는다 |\n| 사전예약 | `purple`, `purple-deep`, `purple-soft`, `purple-line` | 사전예약 배지 · 타임라인 · 알림 버튼에만. 다른 곳에 보라를 쓰지 않는다 |\n| 후기 도장 랭크 | `rank-1` ~ `rank-5` 의 `-ring` · `-fill` · `-ink` | 도장 테두리 · 바탕 · 글자. 초록 → 진한 초록 → 파랑 → 보라 → 금색 |\n| 지역 | `city-*` | 지역 배지. 시마다 다른 색, 포스터 위에서는 진하게 채우고 흰 테두리 |\n\n명암: `ink` 는 흰 바탕 위 13:1, `ink-soft` 5.5:1, `mint-ink` 6.4:1, `accent-ink` 는 `accent-soft` 위 7.1:1 — 작은 글자에도 쓴다. `accent` · `mint` · `orange` 위의 흰 글자와 `muted` · `subtle` 글자는 4.5:1 이 안 된다(원본 값 그대로 둠) — 굵은 짧은 배지 글자나 큰 글자에만 쓰고, 읽어야 하는 문장은 `ink` 로.\n\n로고의 초록(`logo-green` #21b287)과 화면 포인트(`accent` #14b8a6)는 서로 다른 색이다. 하나로 맞출지는 아직 정하지 않았다 — 지금은 화면 포인트에 `accent` 만 쓴다.\n\n## 글꼴\n\n- **제목** `display` (Jua): 화면 제목, 칸 제목, 카드 작품 이름(17px). 둥글고 귀여운 애니 느낌을 맡는다.\n- **본문** `body` (NanumSquareRound → Pretendard): 나머지 전부. 메뉴바 탭, 버튼, 배지까지.\n- **아이콘** `icon` (Material Symbols Rounded): 글자와 같은 색·크기를 따른다.\n- 홈 칸 제목은 `home-heading`(본문 글꼴 800) + 앞에 `accent` 아이콘.\n- 후기 도장의 둘레 글자 · 단계 숫자만 Titan One (없으면 Jua).\n\n## 모양 · 간격\n\n- 둥글게: 포스터 카드 `radius-md`(12px), 글이 든 카드 `radius-card`(16px), 배너·큰 칸 `radius-lg`(18px), 마이페이지 칸 `radius-panel`(22px), 메뉴바 아래 `radius-gnb`(28px), 배지·칩·알약 탭·알약 버튼·도장 `radius-pill`.\n- 포스터가 주인공: 리스트 카드는 포스터(3:4)를 크게 두고 글자는 그 **아래** 두 줄. 배지는 포스터 위 모서리에 — 왼쪽 위 상태, 오른쪽 위 지역, 오른쪽 아래 북마크.\n- 그림자는 떠 있는 것에만: `shadow-float`(등록 + · 물어보기 버튼), `shadow-card`(고른 랭킹 줄). 평평한 카드에는 테두리(`mint-line` 2.5px 또는 `line` 1.5px).\n- 간격은 `space-*` 단계로. 홈 칸 사이 `space-5`, 카드 사이 `space-3`~`space-4`.\n\n| 크기 | 값 | 쓰는 곳 |\n| --- | --- | --- |\n| `page-max` | 1232px | 페이지 폭 (양옆 24px, 모바일 16px). 지도로 보기만 화면 폭 전체 |\n| `gnb-height` | 76px | 메뉴바 높이. 로고 52px (모바일 44px) |\n| `btn-lg` | 46px | 주 버튼 (저장하기, 리뷰 등록, N건 더보기) |\n| `btn-round` | 44px | 메뉴바 동그란 버튼, 상세의 공유 · 북마크 |\n| `btn-sm` | 40px | 작은 알약 버튼 (오픈 알림 받기, 걸린 필터 칩) |\n| `calendar-width` | 400px | 내 캘린더의 달력 칸 |\n| `stamp` | 20 · 32 · 40 · 96px | 후기 도장 (닉네임 옆 · 리뷰 쓰기 칸 · 다녀온 팝업 카드 · 마이페이지) |\n\n## 배지 뜻 (어디서나 같게)\n\n| 글자 | 색 | 뜻 |\n| --- | --- | --- |\n| `진행 중` | `accent-ink` on `accent-soft` | 지금 열려 있음 |\n| `D-n` | `blue` on `blue-soft` | n일 뒤에 열림 |\n| `마감임박` | `red-deep` on `red-soft` | 3일 안에 끝남 |\n| `종료 D-n` | `red-deep` on `red-soft` | n일 뒤에 끝남 (내 캘린더 '곧 있는 팝업') |\n| `종료` | `ink-soft` on `gray-soft` | 끝났음 |\n| `사전예약 D-n` | 흰 글자 on `purple` | 예약해야 들어감, n일 뒤 열림 |\n\n## 후기 도장 랭크\n\n| 랭크 | 다녀온 후기 | 도장 색 |\n| --- | --- | --- |\n| Lv.1 새싹 팬 | 1개 | 연한 초록 (`rank-1`) |\n| Lv.2 단골 팬 | 3개 | 진한 초록 (`rank-2`) |\n| Lv.3 성지순례러 | 10개 | 파랑 (`rank-3`) |\n| Lv.4 덕질 마스터 | 25개 | 보라 (`rank-4`) |\n| Lv.5 전설의 덕후 | 50개 | 금색 (`rank-5`) |\n\n도장 수 = 내가 '다녀온 후기'를 남긴 팝업 수. 별점만 남겨도 1개, 같은 팝업은 1개, 기대평 · 답글 · 지운 후기는 세지 않는다. 값의 원본은 `common/stamp.py`(웹 `web/lib/stamp.ts` 와 같은 표).\n\n## 아이콘 (Iconography)\n\nMaterial Symbols Rounded 만 쓴다. 자주 쓰는 것: `bookmark_add` / `bookmark_added`(북마크), `map`, `format_list_bulleted`, `calendar_month`, `search`, `notifications`, `location_on`, `local_fire_department`(랭킹), `fiber_new`(신규), `hourglass_bottom`(곧 끝나는), `event_available`(사전예약), `rate_review`(후기), `auto_awesome`(비슷한 팝업), `add`(등록·최애 추가), `edit`(수정하기). 아이콘은 혼자 뜻을 나르지 않는다 — 늘 글자와 함께.\n\n## 로고 · 그림\n\n- **기본 로고** `logo.png`: 메뉴바 왼쪽에 두고, 누르면 홈. 메뉴바에서는 높이 52px(모바일 44px).\n- **로고는 높이 32px 이상에서만** 쓴다. 그보다 작은 자리(앱 아이콘, 파비콘, 도장, 물어보기 버튼)에는 로고 대신 **마스코트만**(`mascot.png`) 쓴다.\n- **물어보기 도우미 얼굴** `ask_avatar.png`: 마스코트를 동그랗게 자른 그림. 물어보기 대화창의 말풍선 옆.\n- **기본 포스터** `default_poster.png`: 포스터가 없을 때 대신 보인다.\n- 로고 · 마스코트는 다시 그리거나 색을 바꾸지 않고 파일 그대로 쓴다. 연민트 메뉴바와 흰 바탕 위에 둔다.\n- 예전 로고(민트 로고 `logo_mint.png`, 보조 로고 `logo2.png`)는 A안부터 화면에서 쓰지 않는다. 새 화면 · 자료에 쓰지 않는다.\n\n## 계절 배경\n\n내 캘린더 화면에서만 3~5월 꽃잎 · 6~8월 잎사귀 · 9~11월 단풍 · 12~2월 눈이 천천히 떨어진다(작은 SVG, 클릭을 막지 않음, '동작 줄이기' 설정이면 끔).\n\n## 파일\n\n| 파일 | 내용 |\n| --- | --- |\n| `docs/design/README.md` | 이 안내서 (말투 · 색 · 글꼴 · 모양 · 배지 · 랭크 · 로고) |\n| `docs/design/tokens.json` | 색 · 글꼴 · 간격 · 크기 · 모서리 · 그림자 토큰 |\n| `docs/design/components/*.md` · `*.html` | 컴포넌트 9개의 쓰는 규칙과 정적 예시 + 표지 |\n| `static/design/components.css` · `cover.css` | 예시를 그리는 CSS (토큰 이름으로) |\n| `docs/design/handoff/` | A안 확정 시안 묶음 (화면 시안 · 예전 토큰 · 로고 원본) |\n\n앱의 `/design` 화면과 공개 웹의 `/design` 이 이 파일들을 읽어 그린다. 값은 여기 한 곳에서만 고친다.\n\n## 옮기지 않은 것 (Not synced)\n\n- 글꼴 파일: Jua 는 Google Fonts, NanumSquareRound · Pretendard 는 jsDelivr 의 CSS 로 불러온다. 파일은 저장소에 없어 `type.fonts` 는 비어 있고 이름만 `type.families` 에 있다.\n- 컴포넌트: 앱은 Streamlit(파이썬), 공개 웹은 Next.js 라 두 쪽이 함께 쓰는 컴포넌트 라이브러리가 없다. 아래 9개 카드는 두 화면의 CSS 를 보고 **손으로 옮긴 정적 모습**이다 (누르는 동작 없음).\n- 화면 전체 배치(홈 칸 순서, 지도 3단, 상세 2단 + 탭, 마이페이지): 컴포넌트가 아니라 화면이라 여기 두지 않았다. 모양은 사용자 튜토리얼(`/guide`)의 화면 그림과 `handoff/` 시안을 본다.\n- 다크 모드: 앱에 없어 테마는 Light 하나.\n",
 "css": "/* ANI:WHERE 정적 컴포넌트 모습 — app_cafemap.py · web/app/a-*.css 의 CSS 를 손으로 옮김 (토큰 이름으로). A안 (11/25~26) 기준 */\n.aw { font-family: var(--font-body); color: var(--ink); }\n.aw .mi { font-family: var(--font-icon); font-weight: normal; font-style: normal; line-height: 1; font-size: 1.15em;\n  display: inline-block; vertical-align: -0.15em; -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; }\n\n/* 배지 */\n.aw-badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: var(--radius-pill);\n  font-size: 12px; font-weight: 800; line-height: 1.5; white-space: nowrap; }\n.aw-badge.live { color: var(--accent-ink); background: var(--accent-soft); }\n.aw-badge.soon { color: var(--blue); background: var(--blue-soft); }\n.aw-badge.closing { color: var(--red-deep); background: var(--red-soft); }\n.aw-badge.ended { color: var(--ink-soft); background: var(--gray-soft); }\n.aw-badge.reserve { color: #ffffff; background: var(--purple); }\n.aw-badge.area { color: #ffffff; padding: 1px 9px; border: 1.5px solid rgba(255,255,255,.85); }\n\n/* 버튼 */\n.aw-btn { font-family: var(--font-body); font-size: 14px; font-weight: 700; border-radius: var(--radius-pill); height: 46px; padding: 0 24px;\n  box-sizing: border-box; border: 1px solid var(--line); background: var(--surface); color: var(--ink); display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }\n.aw-btn.primary { background: var(--accent); border-color: var(--accent); color: #ffffff; }\n.aw-btn.more { background: var(--gray-soft); border-color: var(--gray-soft); color: var(--ink-soft); }\n.aw-btn.tertiary { background: transparent; border-color: transparent; color: var(--ink-soft); padding: 0 6px; }\n.aw-btn.reserve { height: 40px; padding: 0 16px; font-size: 13px; font-weight: 800; border: 1.5px solid var(--purple); color: var(--purple-deep); }\n.aw-btn.reserve.on { background: var(--purple); color: #ffffff; }\n.aw-fab { width: 56px; height: 56px; border-radius: 50%; background: var(--coral); color: #ffffff; border: 0;\n  display: inline-flex; align-items: center; justify-content: center; box-shadow: var(--shadow-float); font-size: 28px; }\n.aw-bm { width: 34px; height: 34px; border-radius: var(--radius-sm); border: 0; display: inline-flex; align-items: center;\n  justify-content: center; font-size: 18px; color: var(--ink); background: rgba(255,255,255,.75); }\n.aw-bm.on { background: var(--accent); color: #ffffff; }\n\n/* 포스터 카드 (리스트로 보기) */\n.aw-card { width: 210px; display: flex; flex-direction: column; gap: 8px; }\n.aw-card .poster { position: relative; aspect-ratio: 3 / 4; border: 2.5px solid var(--mint-line); border-radius: var(--radius-md); overflow: hidden;\n  background: var(--gray-soft) center / cover no-repeat; box-sizing: border-box; }\n.aw-card .tl { position: absolute; left: 10px; top: 10px; }\n.aw-card .tr { position: absolute; right: 10px; top: 10px; }\n.aw-card .bm { position: absolute; right: 10px; bottom: 10px; }\n.aw-card .tip { position: absolute; left: 10px; bottom: 12px; max-width: calc(100% - 64px); padding: 2px 9px; border-radius: var(--radius-pill);\n  font-size: 12px; font-weight: 700; line-height: 1.5; color: var(--accent-ink); background: rgba(255,255,255,.92); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n.aw-card.hover .poster { border-color: var(--accent); box-shadow: 0 6px 18px rgba(0,0,0,.12); }\n.aw-card .over { position: absolute; left: 0; right: 0; bottom: 0; padding: 40px 12px 54px; color: #ffffff; font-size: 12px; line-height: 1.6;\n  background: linear-gradient(transparent, rgba(31,42,39,.86) 45%); display: flex; flex-direction: column; gap: 1px; }\n.aw-card .t { font-family: var(--font-display); font-size: 17px; line-height: 1.25; color: var(--mint-ink); }\n.aw-card .s { font-size: 13px; line-height: 1.5; color: var(--ink-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n\n/* 북마크 팝업 동그라미 (스토리) */\n.aw-story { display: inline-flex; flex-direction: column; align-items: center; width: 84px; padding-bottom: 6px; }\n.aw-story .ring { position: relative; width: 72px; height: 72px; border-radius: 50%; padding: 3px; box-sizing: border-box;\n  background: conic-gradient(from 210deg, var(--accent), #7fe0cf, #ffd66b, var(--accent)); }\n.aw-story .pic { width: 100%; height: 100%; border-radius: 50%; border: 3px solid #ffffff; box-sizing: border-box;\n  background: var(--gray-soft) center / cover no-repeat; }\n.aw-story .rg { position: absolute; left: 50%; bottom: -7px; transform: translateX(-50%); font-size: 10px; font-weight: 800;\n  color: #ffffff; background: var(--mint); padding: 1px 7px; border-radius: var(--radius-pill); border: 1.5px solid #ffffff; white-space: nowrap; }\n.aw-story .nm { margin-top: 10px; width: 84px; text-align: center; font-size: 12.5px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n.aw-story.add .ring { background: none; border: 2px dashed #d3dad8; display: flex; align-items: center; justify-content: center;\n  color: var(--accent-deep); font-size: 32px; }\n\n/* 칩 (지역 고르기 · 후기 종류 · 추천 질문) */\n.aw-chip { display: inline-flex; align-items: center; padding: 6px 14px; border-radius: var(--radius-pill); font-size: 13px; line-height: 1.5;\n  border: 1px solid var(--line); background: var(--surface); color: var(--ink); }\n.aw-chip.on { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-ink); font-weight: 700; }\n/* 걸린 필터 칩 (리스트 목록 위): 40px, 끝에 지우기 × */\n.aw-chip.filter { gap: 6px; height: 40px; padding: 0 14px; box-sizing: border-box; font-size: 13.5px; font-weight: 800; line-height: 1;\n  border: 1.5px solid var(--accent); background: var(--accent-soft); color: var(--accent-ink); }\n\n/* 알약 탭 (메뉴바 · 내 캘린더 목록) */\n.aw-gnb { display: flex; align-items: center; gap: 12px; min-width: 720px; min-height: 76px; padding: 12px 24px; box-sizing: border-box; background: var(--gnb);\n  border-radius: 0 0 var(--radius-gnb) var(--radius-gnb); }\n.aw-gnb .logo { height: 52px; width: auto; display: block; }\n.aw-gnb .tabs { display: flex; gap: 4px; margin: 0 auto; }\n.aw-gnb .tabs span { padding: 9px 18px; border-radius: var(--radius-pill); font-size: 15px; font-weight: 600; line-height: 1.3; white-space: nowrap; }\n.aw-gnb .tabs span.on { background: #ffffff; color: var(--ink-strong); font-weight: 800; }\n.aw-gnb .round { width: 44px; height: 44px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 20px; }\n.aw-gnb .round.hover { background: #ffffff; }\n.aw-gnb .me { width: 44px; height: 44px; border-radius: 50%; border: 2px solid var(--mint-line); box-sizing: border-box; background: var(--accent-soft);\n  display: inline-flex; align-items: center; justify-content: center; color: var(--mint); font-size: 26px; }\n.aw-tabs { display: flex; gap: 4px; padding: 4px; border-radius: var(--radius-pill); background: var(--gray-soft); width: 460px; max-width: 100%; box-sizing: border-box; }\n.aw-tabs span { flex: 1; text-align: center; padding: 12px 8px; border-radius: var(--radius-pill); font-size: 15px; color: var(--ink-soft); white-space: nowrap; }\n.aw-tabs span.on { background: #ffffff; color: var(--ink); font-weight: 800; }\n\n/* 후기 도장 (RankStamp) */\n.aw-stamp { display: inline-flex; align-items: center; justify-content: center; flex: none; border-radius: 50%; border-style: solid;\n  box-sizing: border-box; vertical-align: middle; }\n.aw-stamp img { width: 62%; height: auto; display: block; }\n.aw-stamp.s20 { width: 20px; height: 20px; border-width: 2px; background: #ffffff; }\n.aw-stamp.s32 { width: 32px; height: 32px; border-width: 2.5px; }\n.aw-stamp.s40 { width: 40px; height: 40px; border-width: 3px; }\n.aw-stamp.lv1 { border-color: var(--rank-1-ring); } .aw-stamp.lv2 { border-color: var(--rank-2-ring); } .aw-stamp.lv3 { border-color: var(--rank-3-ring); }\n.aw-stamp.lv4 { border-color: var(--rank-4-ring); } .aw-stamp.lv5 { border-color: var(--rank-5-ring); }\n.aw-stamp.s32.lv1, .aw-stamp.s40.lv1, .aw-rkchip.lv1 { background: var(--rank-1-fill); } .aw-stamp.s32.lv2, .aw-stamp.s40.lv2, .aw-rkchip.lv2 { background: var(--rank-2-fill); }\n.aw-stamp.s32.lv3, .aw-stamp.s40.lv3, .aw-rkchip.lv3 { background: var(--rank-3-fill); } .aw-stamp.s32.lv4, .aw-stamp.s40.lv4, .aw-rkchip.lv4 { background: var(--rank-4-fill); }\n.aw-stamp.s32.lv5, .aw-stamp.s40.lv5, .aw-rkchip.lv5 { background: var(--rank-5-fill); }\n.aw-rkchip { display: inline-flex; align-items: center; gap: 4px; padding: 1px 8px 1px 2px; border-radius: var(--radius-pill); font-size: 11.5px;\n  font-weight: 800; line-height: 1.4; white-space: nowrap; vertical-align: middle; }\n.aw-rkchip.lv1 { color: var(--rank-1-ink); } .aw-rkchip.lv2 { color: var(--rank-2-ink); } .aw-rkchip.lv3 { color: var(--rank-3-ink); }\n.aw-rkchip.lv4 { color: var(--rank-4-ink); } .aw-rkchip.lv5 { color: var(--rank-5-ink); }\n.aw-stamp-big { position: relative; display: inline-block; flex: none; width: 96px; height: 96px; }\n.aw-stamp-big svg { position: absolute; inset: 0; }\n.aw-stamp-big svg text { font-family: \"Titan One\", var(--font-display); }\n.aw-stamp-big > img { position: absolute; left: 50%; top: 50%; width: 41%; height: auto; transform: translate(-50%, -50%); }\n.aw-stamp-big .lv { position: absolute; right: -2px; bottom: 2px; min-width: 30px; height: 26px; padding: 0 6px; border-radius: var(--radius-pill);\n  border: 3px solid #ffffff; color: #ffffff; font-family: \"Titan One\", var(--font-display); font-size: 13px; line-height: 20px; text-align: center; box-sizing: border-box; }\n.aw-stamp-big.dim { filter: grayscale(1); opacity: .45; }\n.aw-stamps { display: flex; flex-wrap: wrap; gap: 18px; align-items: flex-end; }\n.aw-stamps figure { margin: 0; display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 12px; color: var(--ink-soft); }\n.aw-stamps figure b { color: var(--ink); font-size: 13px; }\n\n/* 사전예약 타임라인 항목 */\n.aw-pre { display: flex; gap: 14px; }\n.aw-pre .i { position: relative; flex: none; width: 220px; display: flex; flex-direction: column; gap: 10px; }\n.aw-pre .i::before { content: \"\"; position: absolute; left: 0; right: -14px; top: 43.5px; height: 3px; background: var(--purple-line); }\n.aw-pre .i:last-child::before { right: 0; }\n.aw-pre .date { position: relative; align-self: flex-start; height: 28px; display: inline-flex; align-items: center; padding: 0 10px; border-radius: var(--radius-pill);\n  box-sizing: border-box; font-size: 12.5px; font-weight: 800; color: var(--purple-deep); background: #ffffff; border: 1.5px solid var(--purple-line); white-space: nowrap; }\n.aw-pre .dot { position: relative; width: 14px; height: 14px; box-sizing: border-box; border-radius: 50%; background: #a99cf2; border: 3px solid #ffffff; box-shadow: 0 0 0 2px #a99cf2; margin-left: 12px; }\n.aw-pre .i.first .dot { background: var(--purple); box-shadow: 0 0 0 2px var(--purple); }\n.aw-pre .card { border: 1.5px solid var(--line); border-radius: var(--radius-card); overflow: hidden; background: #ffffff; }\n.aw-pre .pic { position: relative; aspect-ratio: 4 / 3; background: var(--gray-soft) center top / cover no-repeat; }\n.aw-pre .pic .aw-badge { position: absolute; left: 10px; top: 10px; }\n.aw-pre .txt { padding: 12px; display: flex; flex-direction: column; gap: 4px; }\n.aw-pre .t { font-family: var(--font-display); font-size: 17px; line-height: 1.25; color: var(--mint-ink); }\n.aw-pre .m { font-size: 12.5px; line-height: 1.5; color: var(--ink-soft); }\n.aw-pre .aw-btn { justify-content: center; }\n\n/* 후기 카드 (홈 후기 모음) */\n.aw-rv { flex: none; width: 300px; border: 1.5px solid var(--line); border-radius: var(--radius-card); background: #ffffff; padding: 14px; box-sizing: border-box;\n  display: flex; flex-direction: column; gap: 8px; }\n.aw-rv .kind { align-self: flex-start; font-size: 12px; font-weight: 800; line-height: 1.5; padding: 2px 10px; border-radius: var(--radius-pill);\n  color: var(--accent-ink); background: var(--accent-soft); }\n.aw-rv .kind.hope { color: var(--blue); background: var(--blue-soft); }\n.aw-rv .kind.etc { color: var(--star-ink); background: var(--rank-5-fill); }\n.aw-rv .who { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 800; }\n.aw-rv .av { width: 26px; height: 26px; border-radius: 50%; background: var(--accent-soft); display: inline-flex; align-items: center; justify-content: center; color: var(--mint); font-size: 18px; }\n.aw-rv .time { margin-left: auto; font-size: 12px; font-weight: 400; color: var(--ink-soft); }\n.aw-rv .stars { font-size: 12.5px; font-weight: 800; letter-spacing: 1px; color: var(--star-ink); }\n.aw-rv .body { font-size: 14px; line-height: 1.65; }\n.aw-rv .pop { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: var(--radius-md); background: var(--surface-soft); font-size: 13px; font-weight: 800; }\n.aw-rv .pop .pp { flex: none; width: 28px; height: 36px; border-radius: 6px; background: var(--gray-soft) center / cover no-repeat; }\n.aw-rv .pop .pn { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n.aw-rv .pop .aw-badge { font-size: 11.5px; padding: 1px 8px; }\n/* 표지 꾸밈 (docs/design/components/Cover.html) */\n.cv { position: relative; width: 960px; height: 300px; background: var(--surface); overflow: hidden; }\n    .cv svg { position: absolute; inset: 0; }\n    .cv .accent { fill: var(--accent); } .cv .deep { fill: var(--mint-deep); } .cv .coral { fill: var(--coral); }\n    .cv .tint { fill: var(--gnb); } .cv .line { fill: var(--mint-line); } .cv .soft { fill: var(--accent-soft); }\n    .cv .ring { fill: none; stroke: var(--surface); stroke-width: 3; }\n    .cv .slab { rx: var(--radius-lg); } .cv .pill { rx: 30px; }\n    .cv .txt { position: absolute; left: 48px; bottom: 44px; max-width: 440px; }\n    .cv .name { font-family: var(--font-display); font-size: 80px; line-height: .95; color: var(--ink); }\n    .cv .tag { margin-top: 12px; font-family: var(--font-body); font-size: 14px; color: var(--muted); }\n",
 "components": {
  "Badge.html": "<div class=\"aw\" style=\"display:flex;gap:8px;flex-wrap:wrap;padding:16px;align-items:center\"><span class=\"aw-badge live\">진행 중</span><span class=\"aw-badge soon\">D-5</span><span class=\"aw-badge closing\">마감임박</span><span class=\"aw-badge closing\">종료 D-7</span><span class=\"aw-badge ended\">종료</span><span class=\"aw-badge reserve\">사전예약 D-5</span><span style=\"display:inline-flex;gap:6px;padding:6px 8px;border-radius:10px;background:#8a9a96\"><span class=\"aw-badge area\" style=\"background:var(--city-busan)\">부산</span><span class=\"aw-badge area\" style=\"background:var(--city-seoul)\">마포</span></span></div>\n",
  "Badge.md": "# Badge\n\n팝업의 지금 상태나 지역을 짧게 알려 주는 알약 모양 표시.\n\n- 상태 배지는 포스터 왼쪽 위, 지역 배지는 오른쪽 위. 한 카드에 상태 하나, 지역 하나.\n- 뜻과 색은 어디서나 같게 (아래 줄은 '글자 on 바탕').\n- `진행 중` — `accent-ink` on `accent-soft`\n- `D-n` (n일 뒤 열림) — `blue` on `blue-soft`\n- `마감임박` (3일 안에 끝남) · `종료 D-n` (내 캘린더 '곧 있는 팝업') — `red-deep` on `red-soft`\n- `종료` — `ink-soft` on `gray-soft`\n- `사전예약 D-n` — 흰 글자 on `purple` (사전예약에만)\n- 글자 12px · 800, 안쪽 여백 2px 10px, 모서리 `radius-pill`.\n- 지역 배지 바탕은 `city-*` 토큰 (포스터 위에서는 진하게 채우고 흰 테두리 1.5px).\n- 쓰는 쪽이 정하는 것: 글자, 종류(live · soon · closing · ended · reserve · area).\n\n손으로 옮김: `app_cafemap.py` 의 `.ah-st`, `.cstate`, `_area_badge` · 웹 `a-home.css` 의 `.ah-st`, `a-browse.css` 의 `.bc-state` · `.bc-area`.\n",
  "Button.html": "<div class=\"aw\" style=\"display:flex;gap:10px;flex-wrap:wrap;padding:16px;align-items:center\"><span role=\"button\" class=\"aw-btn primary\"><span class=\"mi\">check_circle</span>저장하기</span><span role=\"button\" class=\"aw-btn\">되돌리기</span><span role=\"button\" class=\"aw-btn more\"><span class=\"mi\">expand_more</span>97건 더보기</span><span role=\"button\" class=\"aw-btn tertiary\">다음에 할게요</span><span role=\"button\" class=\"aw-btn reserve\"><span class=\"mi\">notifications</span>북마크하고 오픈 알림 받기</span><span role=\"button\" class=\"aw-fab\" aria-label=\"등록하기\"><span class=\"mi\">add</span></span><span style=\"display:inline-flex;gap:6px;padding:6px;border-radius:10px;background:#56c2a7\"><span role=\"button\" class=\"aw-bm\" aria-label=\"북마크\"><span class=\"mi\">bookmark_add</span></span><span role=\"button\" class=\"aw-bm on\" aria-label=\"북마크됨\"><span class=\"mi\">bookmark_added</span></span></span></div>\n",
  "Button.md": "# Button\n\n누르면 일이 일어나는 버튼. 글자는 하는 일 그대로 (`저장하기`, `최애 추가하기`, `97건 더보기`).\n\n- 모양은 알약(`radius-pill`). 높이는 세 가지: 주 버튼 46px(`btn-lg`), 작은 버튼 40px(`btn-sm`), 메뉴바 · 상세의 동그란 버튼 44px(`btn-round`).\n- `primary`(accent 바탕): 한 화면에서 가장 중요한 한 가지 (저장하기, 리뷰 등록).\n- 기본(흰 바탕 + line 테두리): 그 밖의 선택 (되돌리기, 프로필 수정).\n- `more`(gray-soft): 목록 아래 `N건 더보기` — 앞에 `expand_more` 아이콘.\n- `tertiary`: 글자만 (취소, 다음에 할게요, 더보기 링크).\n- `reserve`(보라 테두리 1.5px + `purple-deep` 글자): 사전예약 타임라인의 `북마크하고 오픈 알림 받기` 에만. 북마크한 뒤에는 `purple` 로 채우고 흰 글자.\n- 떠 있는 등록 버튼(FAB)은 `coral` 동그라미 하나, 화면 오른쪽 아래에만.\n- 북마크 버튼(카드 위 34px): 안 한 상태는 흰 바탕 75%, 한 상태는 accent 바탕 + 흰 아이콘.\n- 메뉴바의 검색 · 알림 · 프로필 · 로그인은 평소 바탕이 투명하고, 커서를 올렸을 때만 흰 바탕이 된다 (알약 탭 참고).\n- 버튼에 마우스를 올리면 뜨는 설명(title)은 쓰지 않는다.\n\n손으로 옮김: `app_cafemap.py` 의 `.st-key-add_btn`, `.st-key-list_more`, `[class*=st-key-fav_]`, `.st-key-ade_bar` · 웹 `a-browse.css` 의 `.btn-primary` · `.bm-card`, `a-home.css` 의 `.ah-pre-btn`.\n",
  "Chip.html": "<div class=\"aw\" style=\"display:flex;gap:6px;flex-wrap:wrap;padding:16px;align-items:center\"><span class=\"aw-chip on\">전체</span><span class=\"aw-chip\">다녀온 후기</span><span class=\"aw-chip\">기대평</span><span class=\"aw-chip\">기타</span><span class=\"aw-chip\">이번 주말 홍대 팝업</span><span class=\"aw-chip\">내 주변 가까운 팝업</span><span class=\"aw-chip filter\">마포 <span class=\"mi\">close</span></span><span class=\"aw-chip filter\">진행 중 <span class=\"mi\">close</span></span></div>\n",
  "Chip.md": "# Chip\n\n여러 개 중 하나를 고르거나, 눌러서 바로 물어보는 작은 알약.\n\n- 홈 칸의 지역 고르기(`전체 · 마포 · 부산 · 송파`), 후기 모음의 종류(`전체 · 다녀온 후기 · 기대평 · 기타`), 물어보기의 추천 질문.\n- 고른 칩: `accent` 테두리 + `accent-soft` 바탕 + `accent-ink` 굵은 글자.\n- 걸린 필터 칩(리스트 목록 위, 40px): 지금 걸려 있는 조건을 하나씩 보여 주고, 끝의 `close` 를 누르면 그 조건만 풀린다.\n- 한 줄에 다 안 들어가면 다음 줄로 넘긴다 (가로 스크롤 없음).\n\n손으로 옮김: `app_cafemap.py` 의 홈 `st.pills`, `.apn-chips` · 웹 `a-home.css` 의 `.ah-chip`, `a-browse.css` 의 `.fchip`.\n",
  "Cover.html": "<div class=\"cv\">\n  <svg viewBox=\"0 0 960 300\" width=\"960\" height=\"300\" aria-hidden=\"true\">\n    <!--\n      blocks: accent 200×240 slab (radius-lg) · mint-deep 240×120 slab bleeding right · gnb tint 240×140 slab · coral pill 120×60\n      arrangement: one tall slab with satellites, the slab and the deep block bleed off the top and right edges\n      pattern: discs from the radius scale (\"둥글고 귀여운\", 스토리 동그라미) — 12 mint-line discs on the tint block, 3 surface rings on the slab\n      steps/radii: radius-lg 18, radius-pill for the pill and discs (r = half the side), pitch 36 = space-3 × 3\n    -->\n    <rect class=\"accent slab\" x=\"520\" y=\"-24\" width=\"200\" height=\"244\" />\n    <rect class=\"deep slab\" x=\"740\" y=\"36\" width=\"244\" height=\"120\" />\n    <rect class=\"tint slab\" x=\"740\" y=\"172\" width=\"244\" height=\"150\" />\n    <rect class=\"coral pill\" x=\"560\" y=\"236\" width=\"120\" height=\"60\" />\n    <circle class=\"ring\" cx=\"580\" cy=\"64\" r=\"26\" /><circle class=\"ring\" cx=\"652\" cy=\"112\" r=\"26\" /><circle class=\"ring\" cx=\"580\" cy=\"160\" r=\"26\" />\n    <g class=\"line\">\n      <circle cx=\"772\" cy=\"204\" r=\"12\" /><circle cx=\"808\" cy=\"204\" r=\"12\" /><circle cx=\"844\" cy=\"204\" r=\"12\" /><circle cx=\"880\" cy=\"204\" r=\"12\" />\n      <circle cx=\"772\" cy=\"240\" r=\"12\" /><circle cx=\"808\" cy=\"240\" r=\"12\" /><circle cx=\"844\" cy=\"240\" r=\"12\" /><circle cx=\"880\" cy=\"240\" r=\"12\" />\n      <circle cx=\"772\" cy=\"276\" r=\"12\" /><circle cx=\"808\" cy=\"276\" r=\"12\" /><circle cx=\"844\" cy=\"276\" r=\"12\" /><circle cx=\"880\" cy=\"276\" r=\"12\" />\n    </g>\n  </svg>\n  <div class=\"txt\">\n    <div class=\"name\">ANI:WHERE</div>\n    <div class=\"tag\">함께 만드는 애니 팝업 지도. 찾고, 북마크하고, 놓치지 않게.</div>\n  </div>\n</div>\n",
  "PillTabs.html": "<div class=\"aw\" style=\"display:flex;flex-direction:column;gap:18px;padding:0 16px 16px\"><div class=\"aw-gnb\"><img class=\"logo\" src=\"/design/logo.png\" alt=\"ANI:WHERE\"><div class=\"tabs\"><span class=\"on\">홈</span><span>지도로 보기</span><span>리스트로 보기</span><span>내 캘린더</span></div><span class=\"round\"><span class=\"mi\">search</span></span><span class=\"round hover\"><span class=\"mi\">notifications</span></span><span class=\"me\"><span class=\"mi\">person</span></span></div><div class=\"aw-tabs\"><span class=\"on\">북마크 4</span><span>다녀온 팝업 3</span><span>최근 본</span></div></div>\n",
  "PillTabs.md": "# PillTabs\n\n화면이나 목록을 바꾸는 알약 탭. 고른 탭 하나만 흰 알약이 된다.\n\n- **메뉴바**: 바탕 `gnb`(연민트), 아래 두 모서리 `radius-gnb`(28px), 높이 76px, 로고 52px(모바일 44px). 탭 글자 15px · 600, 고른 탭은 흰 알약 + 800 (밑줄은 쓰지 않는다). 모바일은 탭이 한 줄을 나눠 쓴다(14px).\n- 메뉴바 오른쪽의 검색 · 알림 · 프로필은 44px 동그라미. 평소에는 바탕이 **투명**하고, 커서를 올렸을 때만 흰 바탕(위 그림의 종 모양)이 된다. 프로필 동그라미는 `mint-line` 2px 테두리. 로그인 전에는 그 자리에 글자 버튼 `로그인`.\n- **목록 탭**(내 캘린더의 `북마크 · 다녀온 팝업 · 최근 본`): `gray-soft` 알약 판 안에 같은 폭으로 나눈 탭, 고른 탭은 흰 알약 + 800, 나머지는 `ink-soft`.\n- 상세 아래쪽의 `리뷰 · 블로그 후기 · 수정하기` 는 알약이 아니라 **밑줄 탭**(고른 탭 아래 `accent` 줄)이다 — 화면 폭 전체를 쓰는 큰 묶음이라서.\n\n손으로 옮김: `app_cafemap.py` 의 `_gnb`, `.st-key-gnb_tabs`, `.st-key-box_tabs` · 웹 `a-shell.css` 의 `.gnb-tabs`, `a-member.css` 의 `.am-tabs`.\n",
  "PosterCard.html": "<div class=\"aw\" style=\"display:flex;gap:16px;padding:16px\"><div class=\"aw-card\"><div class=\"poster\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"tl aw-badge soon\">D-9</span><span class=\"tr aw-badge area\" style=\"background:var(--city-seoul)\">마포</span><span role=\"button\" class=\"bm aw-bm on\" aria-label=\"북마크됨\"><span class=\"mi\">bookmark_added</span></span></div><div class=\"t\">학원 아이돌마스터</div><div class=\"s\">애니메이트 카페 홍대점 · 12.05 ~ 12.27</div></div><div class=\"aw-card\"><div class=\"poster\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"tl aw-badge live\">진행 중</span><span class=\"tr aw-badge area\" style=\"background:var(--city-busan)\">부산</span><span class=\"tip\">사전 예약</span><span role=\"button\" class=\"bm aw-bm\" aria-label=\"북마크\"><span class=\"mi\">bookmark_add</span></span></div><div class=\"t\">승리의 여신: 니케</div><div class=\"s\">카카오프렌즈 센텀시티점 · 11.19 ~ 12.03</div></div><div class=\"aw-card hover\"><div class=\"poster\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"tl aw-badge live\">진행 중</span><span class=\"tr aw-badge area\" style=\"background:var(--city-busan)\">부산</span><div class=\"over\"><span>캐릭터 · 도로, 춘식</span><span>주소 · 부산 해운대구 센텀남대로 35</span><span>특전 · 구매 금액별 스티커</span></div><span role=\"button\" class=\"bm aw-bm\" aria-label=\"북마크\"><span class=\"mi\">bookmark_add</span></span></div><div class=\"t\">승리의 여신: 니케</div><div class=\"s\">카카오프렌즈 센텀시티점 · 11.19 ~ 12.03</div></div></div>\n",
  "PosterCard.md": "# PosterCard\n\n팝업 하나를 포스터로 보여 주는 리스트 카드. 누르면 상세가 열린다.\n\n- 포스터(3:4)는 테두리 `mint-line` 2.5px · 모서리 `radius-md`(12px). 글자는 포스터 **아래**에 두 줄: 작품 이름(`card-title`, Jua 17px, `mint-ink`, 두 줄까지) · 장소와 기간(13px, `ink-soft`, 한 줄).\n- 포스터 왼쪽 위 상태 Badge, 오른쪽 위 지역 Badge, 오른쪽 아래 북마크 버튼(34px). 왼쪽 아래에는 특전 · 이벤트 한 줄 칩(있을 때만).\n- 마우스를 올리면(세 번째 카드) 테두리가 `accent` 로 바뀌고, 포스터 아래쪽에 어두운 판이 올라와 **캐릭터 · 주소 · 특전**을 보여 준다. 터치 기기에서는 띄우지 않는다.\n- 포스터가 없으면 기본 포스터(`default_poster.png`).\n- 쓰는 쪽이 정하는 것: 포스터, 작품 이름, 장소, 기간, 상태, 지역, 북마크 여부, 겹침 판에 넣을 글.\n\n손으로 옮김: `app_cafemap.py` 의 `_poster_card`, `.pcard` · 웹 `a-browse.css` 의 `.bc`, `.bc-poster`, `.bc-over`, `.bc-title`.\n",
  "PreTimeline.html": "<div class=\"aw\" style=\"padding:16px\"><div class=\"aw-pre\"><div class=\"i first\"><span class=\"date\">11.28 (토) 팝업 오픈</span><span class=\"dot\"></span><div class=\"card\"><div class=\"pic\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"aw-badge reserve\">사전예약 D-2</span></div><div class=\"txt\"><div class=\"t\">아주르 프로밀리아</div><div class=\"m\">서초 · 11.28 ~ 11.29</div></div></div><span role=\"button\" class=\"aw-btn reserve\"><span class=\"mi\">notifications</span>북마크하고 오픈 알림 받기</span></div><div class=\"i\"><span class=\"date\">12.02 (수) 팝업 오픈</span><span class=\"dot\"></span><div class=\"card\"><div class=\"pic\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"aw-badge reserve\">사전예약 D-6</span></div><div class=\"txt\"><div class=\"t\">2026 월드웹툰페스티벌</div><div class=\"m\">코엑스 B홀 · 12.02 ~ 12.06</div></div></div><span role=\"button\" class=\"aw-btn reserve on\"><span class=\"mi\">notifications</span>오픈 알림 받는 중</span></div><div class=\"i\"><span class=\"date\">12.11 (금) 팝업 오픈</span><span class=\"dot\"></span><div class=\"card\"><div class=\"pic\" style=\"background-image:url(/design/default_poster.png)\"><span class=\"aw-badge reserve\">사전예약 D-15</span></div><div class=\"txt\"><div class=\"t\">슬램덩크</div><div class=\"m\">용산 아이파크몰 · 12.11 ~ 01.10</div></div></div><span role=\"button\" class=\"aw-btn reserve\"><span class=\"mi\">notifications</span>북마크하고 오픈 알림 받기</span></div></div></div>\n",
  "PreTimeline.md": "# PreTimeline\n\n홈 '사전예약 팝업' 칸의 타임라인 항목. 예약해야 들어갈 수 있는 팝업을 **팝업이 열리는 날** 순서로 한 줄에 놓는다.\n\n- 보라는 사전예약 전용이다: 가로줄 `purple-line` 3px, 날짜 알약(`purple-deep` 글자 · `purple-line` 테두리 1.5px), 점 14px(첫 항목만 `purple` 로 진하게).\n- 카드: `line` 테두리 1.5px · 모서리 `radius-card`(16px), 포스터 4:3, 왼쪽 위 `사전예약 D-n` Badge, 작품 이름(Jua 17px `mint-ink`), 장소 · 기간(12.5px `ink-soft`). 커서를 올리면 테두리가 `purple`.\n- 카드 아래 `북마크하고 오픈 알림 받기`(40px 보라 테두리 버튼) — 누르면 북마크되고, 팝업이 열리기 3일 전부터 알림이 온다. 북마크한 뒤에는 `purple` 로 채운다.\n- 왼쪽 요약 칸(`purple-soft` 바탕): 칸 이름 · 한 줄 설명 · `N곳 예약 대기` · `사전예약 팝업만 보기`.\n- 날짜는 팝업 오픈일이다. 예약이 열리는 시각 · 예약처는 데이터에 없어 보여 주지 않는다.\n\n손으로 옮김: `app_cafemap.py` 의 홈 사전예약 칸(`ah_pre`) · 웹 `a-home.css` 의 `.ah-pre*`.\n",
  "RankStamp.html": "<div class=\"aw\" style=\"display:flex;flex-direction:column;gap:22px;padding:18px 16px\"><div class=\"aw-stamps\"><figure><span class=\"aw-stamp-big\" role=\"img\" aria-label=\"Lv.1 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-1\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-1-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-1-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-1-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-1-ink)\"><textPath href=\"#aw-rk-ring-1\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.1 SPROUT ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-1-ring)\">1</span></span><b>Lv.1 새싹 팬</b><span>다녀온 후기 1개</span></figure><figure><span class=\"aw-stamp-big\" role=\"img\" aria-label=\"Lv.2 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-2\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-2-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-2-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-2-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-2-ink)\"><textPath href=\"#aw-rk-ring-2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.2 REGULAR ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-2-ring)\">2</span></span><b>Lv.2 단골 팬</b><span>다녀온 후기 3개</span></figure><figure><span class=\"aw-stamp-big\" role=\"img\" aria-label=\"Lv.3 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-3\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-3-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-3-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-3-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-3-ink)\"><textPath href=\"#aw-rk-ring-3\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.3 PILGRIM ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-3-ring)\">3</span></span><b>Lv.3 성지순례러</b><span>다녀온 후기 10개</span></figure><figure><span class=\"aw-stamp-big\" role=\"img\" aria-label=\"Lv.4 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-4\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-4-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-4-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-4-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-4-ink)\"><textPath href=\"#aw-rk-ring-4\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.4 MASTER ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-4-ring)\">4</span></span><b>Lv.4 덕질 마스터</b><span>다녀온 후기 25개</span></figure><figure><span class=\"aw-stamp-big\" role=\"img\" aria-label=\"Lv.5 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-5\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-5-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-5-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-5-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-5-ink)\"><textPath href=\"#aw-rk-ring-5\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.5 LEGEND ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-5-ring)\">5</span></span><b>Lv.5 전설의 덕후</b><span>다녀온 후기 50개</span></figure></div><div class=\"aw-stamps\"><figure><span class=\"aw-stamp s20 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>20px</span></figure><figure><span class=\"aw-stamp s32 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>32px</span></figure><figure><span class=\"aw-stamp s40 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>40px</span></figure><figure><span class=\"aw-rkchip lv1\"><span class=\"aw-stamp s20 lv1\" role=\"img\" aria-label=\"Lv.1 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.1</span></span><span>닉네임 옆</span></figure><figure><span class=\"aw-rkchip lv2\"><span class=\"aw-stamp s20 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.2</span></span><span>닉네임 옆</span></figure><figure><span class=\"aw-rkchip lv3\"><span class=\"aw-stamp s20 lv3\" role=\"img\" aria-label=\"Lv.3 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.3</span></span><span>닉네임 옆</span></figure><figure><span class=\"aw-rkchip lv4\"><span class=\"aw-stamp s20 lv4\" role=\"img\" aria-label=\"Lv.4 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.4</span></span><span>닉네임 옆</span></figure><figure><span class=\"aw-rkchip lv5\"><span class=\"aw-stamp s20 lv5\" role=\"img\" aria-label=\"Lv.5 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.5</span></span><span>닉네임 옆</span></figure><figure><span class=\"aw-stamp-big dim\" role=\"img\" aria-label=\"Lv.3 도장\"><svg width=\"96\" height=\"96\" viewBox=\"0 0 80 80\" aria-hidden=\"true\"><defs><path id=\"aw-rk-ring-3\" d=\"M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0\"></path></defs><circle cx=\"40\" cy=\"40\" r=\"38\" style=\"fill:var(--rank-3-fill)\"></circle><circle cx=\"40\" cy=\"40\" r=\"38\" fill=\"none\" stroke-width=\"3.5\" style=\"stroke:var(--rank-3-ring)\"></circle><circle cx=\"40\" cy=\"40\" r=\"22.5\" fill=\"#ffffff\" stroke-width=\"1.2\" style=\"stroke:var(--rank-3-ring)\"></circle><text font-size=\"7.2\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\" style=\"fill:var(--rank-3-ink)\"><textPath href=\"#aw-rk-ring-3\" textLength=\"172\" lengthAdjust=\"spacingAndGlyphs\">ANI:WHERE ✦ LV.3 PILGRIM ✦</textPath></text></svg><img src=\"/design/mascot.png\" alt=\"\"><span class=\"lv\" style=\"background:var(--rank-3-ring)\">3</span></span><span>아직 못 받은 랭크</span></figure></div></div>\n",
  "RankStamp.md": "# RankStamp\n\n후기 도장. 다녀온 후기를 남긴 팝업 수만큼 도장이 쌓이고, 쌓인 수로 랭크 5단계가 정해진다. 어디서나 같은 도장을 크기만 바꿔 쓴다.\n\n| 랭크 | 다녀온 후기 | 테두리 | 바탕 | 글자 |\n| --- | --- | --- | --- | --- |\n| Lv.1 새싹 팬 | 1개 | `rank-1-ring` #5fbf9f | `rank-1-fill` #f0faf6 | `rank-1-ink` #0f6b5c |\n| Lv.2 단골 팬 | 3개 | `rank-2-ring` #21b287 | `rank-2-fill` #e9f7f2 | `rank-2-ink` #0f6b5c |\n| Lv.3 성지순례러 | 10개 | `rank-3-ring` #2c5bc5 | `rank-3-fill` #eaf0fc | `rank-3-ink` #2c5bc5 |\n| Lv.4 덕질 마스터 | 25개 | `rank-4-ring` #7656c4 | `rank-4-fill` #f1ecff | `rank-4-ink` #5b3fae |\n| Lv.5 전설의 덕후 | 50개 | `rank-5-ring` #c99a00 | `rank-5-fill` #fff6d6 | `rank-5-ink` #7a5a00 |\n\n- **96px** 마이페이지 대표 도장 — 둘레 글자(`ANI:WHERE ✦ LV.n 이름 ✦`) + 오른쪽 아래 단계 숫자. 랭크 안내 팝업에서는 같은 도장을 116px 로.\n- **40px** 내 캘린더 '다녀온 팝업' 카드의 포스터 모서리 (테두리 3px).\n- **32px** 리뷰 쓰기 칸의 내 닉네임 옆 (테두리 2.5px).\n- **20px** 리뷰 · 후기 카드의 닉네임 옆, `Lv.n` 알약 안 (테두리 2px, 바탕 흰색).\n- 40px 이하는 색 테두리 + 마스코트(`mascot.png`, 도장 폭의 62%)만. 글자는 넣지 않는다.\n- 아직 못 받은 랭크는 회색(grayscale) + 45% 로 흐리게.\n- 세는 규칙: 다녀온 후기만(별점만 남겨도 1개), 같은 팝업은 여러 번 써도 1개, 기대평 · 답글 · 지운 후기는 세지 않는다. 탈퇴하면 도장도 지워진다.\n- 랭크가 오르면 **도장 색만** 바뀐다. 그 밖의 혜택은 없다 — 없는 혜택을 화면에 쓰지 않는다.\n- 도장이 없는 회원(0개)에게는 도장을 그리지 않는다.\n\n손으로 옮김: `common/stamp.py` 의 `TIERS`(값) · `app_cafemap.py` 의 `_ad_stamp` · `_ahome_stamp` · 웹 `components/RankStamp.tsx`, `a-shell.css` 의 `.rk-*`.\n",
  "ReviewCard.html": "<div class=\"aw\" style=\"display:flex;gap:16px;align-items:flex-start;padding:16px\"><div class=\"aw-rv\"><span class=\"kind\">다녀온 후기</span><div class=\"who\"><span class=\"av\"><span class=\"mi\">person</span></span>튜토리얼<span class=\"aw-rkchip lv2\"><span class=\"aw-stamp s20 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.2</span></span><span class=\"time\">5분 전</span></div><div class=\"stars\">★★★★★</div><div class=\"body\">평일 오후 3시쯤 갔더니 기다리지 않고 바로 들어갔어요. 특전도 넉넉히 남아 있었어요!</div><div class=\"pop\"><span class=\"pp\" style=\"background-image:url(/design/default_poster.png)\"></span><span class=\"pn\">승리의 여신: 니케</span><span class=\"aw-badge live\">진행 중</span></div></div><div class=\"aw-rv\"><span class=\"kind hope\">기대평</span><div class=\"who\"><span class=\"av\"><span class=\"mi\">person</span></span>튜토리얼<span class=\"aw-rkchip lv2\"><span class=\"aw-stamp s20 lv2\" role=\"img\" aria-label=\"Lv.2 도장\"><img src=\"/design/mascot.png\" alt=\"\"></span><span>Lv.2</span></span><span class=\"time\">5분 전</span></div><div class=\"body\">열리는 날 바로 가 보려고요. 특전이 궁금해요!</div><div class=\"pop\"><span class=\"pp\" style=\"background-image:url(/design/default_poster.png)\"></span><span class=\"pn\">학원 아이돌마스터</span><span class=\"aw-badge soon\">D-9</span></div></div></div>\n",
  "ReviewCard.md": "# ReviewCard\n\n홈 '꿀팁 가득! 실시간 후기 모음' 의 후기 카드. 3칸 열(좁으면 2칸)에 왼쪽부터 놓이고, 글 길이만큼 높이가 달라진다.\n\n- 테두리 `line` 1.5px · 모서리 `radius-card`(16px) · 안쪽 여백 14px.\n- 위에서부터: 종류 칩 → 프로필 사진(26px) · 닉네임 · 랭크 칩(RankStamp 20px + `Lv.n`) · 시간 → 별(다녀온 후기만, `star-ink`) → 본문(14px, 8줄까지) → 어떤 팝업인지 한 줄(작은 포스터 · 작품 이름 · 상태 Badge).\n- 종류 칩 색: `다녀온 후기` = `accent-ink` on `accent-soft` · `기대평` = `blue` on `blue-soft` · `기타` = `star-ink` on `rank-5-fill`.\n- 사진이 있는 후기는 카드 맨 위에 사진을 꽉 채워 싣는다.\n- 칸 제목 오른쪽의 칩(`전체 · 다녀온 후기 · 기대평 · 기타`)으로 종류를 골라 본다.\n- 예시의 닉네임 · 글은 시험용이다. 화면 그림 · 문서에 실제 회원의 글을 옮기지 않는다.\n\n손으로 옮김: `app_cafemap.py` 의 `_home_reviews`(`ah_wall`) · 웹 `a-home.css` 의 `.ah-wall`, `.ah-rv*`.\n",
  "StoryCircle.html": "<div class=\"aw\" style=\"display:flex;gap:8px;padding:16px 16px 8px\"><div class=\"aw-story add\"><div class=\"ring\"><span class=\"mi\">add</span></div><div class=\"nm\">최애 추가하기</div></div><div class=\"aw-story\"><div class=\"ring\"><div class=\"pic\" style=\"background-image:url(/design/default_poster.png)\"></div><span class=\"rg\">부산</span></div><div class=\"nm\">승리의 여신: 니케</div></div><div class=\"aw-story\"><div class=\"ring\"><div class=\"pic\" style=\"background-image:url(/design/default_poster.png)\"></div><span class=\"rg\">마포</span></div><div class=\"nm\">학원 아이돌마스터</div></div></div>\n",
  "StoryCircle.md": "# StoryCircle\n\n홈 맨 위 동그라미 줄. 회원은 '북마크 팝업'(내가 북마크한 팝업 하나에 하나), 손님은 '특전 있는 작품들'. 누르면 그 팝업 상세.\nA안에서도 이 줄은 **개편 전 모양 그대로** 둔다 (11/25 결정).\n\n- 72px 동그라미, 민트→노랑 고리(`accent` → `#7fe0cf` → `#ffd66b`), 흰 3px 테두리 안에 포스터.\n- 동그라미 아래쪽에 걸친 지역 이름 알약(`mint` 바탕 · 흰 글자 · 흰 테두리 1.5px), 그 아래 작품 이름 한 줄(넘치면 …).\n- 회원 줄의 맨 앞은 늘 `최애 추가하기`(점선 동그라미 + `add`) — 팝업을 골라 한 번에 북마크하는 창을 연다.\n- 줄이 길면 마우스로 끌거나 양옆 ‹ › 로 넘긴다.\n\n손으로 옮김: `app_cafemap.py` 의 `render_stories`, `STORY_CSS`.\n"
 }
} as never;

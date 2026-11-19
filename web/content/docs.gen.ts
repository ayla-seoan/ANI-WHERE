// 자동 생성 파일 — 손으로 고치지 말 것. 원본: docs/privacy-policy.md · docs/guide.md · static/guide/guide.css · docs/design/** · static/design/*.css
// 다시 만들기: cd web && node scripts/sync_docs.mjs

export const PRIVACY_MD: string = "# 개인정보처리방침\n\nANI:WHERE(이하 '서비스')는 「개인정보 보호법」에 따라 이용자의 개인정보를 보호하고, 관련 고충을 신속하게 처리하기 위해 다음과 같이 개인정보처리방침을 둡니다. 개인정보보호위원회 표준 개인정보처리방침의 항목 순서를 따랐습니다.\n\n> 이 서비스는 부트캠프 2차 프로젝트로 만든 개인 서비스입니다. 필요한 최소한의 정보만 받고, 이메일·전화번호·실명·생일은 받지 않습니다.\n\n## 1. 개인정보의 처리 목적\n\n| 목적 | 내용 |\n| --- | --- |\n| 회원 식별·로그인 | 같은 사람인지 알아보고 로그인 상태를 유지 |\n| 리뷰·수정 작성자 표시 | 리뷰·수정 이력에 닉네임(과 선택한 경우 프로필 사진)을 표시 |\n| 북마크·내 캘린더·알림 | 북마크한 팝업의 오픈·종료 알림, 삭제 요청 처리 결과 알림 |\n| 서비스 운영 통계 | 일별 접속 회원 수 (관리자 대시보드) |\n\n## 2. 처리하는 개인정보 항목\n\n| 구분 | 항목 | 수집 방법 |\n| --- | --- | --- |\n| 필수 (카카오·네이버 가입) | 로그인 수단, 카카오·네이버 계정 번호를 **되돌릴 수 없게 바꾼 값**(해시), 닉네임, 약관 동의 시각 | 가입 화면 |\n| 필수 (아이디 가입) | 아이디, **일방향 암호화한** 비밀번호, 닉네임, 약관 동의 시각 | 가입 화면 |\n| 선택 | 프로필 사진 (카카오·네이버 프로필 사진 주소, 또는 직접 올린 사진) | 가입 화면 선택 동의, 마이페이지 |\n| 자동 생성 | 접속한 날짜(회원 번호와 함께), 로그인 유지 쿠키, 알림 읽음 쿠키 | 서비스 이용 중 |\n| 자동 생성 (손님) | 접속 IP 를 **되돌릴 수 없게 바꾼 값** (손님 북마크 구분용, IP 원문은 저장하지 않음) | 서비스 이용 중 |\n\n받지 않는 정보: 이메일, 전화번호, 실명, 생일, 성별, 카카오·네이버 계정 번호 원래 값.\n\n서비스를 쓰는 동안 생기는 정보:\n- **위치 (선택)**: 브라우저에서 위치를 허용한 경우에만, '내 주변 팝업' · '지금 내 위치 어디야?' 에 씁니다. **저장하지 않고** 화면을 닫으면 사라집니다. 동네 이름을 알아내려고 좌표를 카카오에 보냅니다 (5번).\n- **리뷰에 붙인 사진**: 올릴 때 사진 속 **위치(GPS) · 기기 · 촬영 시각 정보를 자동으로 지운 뒤** 저장합니다. 사진은 주소를 아는 사람이 볼 수 있으니 다른 사람 얼굴 · 영수증 · 연락처가 보이는 사진은 올리지 말아 주세요.\n리뷰·공지·삭제 사유에 전화번호·이메일·계좌번호·주민번호·카드번호가 들어 있으면 저장하지 않습니다.\n\n## 3. 보유 기간과 파기\n\n| 항목 | 보유 기간 | 파기 방법 |\n| --- | --- | --- |\n| 회원 정보 (닉네임·사진·아이디·비밀번호) | **탈퇴할 때까지** | 탈퇴 즉시 지난 기록까지 지움 (닉네임·사진은 빈 값으로, 아이디·비밀번호 해시는 삭제) |\n| 접속한 날짜 | 1년 (탈퇴하면 즉시) | 기간이 지나면 삭제 |\n| 쓴 리뷰·수정 이력 | 서비스 운영 기간 | 탈퇴하면 작성자를 '탈퇴한 회원'으로 바꿈 (내용은 다른 이용자를 위해 남음). 지우고 싶은 글은 탈퇴 전에 삭제 요청 |\n| 기간이 끝난(또는 운영자가 내린) 팝업에 단 리뷰 · 북마크 | 팝업이 내려간 주가 끝날 때까지 | 다음 주 월요일에 팝업과 함께 리뷰 · 북마크 · 리뷰 사진을 모두 삭제 |\n| 리뷰에 붙인 사진 | 그 리뷰를 지울 때까지 | 리뷰를 지우면(내가 지우거나 관리자가 지우면) 사진 파일을 바로 삭제. 지운 리뷰의 글은 화면에서 사라지고, 되돌리기용 내부 기록에만 남아 관리자만 볼 수 있음 |\n| 쿠키 | 로그인 30일, 알림 읽음 60일 | 기간이 지나면 브라우저에서 사라짐, 로그아웃·탈퇴 시 바로 지움 |\n\n전자적 파일은 복구할 수 없는 방법으로 지웁니다.\n\n## 4. 제3자 제공\n\n개인정보를 제3자에게 제공하지 않습니다.\n\n## 5. 처리 위탁과 국외 이전\n\n서비스를 운영하려고 다음 업체의 서비스를 씁니다.\n\n| 업체 | 하는 일 | 저장 위치 | 옮겨 가는 정보 |\n| --- | --- | --- | --- |\n| Supabase | 데이터베이스 (회원·리뷰·북마크) | 대한민국(서울) 리전 | 2번의 모든 항목 |\n| Streamlit (Snowflake) | 앱 서버 | 미국 | 서비스를 쓰는 동안 오가는 정보, 직접 올린 사진 파일 |\n| Vercel | 공개 웹 서버 (읽기 전용) | 미국 | 접속 기록 (개인정보 저장 없음) |\n| OpenAI | '물어보기' 답 만들기 | 미국 | 질문 글 (전화번호·이메일 등은 가린 뒤 보냄, 회원 정보는 보내지 않음) |\n| 카카오 · 네이버 | 간편 로그인 인증 | 대한민국 | 로그인할 때 인증 정보 (서비스는 해시값만 저장) |\n| 카카오 (지도 · 로컬) | 지도 표시, 주소 → 좌표, 내 위치 → 동네 이름 | 대한민국 | 팝업 주소, 위치를 허용한 경우 내 좌표 (저장하지 않음, 회원 정보는 보내지 않음) |\n| 네이버클라우드 (NAVER API HUB) | 블로그 후기 검색 | 대한민국 | 없음 (팝업 작품명·매장명만 보냄, 회원 정보는 보내지 않음) |\n\n국외 이전은 서비스를 쓰는 시점에 인터넷으로 옮겨지며, 거부하려면 서비스를 쓰지 않거나 탈퇴하면 됩니다.\n\n## 6. 이용자의 권리와 행사 방법\n\n- **열람·정정:** 마이페이지(오른쪽 위 내 닉네임)에서 닉네임·프로필 사진을 보고 고칠 수 있습니다.\n- **삭제·처리 정지:** 마이페이지의 **탈퇴하기**로 언제든 지울 수 있습니다. 프로필 사진은 '기본 사진 설정'을 누르면 바로 지워집니다.\n- **동의 철회:** 선택 동의(프로필 사진)는 마이페이지에서 '기본 사진 설정'을 눌러 철회할 수 있습니다.\n\n## 7. 만 14세 미만 아동\n\n**만 14세 이상만 가입할 수 있습니다.** 만 14세 미만의 개인정보를 처리하려면 법정대리인 동의가 필요하지만, 이 서비스는 그 확인 절차를 아직 갖추지 않아 만 14세 미만의 가입을 받지 않습니다. 가입 화면에서 만 14세 이상인지 확인합니다.\n\n## 8. 안전성 확보 조치\n\n- 비밀번호는 **일방향 암호화(bcrypt)** 해서 저장하고, 원래 비밀번호는 어디에도 남기지 않습니다.\n- 카카오·네이버 계정 번호와 손님 IP 는 소금 친 해시로 바꿔 원래 값을 알 수 없게 저장합니다.\n- 모든 통신은 HTTPS 로 암호화합니다. 데이터베이스는 행 단위 보안(RLS)으로 고치기·지우기를 막습니다.\n- 관리자 권한은 지정한 1명에게만 있습니다.\n- 글에 개인정보(전화번호·이메일 등)가 들어 있으면 저장하지 않습니다.\n- 올린 사진은 위치(GPS) · 기기 · 촬영 시각 정보를 지운 뒤 저장하고, 리뷰를 지우면 사진 파일도 지웁니다.\n\n## 9. 쿠키\n\n| 쿠키 | 목적 | 기간 |\n| --- | --- | --- |\n| `aw_session` | 로그인 유지 (서명한 회원 번호) | 30일 |\n| `aw_ntf_read` | 읽은 알림 표시 | 60일 |\n\n브라우저 설정에서 쿠키를 거부할 수 있으며, 거부하면 로그인이 유지되지 않습니다.\n\n## 10. 개인정보 보호책임자\n\n| | |\n| --- | --- |\n| 책임자 | 김서안 (ANI:WHERE 운영자) |\n| 연락처 | tjtek888@gmail.com |\n\n개인정보 침해 상담: 개인정보침해신고센터(privacy.kisa.or.kr, 국번 없이 118), 개인정보분쟁조정위원회(www.kopico.go.kr, 1833-6972)\n\n## 11. 시행일\n\n이 개인정보처리방침은 2026년 11월 18일부터 적용합니다.\n\n---\n\n# 이용약관 (요약)\n\n1. **서비스:** 애니메이션 팝업·콜라보 카페 정보를 지도와 목록으로 보여 주고, 회원이 리뷰·북마크·정보 수정을 할 수 있게 합니다.\n2. **가입:** 만 14세 이상만 가입할 수 있습니다. 다른 사람인 척하거나 욕설·음란한 닉네임은 쓸 수 없습니다.\n3. **게시물:** 리뷰·수정한 정보에 대한 책임은 쓴 사람에게 있습니다. 욕설·광고·남의 개인정보·저작권을 침해하는 글은 관리자가 지울 수 있습니다. 다른 회원의 글은 '삭제 요청'으로 신고할 수 있습니다.\n4. **정보의 정확성:** 팝업 정보는 자동 수집과 이용자 입력으로 모읍니다. 방문 전 공식 공지를 꼭 확인해 주세요. '기간 확인 필요'·'링크 확인 필요' 표시가 있는 정보는 특히 확인이 필요합니다.\n5. **탈퇴:** 마이페이지에서 언제든 탈퇴할 수 있고, 개인정보는 개인정보처리방침 3번에 따라 지웁니다.\n";

export const GUIDE_HTML: string = "<div class=\"g-hero\">\n<div class=\"g-hero-t\">ANI:WHERE 사용자 튜토리얼</div>\n<div class=\"g-hero-s\">애니 팝업 · 콜라보 카페 · 굿즈 행사를 <b>찾고</b>, <b>북마크</b>하고, <b>놓치지 않게</b> 도와주는 곳이에요.<br>처음이라도 괜찮아요. 그림을 보면서 하나씩 따라 해 보세요!</div>\n</div>\n\n<div class=\"g-h2\">처음 왔다면 딱 3단계만!</div>\n<div class=\"g-sub\">옆으로 넘겨 보세요 (‹ › 버튼을 누르거나, 손가락 · 마우스로 밀어도 돼요)</div>\n<div class=\"g-slides-wrap\">\n<div class=\"g-slides\">\n<div class=\"g-slide\"><img src=\"/guide/home.webp\" alt=\"홈 화면\"><div class=\"g-slide-t\"><b>1</b> 홈에서 둘러보기</div><div class=\"g-slide-s\">지금 인기 있는 팝업, 새로 생긴 팝업, 이번 주에 끝나는 팝업이 한눈에 보여요.</div></div>\n<div class=\"g-slide\"><img src=\"/guide/card.webp\" alt=\"팝업 카드\"><div class=\"g-slide-t\"><b>2</b> 마음에 들면 북마크</div><div class=\"g-slide-s\">카드 오른쪽 아래 <b>북마크 버튼</b>을 꾹! 누르면 내 목록에 저장돼요.</div></div>\n<div class=\"g-slide\"><img src=\"/guide/calendar.webp\" alt=\"내 캘린더\"><div class=\"g-slide-t\"><b>3</b> 내 캘린더에서 챙기기</div><div class=\"g-slide-s\">북마크한 팝업이 달력에 쏙. 열리기 전 · 끝나기 전에 알림도 와요.</div></div>\n</div>\n</div>\n\n<div class=\"g-h2\">어떤 걸 알고 싶나요?</div>\n<div class=\"g-nav\">\n<a href=\"#home\"><span class=\"mi\">home</span>홈</a>\n<a href=\"#map\"><span class=\"mi\">map</span>지도로 보기</a>\n<a href=\"#list\"><span class=\"mi\">format_list_bulleted</span>리스트로 보기</a>\n<a href=\"#bookmark\"><span class=\"mi\">bookmark_add</span>북마크</a>\n<a href=\"#cal\"><span class=\"mi\">calendar_month</span>내 캘린더 · 알림</a>\n<a href=\"#add\"><span class=\"mi\">add_circle</span>팝업 등록하기</a>\n<a href=\"#edit\"><span class=\"mi\">edit</span>정보 고치기</a>\n<a href=\"#delete\"><span class=\"mi\">delete</span>삭제 요청하기</a>\n<a href=\"#login\"><span class=\"mi\">login</span>로그인 · 회원가입</a>\n<a href=\"#ask\"><span class=\"mi\">forum</span>물어보기</a>\n<a href=\"#mobile\"><span class=\"mi\">smartphone</span>휴대폰으로 쓰기</a>\n</div>\n\n<a id=\"home\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">home</span>홈</div>\n<div class=\"g-lead\">왼쪽 위 <b>ANI:WHERE 로고</b>를 누르거나, 메뉴의 <b>홈</b>을 누르면 와요. 처음 들어오면 언제나 홈부터 보여요.</div>\n<img class=\"g-img\" src=\"/guide/home.webp\" alt=\"홈 화면\">\n<table class=\"g-table\">\n<tr><th>칸 이름</th><th>무엇을 보여 주나요?</th></tr>\n<tr><td><b>북마크 팝업</b></td><td>내가 북마크한 팝업이 동그라미로 모여요. 동그라미 위에는 지역이 보이고, 누르면 그 팝업으로 가요.</td></tr>\n<tr><td><b>실시간 인기 급상승 랭킹</b></td><td>최근 7일 동안 북마크와 리뷰가 많이 늘어난 팝업 1~5위예요 (북마크 1개 = 2점, 리뷰 · 답글 1개 = 1점. 같으면 전체 기간 점수, 그다음 오픈이 빠른 순). 오른쪽 순위를 누르면 큰 배너가 바뀌고, 배너를 누르면 그 팝업으로 가요.</td></tr>\n<tr><td><b>따끈따끈 신규 등록 팝업</b></td><td>새로 올라온 팝업이에요. 지역 버튼으로 골라 볼 수 있어요.</td></tr>\n<tr><td><b>이번 주에 끝나는 팝업</b></td><td>월요일부터 일요일까지, 그날 끝나는 팝업을 달력처럼 보여 줘요. 오늘 칸은 민트색이에요.</td></tr>\n<tr><td><b>사전예약 팝업</b></td><td>아직 열기 전이고, 미리 예약해야 들어갈 수 있는 팝업이에요.</td></tr>\n<tr><td><b>꿀팁 가득! 실시간 후기 모음</b></td><td>다녀온 사람들의 최신 후기예요. 사진이 있는 후기가 먼저 나와요.</td></tr>\n</table>\n<div class=\"g-row\">\n<img src=\"/guide/home_rank.webp\" alt=\"랭킹 배너\">\n<div><div class=\"g-h3\">랭킹 배너 쓰는 법</div>\n<ol class=\"g-steps\"><li>‹ › 버튼을 누르면 다음 순위로 넘어가요.</li><li>가만히 두면 5초마다 저절로 넘어가요.</li><li>오른쪽 목록에서 <b>3</b>을 누르면 3위 배너로 바로 바뀌어요.</li><li>배너를 누르면 그 팝업의 자세한 정보가 열려요.</li></ol></div>\n</div>\n</div>\n\n<a id=\"map\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">map</span>지도로 보기</div>\n<div class=\"g-lead\">메뉴의 <b>지도로 보기</b>를 누르면, 팝업이 어디에 있는지 지도에서 볼 수 있어요.</div>\n<img class=\"g-img\" src=\"/guide/map.webp\" alt=\"지도로 보기\">\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">event_note</span><b>왼쪽 · 데일리 팝업 노트</b><p>날짜와 지역을 ‹ › 로 바꾸면 그날 열려 있는 팝업이 나와요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">location_on</span><b>가운데 · 지도</b><p>민트색 핀이 팝업이 있는 곳이에요. 핀 위에 마우스를 올리면 카드가, 누르면 목록이 떠요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">forum</span><b>오른쪽 · 물어보기</b><p>“이번 주말 홍대 팝업”처럼 말로 물어보면 찾아 줘요.</p></div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>위치 사용을 허락하면 <b>내 주변</b>부터 보여 줘요. 지도 오른쪽 위 + − 로 크게 · 작게 볼 수 있어요.</div>\n</div>\n\n<a id=\"list\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">format_list_bulleted</span>리스트로 보기</div>\n<div class=\"g-lead\">팝업을 포스터 카드로 쭉 모아 봐요. 카드를 누르면 자세한 정보가 열려요.</div>\n<img class=\"g-img\" src=\"/guide/list.webp\" alt=\"리스트로 보기\">\n<div class=\"g-h3\">카드 위 작은 글씨는 무슨 뜻일까요?</div>\n<table class=\"g-table\">\n<tr><th>보이는 글씨</th><th>뜻</th></tr>\n<tr><td><span class=\"g-badge green\">진행 중</span></td><td>지금 열려 있어요. 가 볼 수 있어요!</td></tr>\n<tr><td><span class=\"g-badge blue\">D-5</span></td><td>5일 뒤에 열려요.</td></tr>\n<tr><td><span class=\"g-badge red\">마감임박</span></td><td>3일 안에 끝나요. 서둘러요!</td></tr>\n<tr><td><span class=\"g-badge purple\">사전예약 D-5</span></td><td>예약해야 들어갈 수 있고, 5일 뒤에 열려요. (홈의 사전예약 칸)</td></tr>\n</table>\n<div class=\"g-row\">\n<img src=\"/guide/search.webp\" alt=\"검색 필터\">\n<div><div class=\"g-h3\">원하는 팝업만 골라 보기</div>\n<ol class=\"g-steps\"><li>메뉴 오른쪽 <b>돋보기</b>를 눌러요. (지도로 보기 · 리스트로 보기에서만 보여요)</li><li>작품 이름, 캐릭터, 날짜를 넣어요.</li><li>목록 위 <b>북마크</b>, <b>지역 고르기</b>, <b>정렬</b>로 더 좁힐 수 있어요.</li><li>아무것도 안 나오면, 어떤 조건을 빼면 몇 곳이 나오는지 알려 줘요.</li></ol></div>\n</div>\n<div class=\"g-row\">\n<img src=\"/guide/detail.webp\" alt=\"자세히 보기\">\n<div><div class=\"g-h3\">자세히 보기</div><p>위치 · 일정 · 특전 · 참고 웹사이트가 나와요. 오른쪽에는 <b>리뷰</b>와 <b>블로그 후기</b>가 있어요.</p><p>맨 아래에는 같은 작품의 <b>비슷한 팝업</b>과 <b>이 근처 다른 팝업</b>도 보여 줘요.</p></div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>처음에는 24곳만 보여요. 맨 아래 <b>N건 더보기</b>를 누르면 더 나와요.</div>\n</div>\n\n<a id=\"bookmark\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">bookmark_add</span>북마크 · 북마크 팝업</div>\n<div class=\"g-lead\">북마크는 “이거 가고 싶어!” 하고 표시해 두는 거예요. 북마크는 <b>회원마다 따로</b> 저장돼요.</div>\n<div class=\"g-row\">\n<img src=\"/guide/card.webp\" alt=\"카드의 북마크 버튼\" class=\"g-small\">\n<div><div class=\"g-h3\">하나씩 북마크하기</div><ol class=\"g-steps\"><li>카드 오른쪽 아래(또는 자세히 보기의 제목 옆) <b>북마크 버튼</b>을 눌러요.</li><li>버튼이 민트색으로 바뀌면 저장된 거예요.</li><li>한 번 더 누르면 풀려요.</li></ol></div>\n</div>\n<div class=\"g-row\">\n<img src=\"/guide/fav_dialog.webp\" alt=\"최애 추가하기 창\">\n<div><div class=\"g-h3\">여러 개를 한 번에 — 최애 추가하기</div><ol class=\"g-steps\"><li>홈의 <b>북마크 팝업</b>에서 <b>+ 최애 추가하기</b>를 눌러요.</li><li>마음에 드는 팝업 포스터를 눌러 골라요. (체크 표시가 생겨요)</li><li><b>저장하기</b>를 누르면 끝!</li></ol></div>\n</div>\n<img class=\"g-img g-narrow\" src=\"/guide/home_fav.webp\" alt=\"북마크 팝업\">\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>로그인하지 않았을 때 북마크를 누르면 로그인 화면으로 가요.</div>\n</div>\n\n<a id=\"cal\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">calendar_month</span>내 캘린더 · 알림</div>\n<div class=\"g-lead\">회원만 쓸 수 있어요. 메뉴의 <b>내 캘린더</b>를 누르세요. 계절마다 꽃잎 · 잎사귀 · 단풍 · 눈이 내려요!</div>\n<img class=\"g-img\" src=\"/guide/calendar.webp\" alt=\"내 캘린더\">\n<div class=\"g-cols\">\n<div class=\"g-card\"><span class=\"mi\">calendar_month</span><b>왼쪽 · 달력</b><p>북마크한 팝업이 날짜 막대로 보여요.</p></div>\n<div class=\"g-card\"><span class=\"mi\">bookmarks</span><b>가운데 · 내 목록</b><p>북마크 · 다녀온 팝업 · 최근 본 팝업(10개)</p></div>\n<div class=\"g-card\"><span class=\"mi\">notifications</span><b>오른쪽 · 알림</b><p>최근 알림과 내 주변 추천 팝업</p></div>\n</div>\n<div class=\"g-h3\">알림은 언제 오나요?</div>\n<div class=\"g-timeline\">\n<div class=\"g-tl-row\"><div class=\"g-tl-lab\">열리기 전</div><div class=\"g-tl-bar\"><span>D-3</span><span>D-2</span><span>D-1</span><span class=\"hit\">오픈!</span></div></div>\n<div class=\"g-tl-row\"><div class=\"g-tl-lab\">끝나기 전</div><div class=\"g-tl-bar\"><span>D-3</span><span>D-2</span><span>D-1</span><span class=\"hit end\">종료!</span></div></div>\n</div>\n<div class=\"g-sub\">북마크한 팝업이 열리기 3일 전부터, 끝나기 3일 전부터 메뉴의 <b>종 모양</b>에 빨간 점이 생겨요. 관리자 공지와 삭제 요청 결과도 여기로 와요.</div>\n</div>\n\n<a id=\"add\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">add_circle</span>팝업 등록하기</div>\n<div class=\"g-lead\">아직 없는 팝업을 알려 주세요! 로그인한 뒤 화면 <b>오른쪽 아래 코랄색 + 버튼</b>을 누르면 돼요.</div>\n<img class=\"g-img\" src=\"/guide/add.webp\" alt=\"팝업 등록하기\">\n<div class=\"g-stepper\">\n<div><b>1</b>작품 · 캐릭터</div><div><b>2</b>카페 정보</div><div><b>3</b>이미지</div><div><b>4</b>기간</div><div><b>5</b>특전 · 굿즈</div><div><b>6</b>팝업 소개</div><div><b>7</b>등록 확인</div>\n</div>\n<div class=\"g-tip\"><span class=\"mi\">lightbulb</span>공지 글이 있다면 <b>공지로 간편등록</b>을 눌러 붙여 넣기만 해도 돼요. 매일 아침 자동으로 모으기도 하니, 먼저 검색해서 이미 있는지 확인해 보세요. 전화번호 · 이메일 같은 개인정보는 저장되지 않아요.</div>\n</div>\n\n<a id=\"edit\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">edit</span>정보 고치기</div>\n<div class=\"g-row\">\n<img src=\"/guide/edit.webp\" alt=\"수정하기 탭\">\n<div><ol class=\"g-steps\"><li>고칠 팝업의 자세히 보기를 열어요.</li><li>오른쪽 <b>수정하기</b> 탭을 눌러요.</li><li>날짜 · 주소 · 소개 · 사진을 고치고 저장해요. (회원만)</li></ol><p>고친 기록은 모두 남아서, 잘못 고쳐도 예전으로 되돌릴 수 있어요. 리뷰는 내가 쓴 것만 고칠 수 있어요.</p></div>\n</div>\n</div>\n\n<a id=\"delete\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">delete</span>삭제 요청하기</div>\n<div class=\"g-lead\">글은 바로 지워지지 않아요. 대신 <b>삭제 요청</b>을 보내면 관리자가 확인해요.</div>\n<div class=\"g-flow\">\n<div><span class=\"mi\">send</span>상세에서 <b>삭제 요청</b> + 이유 적기</div><i class=\"mi\">arrow_forward</i>\n<div><span class=\"mi\">admin_panel_settings</span>관리자가 확인하고 <b>승인 / 거부</b></div><i class=\"mi\">arrow_forward</i>\n<div><span class=\"mi\">notifications</span>결과를 <b>종 알림</b>으로 받기</div>\n</div>\n</div>\n\n<a id=\"login\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">login</span>로그인 · 회원가입</div>\n<div class=\"g-row\">\n<img src=\"/guide/login.webp\" alt=\"로그인 화면\">\n<div><ol class=\"g-steps\"><li>메뉴 오른쪽 <b>로그인</b>을 눌러요.</li><li><b>카카오 · 네이버 간편 로그인</b>을 누르거나, <b>아이디로 가입</b>해요.</li><li>필수 동의 3개에 체크하면 끝!</li></ol></div>\n</div>\n<table class=\"g-table\">\n<tr><th>받는 것</th><th>받지 않는 것</th></tr>\n<tr><td>닉네임(선택) · 필수 동의 3개 (만 14세 이상 · 이용약관 · 개인정보 수집 · 이용)</td><td>이메일 · 전화번호</td></tr>\n</table>\n<div class=\"g-sub\">로그아웃 · 닉네임 바꾸기 · 프로필 사진 · 탈퇴는 메뉴의 <b>내 닉네임</b>을 누르면 나오는 마이페이지에 있어요. 탈퇴하면 닉네임 · 사진 · 접속 기록을 바로 지워요. 자세한 내용은 <a href=\"./privacy\" target=\"_self\">개인정보처리방침</a>을 봐 주세요.</div>\n</div>\n\n<a id=\"ask\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">forum</span>물어보기 (ANI:WHERE에게 물어보기)</div>\n<div class=\"g-row\">\n<img src=\"/guide/ask.webp\" alt=\"물어보기\" class=\"g-small\">\n<div><div class=\"g-lead\">친구에게 묻듯이 물어보세요. <b>작품 · 지역 · 날짜</b>를 넣으면 더 정확해요.</div>\n<div class=\"g-chips\"><span>치이카와 이번 달 서울 팝업 있어?</span><span>이번 주말 홍대 팝업</span><span>내 주변 가까운 팝업</span><span>곧 끝나는 팝업</span><span>내 북마크 보여줘</span><span>등록 어떻게 해?</span></div>\n<p>PC는 지도 · 리스트 오른쪽 창, 휴대폰은 오른쪽 아래 <b>말풍선 버튼</b>이에요.</p></div>\n</div>\n</div>\n\n<a id=\"mobile\"></a>\n<div class=\"g-sec\">\n<div class=\"g-h2\"><span class=\"mi\">smartphone</span>휴대폰으로 쓰기</div>\n<div class=\"g-phones\">\n<figure><img src=\"/guide/mobile_home.webp\" alt=\"휴대폰 홈\"><figcaption>메뉴는 맨 위 <b>홈 · 지도로 보기 · 리스트로 보기 · 내 캘린더</b></figcaption></figure>\n<figure><img src=\"/guide/mobile_filter.webp\" alt=\"휴대폰 필터\"><figcaption>돋보기를 누르면 <b>필터</b> 창이 열려요. 다 고르면 <b>팝업 N곳 표시</b></figcaption></figure>\n</div>\n</div>\n\n<div class=\"g-end\">궁금한 게 더 있으면 <b>물어보기</b>에 편하게 물어봐 주세요!</div>\n";

export const GUIDE_CSS: string = "/* 사용자 튜토리얼 (/guide) 꾸밈 — 11/18. 내용은 docs/guide.md */\n.pg-guide { max-width: 980px !important; }\n.pg-guide img { max-width: 100%; }\n.g-hero { margin: 8px 0 26px; padding: 30px 30px 26px; border-radius: 22px; color: #fff;\n  background: linear-gradient(135deg, #14b8a6 0%, #0f8f82 60%, #0b6f66 100%); box-shadow: 0 10px 30px rgba(20,184,166,.25); }\n.g-hero-t { font-size: 2rem; font-weight: 900; letter-spacing: -.5px; }\n.g-hero-s { margin-top: 10px; font-size: 1.02rem; line-height: 1.7; opacity: .95; }\n.g-h2 { font-size: 1.45rem; font-weight: 900; margin: 6px 0 6px; display: flex; align-items: center; gap: 8px; }\n.g-h2 .mi { color: var(--accent); font-size: 1.6rem; }\n.g-h3 { font-size: 1.08rem; font-weight: 800; margin: 4px 0 8px; }\n.g-sub { color: #6B7672; font-size: .9rem; line-height: 1.7; margin: 4px 0 12px; }\n.g-lead { font-size: 1.02rem; line-height: 1.8; margin: 2px 0 14px; color: #2E3835; }\n.g-sec { margin: 34px 0 10px; padding-top: 26px; border-top: 1px solid #E6ECEA; }\n.g-img { width: 100%; border-radius: 16px; border: 1px solid #E3E9E7; box-shadow: 0 6px 22px rgba(0,0,0,.07); margin: 6px 0 16px; }\n.g-img.g-narrow { max-width: 620px; display: block; }\n/* 처음 3단계: 옆으로 넘기는 배너 */\n.g-slides { display: flex; gap: 16px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px 2px 14px; margin-bottom: 26px; }\n.g-slide { flex: 0 0 78%; scroll-snap-align: start; background: #F6F8F7; border-radius: 18px; padding: 14px; box-sizing: border-box; }\n.g-slide img { width: 100%; height: 260px; object-fit: contain; object-position: center; background: #fff; border-radius: 12px; border: 1px solid #E3E9E7; }\n.g-slide-t { margin-top: 12px; font-size: 1.1rem; font-weight: 900; display: flex; align-items: center; gap: 8px; }\n.g-slide-t b { display: inline-flex; width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: #fff;\n  align-items: center; justify-content: center; font-size: .95rem; }\n.g-slide-s { margin-top: 6px; color: #4B5653; line-height: 1.7; font-size: .93rem; }\n/* 바로가기 */\n.g-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 8px 0 10px; }\n.g-nav a { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-radius: 14px; background: #fff; border: 1px solid #E3E9E7;\n  color: #26302D !important; text-decoration: none !important; font-weight: 700; font-size: .92rem; transition: all .15s ease; }\n.g-nav a:hover { border-color: var(--accent); background: #F0FBF9; }\n.g-nav a .mi { color: var(--accent-deep); font-size: 1.3rem; }\n/* 그림 + 글 나란히 */\n.g-row { display: grid; grid-template-columns: 1.2fr 1fr; gap: 22px; align-items: center; margin: 14px 0; }\n.g-row img { width: 100%; border-radius: 14px; border: 1px solid #E3E9E7; box-shadow: 0 4px 16px rgba(0,0,0,.06); }\n.g-row img.g-small { max-width: 300px; justify-self: center; }\n.g-row p { line-height: 1.8; margin: 0 0 8px; }\n.g-steps { margin: 0; padding-left: 0 !important; list-style: none; counter-reset: s; }\n.g-steps li { counter-increment: s; position: relative; padding: 6px 0 6px 38px; line-height: 1.7; list-style: none; }\n.g-steps li::before { content: counter(s); position: absolute; left: 0; top: 6px; width: 26px; height: 26px; border-radius: 50%;\n  background: var(--accent-soft); color: var(--accent-deep); font-weight: 900; display: flex; align-items: center; justify-content: center; font-size: .85rem; }\n/* 알림 상자: 글이 칸으로 쪼개지지 않게 아이콘만 왼쪽에 띄우고, 글씨는 작게 (11/18 요청) */\n.g-tip { display: block; position: relative; background: #FFF8E6; border: 1px solid #F6E2A8; border-radius: 14px;\n  padding: 10px 14px 10px 40px; line-height: 1.7; font-size: .82rem; margin: 10px 0; color: #4B4636; }\n.g-tip .mi { position: absolute; left: 13px; top: 10px; color: #E2A100; font-size: 1.1rem; }\n.g-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 12px; }\n.g-card { background: #F6F8F7; border-radius: 14px; padding: 14px; }\n.g-card .mi { color: var(--accent); font-size: 1.5rem; display: block; margin-bottom: 4px; }\n.g-card b { display: block; font-size: .95rem; }\n.g-card p { margin: 6px 0 0; font-size: .88rem; line-height: 1.6; color: #4B5653; }\ntable.g-table { width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #E3E9E7; border-radius: 14px; overflow: hidden;\n  margin: 8px 0 14px; font-size: .92rem; }\ntable.g-table th { background: #EAF8F5; color: var(--accent-deep); text-align: left; padding: 10px 14px; font-weight: 800; }\ntable.g-table td { padding: 10px 14px; border-top: 1px solid #EEF2F1; line-height: 1.6; vertical-align: top; }\n.g-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-weight: 800; font-size: .8rem; white-space: nowrap; }\n.g-badge.green { color: var(--accent-deep); background: var(--accent-soft); }\n.g-badge.blue { color: #2C5BC5; background: #EAF0FC; }\n.g-badge.red { color: #D93A4A; background: #FDECEE; }\n.g-badge.purple { color: #fff; background: #6C5CE7; }\n/* 알림 시점 그래프 */\n.g-timeline { background: #F6F8F7; border-radius: 14px; padding: 14px 16px; margin: 4px 0 8px; }\n.g-tl-row { display: flex; align-items: center; gap: 12px; margin: 6px 0; }\n.g-tl-lab { width: 76px; font-weight: 800; font-size: .88rem; }\n.g-tl-bar { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }\n.g-tl-bar span { text-align: center; padding: 8px 0; border-radius: 10px; background: #D8F1EC; color: var(--accent-deep); font-weight: 800; font-size: .85rem; }\n.g-tl-bar span.hit { background: var(--accent); color: #fff; }\n.g-tl-bar span.hit.end { background: #D93A4A; }\n/* 등록 7단계 */\n.g-stepper { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin: 0 0 10px; }\n.g-stepper div { text-align: center; font-size: .78rem; color: #4B5653; font-weight: 700; background: #F6F8F7; border-radius: 12px; padding: 10px 4px; }\n.g-stepper b { display: flex; margin: 0 auto 6px; width: 26px; height: 26px; border-radius: 50%; background: var(--accent); color: #fff;\n  align-items: center; justify-content: center; }\n/* 삭제 요청 흐름 */\n.g-flow { display: flex; align-items: center; gap: 8px; }\n.g-flow div { flex: 1; background: #F6F8F7; border-radius: 14px; padding: 14px; font-size: .9rem; line-height: 1.6; text-align: center; }\n.g-flow div .mi { display: block; color: var(--accent); font-size: 1.6rem; margin-bottom: 4px; }\n.g-flow > i.mi { color: #B3BCB9; font-style: normal; font-size: 1.4rem; }\n.g-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 10px; }\n.g-chips span { background: #fff; border: 1px solid #DDE5E3; border-radius: 999px; padding: 4px 12px; font-size: .85rem; }\n.g-phones { display: flex; gap: 22px; justify-content: center; flex-wrap: wrap; }\n.g-phones figure { margin: 0; width: 260px; text-align: center; }\n.g-phones img { width: 100%; border-radius: 26px; border: 6px solid #26302D; box-shadow: 0 10px 26px rgba(0,0,0,.15); }\n.g-phones figcaption { margin-top: 10px; font-size: .88rem; line-height: 1.6; color: #4B5653; }\n.g-end { margin: 36px 0 10px; text-align: center; font-size: 1.05rem; padding: 18px; border-radius: 16px; background: #EAF8F5; }\n@media (max-width: 640px) {\n  .g-hero { padding: 22px 18px; }\n  .g-hero-t { font-size: 1.45rem; }\n  .g-slide { flex-basis: 88%; }\n  .g-slide img { height: 180px; }\n  .g-nav { grid-template-columns: repeat(2, 1fr); }\n  .g-row { grid-template-columns: 1fr; }\n  .g-cols { grid-template-columns: 1fr; }\n  .g-stepper { grid-template-columns: repeat(4, 1fr); }\n  .g-flow { flex-direction: column; }\n  .g-flow > i.mi { transform: rotate(90deg); }\n  .g-tl-lab { width: 60px; font-size: .8rem; }\n}\n\n/* 3단계 배너 ‹ › (_DRAG_JS 가 붙인다): 사진 가운데 높이 */\n.g-slides-wrap { position: relative; }\n.g-slides { cursor: grab; scroll-behavior: smooth; scrollbar-width: none; }\n.g-slides::-webkit-scrollbar { display: none; }\n.aw-dragging { cursor: grabbing !important; scroll-behavior: auto !important; user-select: none; }\n.aw-arrow { position: absolute; z-index: 8; width: 36px; height: 36px; border-radius: 50%; border: 1px solid #DDE5E3;\n  background: rgba(255,255,255,.95); box-shadow: 0 2px 8px rgba(0,0,0,.12); color: #26302D; font-size: 22px; line-height: 32px;\n  text-align: center; cursor: pointer; padding: 0; display: none; }\n.aw-arrow:hover { border-color: var(--accent); color: var(--accent-deep); }\n.aw-arrow.l { left: -8px; } .aw-arrow.r { right: -8px; }\n.aw-arrow.show { display: block; }\n";

export const ICON_NAMES: string[] = ["add","add_circle","admin_panel_settings","arrow_forward","bookmark_add","bookmark_added","bookmarks","calendar_month","check_circle","delete","edit","error","event_note","expand_more","format_list_bulleted","forum","home","lightbulb","local_cafe","location_on","login","map","notifications","send","shield","smartphone"];

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
   "source": "github",
   "repo": "ayla-seoan/ANI-WHERE",
   "ref": "feat/cute-gnb@3cbc085",
   "package": ".",
   "paths": {
    "tokens": [
     "app_cafemap.py (GLOBAL_CSS :root, MINT*, CITY_COLORS, GANTT_COLOR, LIST_CSS, STORY_CSS, HOME_CSS)"
    ],
    "fonts": [
     "app_cafemap.py GLOBAL_CSS @import (Jua · Pretendard · NanumSquareRound)"
    ],
    "assets": [
     "static/logo.png",
     "static/logo_mint.png",
     "static/logo2.png",
     "static/ask_avatar.png",
     "static/default_poster.png"
    ],
    "docs": [
     "CLAUDE.md",
     "README.md",
     "docs/guide.md"
    ]
   },
   "synced": "2026-11-18"
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
     "name": "mint",
     "value": "#56c2a7",
     "usage": "브랜드 민트. 카드 테두리 계열·서울 지역 배지 바탕. 흰 글자를 올리면 2.3:1 이라 굵은 짧은 배지 글자에만 (원본 값 유지, 주의)."
    },
    {
     "name": "mint-deep",
     "value": "#2e9c82",
     "usage": "민트 글자. 카드 작품 이름, 보관함 제목."
    },
    {
     "name": "mint-soft",
     "value": "#e6f6f0",
     "usage": "배지·선택 상태처럼 좁은 곳의 민트 바탕."
    },
    {
     "name": "mint-line",
     "value": "#9eddcc",
     "usage": "포스터 카드 테두리 (2.5px). mint 보다 살짝 밝게."
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
     "name": "muted",
     "value": "#7b8784",
     "usage": "보조 글자 (기간, 장소, 설명). surface 위 3.9:1 — 13px 이상, 본문 대신 쓰지 않는다."
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
     "usage": "이미지가 없는 칸, 업로드 칸, 칩 바탕."
    },
    {
     "name": "gnb",
     "value": "#e9f7f2",
     "usage": "맨 위 메뉴바 바탕 (연민트, 아래 모서리 28px 둥글게)."
    },
    {
     "name": "coral",
     "value": "#ff6b6b",
     "usage": "등록하기 + 떠 있는 버튼, 새 알림 빨간 점, '새 알림' 글자. 한 화면에 한 곳만."
    },
    {
     "name": "blue",
     "value": "#2c5bc5",
     "usage": "오픈 예정 D-n 배지 글자, 별점 외 정보 강조."
    },
    {
     "name": "blue-soft",
     "value": "#eaf0fc",
     "usage": "D-n 칩 바탕."
    },
    {
     "name": "red",
     "value": "#d93a4a",
     "usage": "마감임박(3일 안에 끝남) 글자. 상태에만 쓰고 장식으로 쓰지 않는다."
    },
    {
     "name": "red-soft",
     "value": "#fdecee",
     "usage": "마감임박 칩 바탕."
    },
    {
     "name": "purple",
     "value": "#6c5ce7",
     "usage": "사전예약 D-n 배지 바탕 (흰 글자 4.6:1). 사전예약에만."
    },
    {
     "name": "orange",
     "value": "#f2a33a",
     "usage": "홈 '종료 D-n' 배지 바탕. 흰 글자는 굵게 12px 이상 (2.2:1, 원본 값 유지)."
    },
    {
     "name": "star",
     "value": "#f4b63f",
     "usage": "별점 채운 별."
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
       "usage": "포스터 카드 위 작품 이름."
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
       "usage": "메뉴바 탭. 고른 탭은 800 + 아래 3px 밑줄."
      },
      {
       "name": "small",
       "fontSize": "13px",
       "lineHeight": "1.5",
       "fontWeight": 400,
       "sample": "애니메이트 카페 홍대점 · 12.11 ~ 01.10",
       "usage": "카드 둘째 줄, 장소·기간."
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
  "radius": {
   "tokens": [
    {
     "name": "radius-sm",
     "value": "8px",
     "usage": "북마크 버튼, 작은 칩, 입력칸 안 버튼."
    },
    {
     "name": "radius-md",
     "value": "12px",
     "usage": "포스터 카드, 리뷰 상자."
    },
    {
     "name": "radius-lg",
     "value": "18px",
     "usage": "랭킹 배너, 랭킹 목록, 튜토리얼 카드."
    },
    {
     "name": "radius-pill",
     "value": "999px",
     "usage": "배지, 칩, 탭 알약, 스토리 동그라미."
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
 "readme": "# ANI:WHERE\n\n애니 팝업 · 콜라보 카페 · 굿즈 행사를 **찾고, 북마크하고, 놓치지 않게** 돕는 지도 서비스의 디자인 시스템.\n흰 바탕 위에 포인트만 우유빛 민트, 둥근 글꼴, 포스터가 주인공인 카드. 저장소 `ayla-seoan/ANI-WHERE` 의 실제 화면 코드(`app_cafemap.py`)에서 값을 그대로 옮겼다.\n\n## 말투 (콘텐츠 기본)\n\n- **친절한 존댓말, 짧게.** \"~해요 / ~예요\". 초등학생도 알아듣는 말로. 예: \"북마크한 팝업은 오픈·종료 3일 전부터 알려 드려요.\"\n- **사용자 쪽 말로 이름 짓기.** 기능 이름이 아니라 하는 일: `최애 추가하기`, `N건 더보기`, `팝업 N곳 표시`.\n- **안 될 때는 이유와 다음 할 일.** \"이 조건엔 행사가 없어요\" + `검색어 지우기 (12곳)` 버튼. 빈 표를 보여 주지 않는다.\n- **이모지 대신 아이콘.** 버튼·안내에는 Material Symbols Rounded (`:material/…:`, HTML 안에서는 `<span class=\"mi\">이름</span>`).\n- **숫자는 규칙으로 센 것만.** 물어보기 답의 건수·날짜는 `accent-deep` 굵게. AI 가 만든 글이면 'AI 산출', 규칙이면 '규칙 기반 대체' 를 기록에 남긴다.\n- 버튼·링크에 마우스를 올리면 뜨는 설명(`title`)은 쓰지 않는다. 설명은 제목·입력칸 옆 `?` 로만.\n\n## 색\n\n| 역할 | 토큰 | 쓰는 곳 |\n| --- | --- | --- |\n| 바탕 | `surface`, `surface-soft`, `gray-soft` | 페이지는 흰색. 칸·상자는 `surface-soft` |\n| 글자 | `ink`, `muted`, `subtle` | 본문 `ink`, 장소·기간 `muted`, 바닥글 `subtle` |\n| 포인트 | `accent`, `accent-deep`, `accent-soft` | 주 버튼·아이콘 `accent`, 포인트 글자 `accent-deep`, 고른 줄·오늘 칸 `accent-soft` |\n| 브랜드 민트 | `mint`, `mint-deep`, `mint-soft`, `mint-line` | 포스터 카드 테두리 `mint-line`, 카드 작품 이름 `mint-deep` |\n| 메뉴바 | `gnb` | 맨 위 메뉴바 바탕 하나에만 |\n| 강조 하나 | `coral` | 등록하기 + 떠 있는 버튼, 새 알림 점. 한 화면에 한 곳 |\n| 상태 | `blue`/`blue-soft` 오픈 예정 · `red`/`red-soft` 마감임박 · `purple` 사전예약 · `orange` 종료 D-n | 상태에만 쓴다. 장식으로 쓰지 않는다 |\n| 지역 | `city-*` | 지역 배지. 시마다 다른 색, 포스터 위에서는 진하게 채우고 흰 테두리 |\n\n명암: `ink` 는 흰 바탕 위 13:1. `accent` · `mint` · `orange` 위의 흰 글자와 `muted` · `subtle` 글자는 4.5:1 이 안 된다(원본 값 그대로 둠) — 굵은 짧은 배지 글자나 큰 글자에만 쓰고, 읽어야 하는 문장은 `ink` 로.\n\n## 글꼴\n\n- **제목 `display` (Jua)**: 화면 제목, 칸 제목, 포스터 카드 작품 이름. 둥글고 귀여운 애니 느낌을 맡는다.\n- **본문 `body` (NanumSquareRound → Pretendard)**: 나머지 전부. 메뉴바 탭, 버튼, 배지까지.\n- **아이콘 `icon` (Material Symbols Rounded)**: 글자와 같은 색·크기를 따른다.\n- 홈 칸 제목은 `home-heading`(본문 글꼴 800) + 앞에 `accent` 아이콘.\n\n## 모양 · 간격\n\n- 둥글게: 카드 `radius-md`, 배너·큰 칸 `radius-lg`, 배지·칩·탭 알약·스토리 동그라미 `radius-pill`.\n- 포스터가 주인공: 카드는 포스터를 꽉 채우고(3:4 또는 4:3), 글자는 아래에 한두 줄. 배지는 포스터 위 모서리에 — 왼쪽 위 상태, 오른쪽 위 지역.\n- 그림자는 떠 있는 것에만: `shadow-float`(등록 + · 물어보기 버튼), `shadow-card`(후기 카드). 평평한 카드에는 테두리(`mint-line` 또는 `line`).\n- 간격은 `space-*` 단계로. 홈 칸 사이 `space-5`, 카드 사이 `space-3`.\n\n## 배지 뜻 (어디서나 같게)\n\n| 글자 | 색 | 뜻 |\n| --- | --- | --- |\n| `진행 중` | `accent-deep` on `accent-soft` | 지금 열려 있음 |\n| `D-n` | `blue` on `blue-soft` | n일 뒤에 열림 |\n| `마감임박` | `red` on `red-soft` | 3일 안에 끝남 |\n| `사전예약 D-n` | 흰 글자 on `purple` | 예약해야 들어감, n일 뒤 열림 |\n| `종료 D-n` · `오늘 종료` | 흰 글자 on `orange` | 이번 주에 끝남 (홈) |\n\n## 아이콘 (Iconography)\n\nMaterial Symbols Rounded 만 쓴다. 자주 쓰는 것: `bookmark_add` / `bookmark_added`(북마크), `map`, `format_list_bulleted`, `calendar_month`, `search`, `notifications`, `location_on`, `local_fire_department`(랭킹), `fiber_new`(신규), `hourglass_bottom`(이번 주), `event_available`(사전예약), `rate_review`(후기), `auto_awesome`(비슷한 팝업), `add`(등록·최애 추가). 아이콘은 혼자 뜻을 나르지 않는다 — 늘 글자와 함께.\n\n## 로고 · 그림\n\n`Logos` 묶음: 기본 로고(`logo.png`), 민트 로고(`logo_mint.png`), 보조 로고(`logo2.png`). 메뉴바 왼쪽에 두고, 누르면 홈. `Images` 묶음: 물어보기 도우미 얼굴(`ask_avatar.png`), 포스터가 없을 때 대신 보이는 기본 포스터(`default_poster.png`). 로고는 다시 그리지 않고 파일 그대로 쓴다.\n\n## 계절 배경\n\n내 캘린더 화면에서만 3~5월 꽃잎 · 6~8월 잎사귀 · 9~11월 단풍 · 12~2월 눈이 천천히 떨어진다(작은 SVG, 클릭을 막지 않음, '동작 줄이기' 설정이면 끔).\n\n## 옮기지 않은 것 (Not synced)\n\n- 글꼴 파일: Jua 는 Google Fonts, NanumSquareRound · Pretendard 는 jsDelivr 의 CSS 로 불러온다. 파일은 저장소에 없어 `type.fonts` 는 비어 있고 이름만 `type.families` 에 있다.\n- 컴포넌트: 앱은 Streamlit(파이썬)이라 React 라이브러리가 없다. 아래 5개 카드(배지 · 버튼 · 포스터 카드 · 북마크 팝업 동그라미 · 칩)는 `app_cafemap.py` 의 CSS 를 보고 **손으로 옮긴 정적 모습**이다.\n- 다크 모드: 앱에 없어 테마는 Light 하나.\n",
 "css": "/* ANI:WHERE 정적 컴포넌트 모습 — app_cafemap.py 의 CSS 를 손으로 옮김 (토큰 이름으로) */\n.aw { font-family: var(--font-body); color: var(--ink); }\n.aw .mi { font-family: var(--font-icon); font-weight: normal; font-style: normal; line-height: 1; font-size: 1.15em;\n  display: inline-block; vertical-align: -0.15em; -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; }\n\n/* 배지 */\n.aw-badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: var(--radius-pill);\n  font-size: 12px; font-weight: 800; line-height: 1.4; white-space: nowrap; }\n.aw-badge.live { color: var(--accent-deep); background: var(--accent-soft); }\n.aw-badge.soon { color: var(--blue); background: var(--blue-soft); }\n.aw-badge.closing { color: var(--red); background: var(--red-soft); }\n.aw-badge.reserve { color: #ffffff; background: var(--purple); }\n.aw-badge.ends { color: #ffffff; background: var(--orange); }\n.aw-badge.area { color: #ffffff; border: 1.5px solid rgba(255,255,255,.8); }\n\n/* 버튼 */\n.aw-btn { font-family: var(--font-body); font-size: 14px; font-weight: 700; border-radius: var(--radius-pill); padding: 8px 18px;\n  border: 1px solid var(--line); background: var(--surface); color: var(--ink); display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }\n.aw-btn.primary { background: var(--accent); border-color: var(--accent); color: #ffffff; }\n.aw-btn.more { background: var(--gray-soft); border-color: var(--gray-soft); color: var(--muted); }\n.aw-btn.tertiary { background: transparent; border-color: transparent; color: var(--muted); padding: 8px 6px; }\n.aw-fab { width: 56px; height: 56px; border-radius: 50%; background: var(--coral); color: #ffffff; border: 0;\n  display: inline-flex; align-items: center; justify-content: center; box-shadow: var(--shadow-float); font-size: 28px; }\n.aw-bm { width: 30px; height: 30px; border-radius: var(--radius-sm); border: 0; display: inline-flex; align-items: center;\n  justify-content: center; font-size: 20px; color: var(--ink); background: rgba(255,255,255,.3); }\n.aw-bm.on { background: var(--accent); color: #ffffff; }\n\n/* 포스터 카드 */\n.aw-card { position: relative; width: 210px; border: 2.5px solid var(--mint-line); border-radius: var(--radius-md); overflow: hidden;\n  aspect-ratio: 3 / 4; background: var(--gray-soft) center / cover no-repeat; box-sizing: border-box; }\n.aw-card .tl { position: absolute; left: 10px; top: 10px; }\n.aw-card .tr { position: absolute; right: 10px; top: 10px; }\n.aw-card .info { position: absolute; left: 0; right: 0; bottom: 0; padding: 40px 14px 12px;\n  background: linear-gradient(transparent, rgba(0,0,0,.72)); color: #ffffff; }\n.aw-card .t { font-family: var(--font-display); font-size: 17px; line-height: 1.25; }\n.aw-card .s, .aw-card .d { font-size: 12px; opacity: .92; margin-top: 2px; }\n.aw-card .bm { position: absolute; right: 12px; bottom: 12px; }\n\n/* 북마크 팝업 동그라미 (스토리) */\n.aw-story { display: inline-flex; flex-direction: column; align-items: center; width: 84px; }\n.aw-story .ring { position: relative; width: 72px; height: 72px; border-radius: 50%; padding: 3px; box-sizing: border-box;\n  background: conic-gradient(from 210deg, var(--coral), #ffb86b, #ffd66b, var(--coral)); }\n.aw-story .pic { width: 100%; height: 100%; border-radius: 50%; border: 3px solid #ffffff; box-sizing: border-box;\n  background: var(--gray-soft) center / cover no-repeat; }\n.aw-story .rg { position: absolute; left: 50%; top: -7px; transform: translateX(-50%); font-size: 10px; font-weight: 800;\n  color: #ffffff; background: var(--accent-deep); padding: 1px 7px; border-radius: var(--radius-pill); border: 1.5px solid #ffffff; white-space: nowrap; }\n.aw-story .nm { margin-top: 6px; width: 84px; text-align: center; font-size: 12.5px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n.aw-story.add .ring { background: none; border: 2px dashed #d3dad8; display: flex; align-items: center; justify-content: center;\n  color: var(--accent-deep); font-size: 32px; }\n\n/* 칩 (지역 고르기 · 추천 질문) */\n.aw-chip { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: var(--radius-pill); font-size: 13px;\n  border: 1px solid var(--line); background: var(--surface); color: var(--ink); }\n.aw-chip.on { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-deep); font-weight: 700; }\n/* 표지 꾸밈 (docs/design/components/Cover.html) */\n.cv { position: relative; width: 960px; height: 300px; background: var(--surface); overflow: hidden; }\n    .cv svg { position: absolute; inset: 0; }\n    .cv .accent { fill: var(--accent); } .cv .deep { fill: var(--mint-deep); } .cv .coral { fill: var(--coral); }\n    .cv .tint { fill: var(--gnb); } .cv .line { fill: var(--mint-line); } .cv .soft { fill: var(--accent-soft); }\n    .cv .ring { fill: none; stroke: var(--surface); stroke-width: 3; }\n    .cv .slab { rx: var(--radius-lg); } .cv .pill { rx: 30px; }\n    .cv .txt { position: absolute; left: 48px; bottom: 44px; max-width: 440px; }\n    .cv .name { font-family: var(--font-display); font-size: 80px; line-height: .95; color: var(--ink); }\n    .cv .tag { margin-top: 12px; font-family: var(--font-body); font-size: 14px; color: var(--muted); }\n",
 "components": {
  "Badge.html": "<div class=\"aw\" style=\"display:flex;gap:8px;flex-wrap:wrap;padding:16px;align-items:center\"><span class=\"aw-badge live\">진행 중</span><span class=\"aw-badge soon\">D-5</span><span class=\"aw-badge closing\">마감임박</span><span class=\"aw-badge reserve\">사전예약 D-5</span><span class=\"aw-badge ends\">종료 D-1</span><span class=\"aw-badge area\" style=\"background:var(--city-busan)\">부산</span><span class=\"aw-badge area\" style=\"background:var(--city-seoul)\">마포</span></div>\n",
  "Badge.md": "# Badge\n\n팝업의 지금 상태나 지역을 짧게 알려 주는 알약 모양 표시.\n\n- 상태 배지는 포스터 왼쪽 위, 지역 배지는 오른쪽 위. 한 카드에 상태 하나, 지역 하나.\n- 뜻은 어디서나 같게: `진행 중`(accent-deep on accent-soft) · `D-n`(blue on blue-soft) · `마감임박`(red on red-soft, 3일 안에 끝남) · `사전예약 D-n`(흰 글자 on purple) · `종료 D-n`(흰 글자 on orange).\n- 지역 배지 바탕은 `city-*` 토큰 (포스터 위에서는 진하게 채우고 흰 테두리).\n- 쓰는 쪽이 정하는 것: 글자, 종류(live · soon · closing · reserve · ends · area).\n\n손으로 옮김: `app_cafemap.py` 의 `.cstate`, `.hcbadge`, `_area_badge`.\n",
  "Button.html": "<div class=\"aw\" style=\"display:flex;gap:10px;flex-wrap:wrap;padding:16px;align-items:center\"><span role=\"button\" class=\"aw-btn primary\"><span class=\"mi\">check_circle</span>저장하기</span><span role=\"button\" class=\"aw-btn\">취소</span><span role=\"button\" class=\"aw-btn more\"><span class=\"mi\">expand_more</span>92건 더보기</span><span role=\"button\" class=\"aw-btn tertiary\">다음에 할게요</span><span role=\"button\" class=\"aw-fab\" aria-label=\"등록하기\"><span class=\"mi\">add</span></span><span style=\"display:inline-flex;gap:6px;padding:6px;border-radius:10px;background:#56c2a7\"><span role=\"button\" class=\"aw-bm\" aria-label=\"북마크\"><span class=\"mi\">bookmark_add</span></span><span role=\"button\" class=\"aw-bm on\" aria-label=\"북마크됨\"><span class=\"mi\">bookmark_added</span></span></span></div>\n",
  "Button.md": "# Button\n\n누르면 일이 일어나는 버튼. 글자는 하는 일 그대로 (`저장하기`, `최애 추가하기`, `92건 더보기`).\n\n- `primary`(accent 바탕): 한 화면에서 가장 중요한 한 가지 (저장하기, 리뷰 등록).\n- 기본(흰 바탕 + line 테두리): 그 밖의 선택.\n- `more`(gray-soft): 목록 아래 `N건 더보기` — 앞에 `expand_more` 아이콘.\n- `tertiary`: 글자만 (취소, 다음에 할게요, 더보기 링크).\n- 떠 있는 등록 버튼(FAB)은 `coral` 동그라미 하나, 화면 오른쪽 아래에만.\n- 북마크 버튼: 안 한 상태는 흰 바탕 70% 투명, 한 상태는 accent 바탕 + 흰 아이콘.\n- 버튼에 마우스를 올리면 뜨는 설명(title)은 쓰지 않는다.\n\n손으로 옮김: `app_cafemap.py` 의 `.st-key-add_btn`, `.st-key-list_more`, `[class*=st-key-fav_]`.\n",
  "Chip.html": "<div class=\"aw\" style=\"display:flex;gap:6px;flex-wrap:wrap;padding:16px\"><span class=\"aw-chip on\">전체</span><span class=\"aw-chip\">마포</span><span class=\"aw-chip\">부산</span><span class=\"aw-chip\">송파</span><span class=\"aw-chip\">이번 주말 홍대 팝업</span><span class=\"aw-chip\">내 주변 가까운 팝업</span></div>\n",
  "Chip.md": "# Chip\n\n여러 개 중 하나를 고르거나, 눌러서 바로 물어보는 작은 알약.\n\n- 홈 칸의 지역 고르기(`전체 · 마포 · 부산 · 송파`), 물어보기의 추천 질문.\n- 고른 칩: `accent` 테두리 + `accent-soft` 바탕 + `accent-deep` 굵은 글자.\n- 한 줄에 다 안 들어가면 다음 줄로 넘긴다 (가로 스크롤 없음).\n\n손으로 옮김: `app_cafemap.py` 의 홈 `st.pills`, `.apn-chips`.\n",
  "Cover.html": "<div class=\"cv\">\n  <svg viewBox=\"0 0 960 300\" width=\"960\" height=\"300\" aria-hidden=\"true\">\n    <!--\n      blocks: accent 200×240 slab (radius-lg) · mint-deep 240×120 slab bleeding right · gnb tint 240×140 slab · coral pill 120×60\n      arrangement: one tall slab with satellites, the slab and the deep block bleed off the top and right edges\n      pattern: discs from the radius scale (\"둥글고 귀여운\", 스토리 동그라미) — 12 mint-line discs on the tint block, 3 surface rings on the slab\n      steps/radii: radius-lg 18, radius-pill for the pill and discs (r = half the side), pitch 36 = space-3 × 3\n    -->\n    <rect class=\"accent slab\" x=\"520\" y=\"-24\" width=\"200\" height=\"244\" />\n    <rect class=\"deep slab\" x=\"740\" y=\"36\" width=\"244\" height=\"120\" />\n    <rect class=\"tint slab\" x=\"740\" y=\"172\" width=\"244\" height=\"150\" />\n    <rect class=\"coral pill\" x=\"560\" y=\"236\" width=\"120\" height=\"60\" />\n    <circle class=\"ring\" cx=\"580\" cy=\"64\" r=\"26\" /><circle class=\"ring\" cx=\"652\" cy=\"112\" r=\"26\" /><circle class=\"ring\" cx=\"580\" cy=\"160\" r=\"26\" />\n    <g class=\"line\">\n      <circle cx=\"772\" cy=\"204\" r=\"12\" /><circle cx=\"808\" cy=\"204\" r=\"12\" /><circle cx=\"844\" cy=\"204\" r=\"12\" /><circle cx=\"880\" cy=\"204\" r=\"12\" />\n      <circle cx=\"772\" cy=\"240\" r=\"12\" /><circle cx=\"808\" cy=\"240\" r=\"12\" /><circle cx=\"844\" cy=\"240\" r=\"12\" /><circle cx=\"880\" cy=\"240\" r=\"12\" />\n      <circle cx=\"772\" cy=\"276\" r=\"12\" /><circle cx=\"808\" cy=\"276\" r=\"12\" /><circle cx=\"844\" cy=\"276\" r=\"12\" /><circle cx=\"880\" cy=\"276\" r=\"12\" />\n    </g>\n  </svg>\n  <div class=\"txt\">\n    <div class=\"name\">ANI:WHERE</div>\n    <div class=\"tag\">함께 만드는 애니 팝업 지도. 찾고, 북마크하고, 놓치지 않게.</div>\n  </div>\n</div>\n",
  "PosterCard.html": "<div class=\"aw\" style=\"display:flex;gap:14px;padding:16px\"><div class=\"aw-card\" style=\"background-image:url(app/static/default_poster.png)\"><span class=\"tl aw-badge soon\" style=\"background:#fff\">D-23</span><span class=\"tr aw-badge area\" style=\"background:var(--city-seoul)\">마포</span><div class=\"info\"><div class=\"t\">Blackish House</div><div class=\"s\"><span class=\"mi\">local_cafe</span> 애니메이트 카페 홍대점</div><div class=\"d\">12월 11일 ~ 01월 10일</div></div><span role=\"button\" class=\"bm aw-bm\" aria-label=\"북마크\"><span class=\"mi\">bookmark_add</span></span></div><div class=\"aw-card\" style=\"background-image:url(app/static/default_poster.png)\"><span class=\"tl aw-badge closing\" style=\"background:#fff\">마감임박</span><span class=\"tr aw-badge area\" style=\"background:var(--city-busan)\">부산</span><div class=\"info\"><div class=\"t\">BanG Dream!</div><div class=\"s\"><span class=\"mi\">local_cafe</span> 애니메이트 카페 부산점</div><div class=\"d\">10월 09일 ~ 11월 19일</div></div><span role=\"button\" class=\"bm aw-bm on\" aria-label=\"북마크됨\"><span class=\"mi\">bookmark_added</span></span></div></div>\n",
  "PosterCard.md": "# PosterCard\n\n팝업 하나를 포스터로 보여 주는 리스트 카드. 누르면 상세가 열린다.\n\n- 포스터가 카드를 꽉 채우고(3:4), 아래 그림자 위에 작품 이름(`card-title`, Jua) · 장소 · 기간.\n- 왼쪽 위 상태 Badge, 오른쪽 위 지역 Badge, 오른쪽 아래 북마크 버튼.\n- 테두리는 `mint-line` 2.5px, 모서리 `radius-md`. 마우스를 올리면 살짝 작아지며 특전·주소가 펼쳐진다.\n- 포스터가 없으면 기본 포스터(`Images/default_poster.png`).\n- 쓰는 쪽이 정하는 것: 포스터, 작품 이름, 장소, 기간, 상태, 지역, 북마크 여부.\n\n손으로 옮김: `app_cafemap.py` 의 `_poster_card`, `.pcard`.\n",
  "StoryCircle.html": "<div class=\"aw\" style=\"display:flex;gap:8px;padding:20px 16px 8px\"><div class=\"aw-story add\"><div class=\"ring\"><span class=\"mi\">add</span></div><div class=\"nm\">최애 추가하기</div></div><div class=\"aw-story\"><div class=\"ring\"><span class=\"rg\">마포</span><div class=\"pic\" style=\"background-image:url(app/static/default_poster.png)\"></div></div><div class=\"nm\">명탐정 코난</div></div><div class=\"aw-story\"><div class=\"ring\"><span class=\"rg\">서귀포</span><div class=\"pic\" style=\"background-image:url(app/static/default_poster.png)\"></div></div><div class=\"nm\">원피스 대해적시대</div></div></div>\n",
  "StoryCircle.md": "# StoryCircle\n\n홈 '북마크 팝업' 줄의 동그라미. 내가 북마크한 팝업 하나에 하나, 누르면 그 팝업 상세.\n\n- 72px 동그라미, 코랄→노랑 고리, 흰 3px 테두리 안에 포스터.\n- 위에 지역 이름(`accent-deep` 알약), 아래 작품 이름 한 줄(넘치면 …).\n- 맨 앞은 늘 `최애 추가하기`(점선 동그라미 + `add`) — 팝업을 골라 한 번에 북마크하는 창을 연다.\n- 줄이 길면 마우스로 끌거나 양옆 ‹ › 로 넘긴다.\n\n손으로 옮김: `app_cafemap.py` 의 `render_stories`, `STORY_CSS`.\n"
 }
} as never;

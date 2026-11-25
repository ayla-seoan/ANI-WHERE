# ANI:WHERE 공개 웹 (`web/`)

애니 팝업스토어·콜라보 카페를 **찾고 → 가기 전에 판단하는** 웹입니다. Streamlit 앱과 같은 계정으로 로그인해 북마크·리뷰·내 캘린더를 쓸 수 있습니다. Next.js(App Router) + PWA 라서 휴대폰 홈 화면에 앱처럼 설치됩니다.

## 왜 따로 만들었나

| | Streamlit 앱 (`app_cafemap.py`) | 공개 웹 (`web/`) |
|---|---|---|
| 하는 일 | 등록·수정·리뷰·검수·관리자 | 찾기·확인 + 회원 기능(로그인·북마크·리뷰·내 캘린더·닉네임) |
| 사용자 | 운영자, 정보를 고치는 팬 | 현장에 가려는 모든 팬 |
| 속도 | 서버가 깨어나는 데 수십 초, 화면마다 파이썬 실행 | 미리 만든 HTML(ISR) 을 바로 보냄 |
| 휴대폰 | 브라우저 탭 | 홈 화면 설치, 한 번 본 화면은 오프라인에서도 열림 |

- 팝업은 **현장에 가는 것**이 목적이라, 사용자는 이동 중에 휴대폰으로 "지금 열려 있나, 언제까지인가, 어디인가, 특전이 뭔가"만 빨리 확인하면 됩니다. 이 순간에 Streamlit 의 느린 첫 로딩은 이탈 원인이 됩니다.
- 회원 기능은 Streamlit 과 **같은 표(members · favorites · reviews)와 같은 규칙**으로 서버 코드에서만 씁니다 (아래 '회원 기능'). 팝업 등록 · 정보 수정 · 사진 올리기 · 블로그 후기 · 관리자는 파일 저장소·외부 API 가 있는 Streamlit 앱에 두고, 웹은 그쪽으로 가는 링크만 둡니다.
- 데이터 출처는 화면 아래에 항상 표시합니다 (`데이터: Supabase` / `데이터: GitHub 공개 데이터`). "AI 산출 / 규칙 기반 대체" 를 늘 표시하는 프로젝트 원칙과 같은 이유입니다.

## 화면

앱(Streamlit, `app_cafemap.py`)과 같은 모양으로 맞췄습니다 (PC 1440px · 모바일 390px 기준, 모바일 = 폭 640px 이하). 메뉴바는 앱과 같은 연민트 바탕에 **홈 · 지도로 보기 · 리스트로 보기 (· 회원이면 내 캘린더)** 탭, 오른쪽은 검색(지도·리스트) · 알림 종(회원) · 관리자(관리자 회원, 앱 관리자 화면 링크) · 로그인 / 프로필 사진입니다.

| 주소 | 내용 |
|---|---|
| `/` 홈 | 특전 있는 작품들(11/20: 동그란 포스터 · 특전 있는 팝업 수, 예전 '요즘 일정 많은 작품') · 실시간 인기 급상승 랭킹 5위(배너 + 목록) · 따끈따끈 신규 등록 · 곧 끝나는 팝업(11/20: 어제부터 7일 칸 — 금요일이면 목 ~ 다음 주 수, 날짜마다 2곳 + 더보기) · 사전예약 팝업 · 꿀팁 가득! 실시간 후기 모음(11/20 요청으로 추가 — 상세에 이미 보이는 리뷰를 홈에도. 원글 · 본문 있는 것, 사진 있는 리뷰 먼저 12개, `lib/server/member.ts` 의 `homeReviews`) |
| `/map` 지도로 보기 | 데일리 팝업 노트 · 지도(카카오맵, 키가 없거나 실패하면 OpenStreetMap) · 팝업 목록. 검색 필터(검색 · 지역 · 진행여부 · 날짜)는 메뉴바 검색 아이콘(모바일은 필터 아이콘)으로 연다 |
| `/list` 리스트로 보기 | 포스터 카드 4열(모바일 2~3열) · 같은 검색 필터 · 지역 고르기 · 정렬(최신순 · 등록순 · 오픈 임박순 · 종료 임박순) · 24장씩 'N건 더보기'. 조건은 주소창(`?q=&area=&span=&day=&work=&reserve=&sort=`)에 남는다 |
| `/popup/[id]` 상세 | 이미지 슬라이드 · 지역/상태 · 북마크 · 방문 전 확인(위치 · 일정) · 혜택(특전 · 굿즈 · 이벤트) · 참고 웹사이트(recal.kr 은 맨 뒤) · 팝업 소개 · 오른쪽 리뷰(쓰기 · 별점 · 답글 · 내 글 수정·삭제) · 비슷한 팝업 / 이 근처 다른 팝업 |
| `/login` | 손님: 로그인 · 회원가입(아이디) · 카카오·네이버 간편 로그인. 회원: 마이페이지 '내 계정'(닉네임 바꾸기 · 기본 사진 · 비밀번호 바꾸기 · 로그아웃 · 탈퇴) |
| `/auth` | 카카오·네이버가 돌려보내는 주소 (Redirect URI). 처음 온 사람은 `/auth/join` '거의 다 됐어요'(닉네임 · 동의) |
| `/calendar` 내 캘린더 | 회원만. 북마크한 팝업 달력 막대 + 곧 있는 팝업 · 북마크 / 다녀온 팝업 / 최근 본 팝업 · 알림 받은 내역(최근 3일) |
| `/this-week` | 오늘~이번 주 일요일과 기간이 겹치는 팝업을 지역별로 |
| `/offline` | 인터넷이 끊겼고 그 화면이 저장돼 있지 않을 때 서비스 워커가 보여 주는 화면 |

- '실시간 인기 급상승'은 앱과 같은 규칙입니다 (11/19, 11/20 완전히 맞춤): 최근 7일 북마크 수 × 2 + 리뷰 · 답글 수 → 같으면 전체 기간 점수 → 같으면 오픈이 빠른 순 → 같으면 팝업 번호 순. 규칙은 `lib/rank.ts`(앱 `common/rank.py` 와 같음, 시험 `npm run test:rank` = `samples/rank_cases.json`), 서버는 북마크 · 리뷰 표에서 팝업별 개수만 넘긴다 (`lib/server/rank.ts`). 예전엔 공개 별점 수 → 진행 중 → 곧 끝나는 순으로 따로 정했다.
- 앱의 '인기순 · 리뷰 많은 순' 정렬은 이 웹에 없습니다 (북마크 수 집계를 공개 화면에 쓰지 않음).

## 회원 기능

| | 어떻게 | Streamlit 과 같게 맞춘 것 |
|---|---|---|
| 로그인 쿠키 | `aw_session` = base64url(JSON {k,p,e}) + '.' + HMAC-SHA256(`AUTH_SECRET`) 앞 32자, 30일, 서버가 HttpOnly·Secure·SameSite=Lax 로 심는다 | `common/auth.py` make_session/read_session 과 같은 모양 (`npm run test:auth` 가 서로 읽히는지 확인) |
| 간편 로그인 | 카카오(prompt=select_account) · 네이버(auth_type=reauthenticate), 서명한 `state`(10분), Redirect URI `{SITE_URL}/auth` | 회원 번호 = sha256(`{REVIEW_NICK_SALT}:member:{수단}:{고유번호}`)[:16] — 같은 사람은 두 사이트에서 같은 회원 |
| 아이디 가입 | Supabase DB 함수 `register_login` / `check_login` / `change_password` / `drop_login` (005, bcrypt). 비밀번호 원문·해시는 서버를 거쳐 DB 함수로만 | 아이디 규칙 · 비밀번호 규칙 · 닉네임 10자 · 욕설/사칭 · 전화번호·이메일 막기 · 닉네임 비우면 자동 닉네임(같은 알고리즘) · 5번 틀리면 5분 잠금 |
| 동의 | [필수] 만 14세 이상 · 이용약관 · 개인정보 수집·이용, '약관 전체 동의', 수집 항목 표 | 같은 문구 · 같은 표 (`PRIVACY_TABLE`) |
| 북마크 | favorites 에 `m:<회원 번호>` · `entry_id = 사람:팝업` 으로 새 행 (해제 = deleted 행) | `common/favorite.py` |
| 리뷰 | reviews 에 '닉네임#m네 글자' 로 새 행. 수정·삭제도 새 revision. 내 글 확인은 끝 꼬리표 (DB 정책 `review_owner_ok` 도 같은 규칙) | `review.validate`(1000자 · 민감정보) · 다녀온 후기 별점 · 답글 한 단계 · 작성자는 지금 닉네임·사진으로 |
| 알림 종 | 북마크한 팝업 오픈 D-3 ~ 당일 · 종료 D-3 ~ 당일 + 관리자 공지(notices) · 관리자가 고친 규칙(alert_rules) | `_notices` · `_inbox`. 읽음 표시는 브라우저(localStorage)에만 |
| 탈퇴 | members 에 deleted 행 → DB 함수 `purge_withdrawn` (009) | 같은 순서 |

- **모든 쓰기는 서버 코드에서만** (`app/actions.ts` 서버 액션 · `app/auth/route.ts`) — 브라우저는 Supabase 주소·키를 모릅니다. anon 키만 씁니다 (RLS: SELECT·INSERT 만, 고치기·지우기 권한 없음 → append-only).
- 웹에 없는 것 (Streamlit 링크): 팝업 등록(오른쪽 아래 +) · 정보 수정하기 · 프로필/리뷰 사진 올리기(파일 저장소가 앱 서버에 있음) · 블로그 후기(네이버 검색 API) · 관리자 대시보드 · 삭제 요청.
- 시험은 실제 DB 가 아니라 local 저장소로:
  ```bash
  npm run build
  WEB_STORAGE=local WEB_DATA_DIR=<빈 임시 폴더> WEB_OAUTH_MOCK=1 AUTH_SECRET=test-secret-1234567890 \
    SITE_URL=http://localhost:3100 npx next start -p 3100
  python -X utf8 scripts/e2e_member.py http://localhost:3100 <같은 임시 폴더>
  npm run test:auth    # 로그인 쿠키·회원 번호·자동 닉네임·민감정보 규칙이 파이썬과 같은지
  ```
- 자동 닉네임에 쓰는 캐릭터 목록은 `lib/server/characters.json` (작품 목록을 바꾸면 `python web/scripts/make_characters.py`).

## 데이터 흐름

```
Notion DB (주간 수집)
   │  매주 월 10:00 KST GitHub Actions (scripts/notion_import.py)
   ▼
data/cafes.json (append-only, GitHub 저장소)  ◀── Streamlit 앱에서 등록·수정
   │  scripts/migrate_to_supabase.py
   ▼
Supabase  cafes 표 (RLS: SELECT·INSERT 만)
   │  supabase/migrations/002_public_views.sql
   ▼
popups_current 뷰 (entry_id 별 최신 revision 중 active)  +  popup_ratings 뷰 (별점 평균)
   │  REST  GET /rest/v1/popups_current   (anon 키, 서버에서만)
   ▼
web/lib/data.ts  ── fetch 캐시 10분 (ISR, revalidate=600)
   │
   ▼
Next.js 서버 컴포넌트가 HTML 을 만들어 보냄 → 브라우저 (키는 내려가지 않음)

* SUPABASE_URL / SUPABASE_ANON_KEY 가 없거나 Supabase 가 실패하면
  GitHub raw 의 data/cafes.json 을 읽어 같은 규칙(최신 revision · active)으로 계산한다.
```

- 데이터를 읽는 코드는 `lib/data.ts` 하나뿐이고 `import "server-only"` 로 막아 두어 브라우저 번들에 들어갈 수 없습니다.
- 환경변수에 `NEXT_PUBLIC_` 을 붙이지 않습니다. 붙이면 키가 브라우저 JS 에 박힙니다.
- 이상한 행(날짜 없음, 좌표가 한국 밖, 빈 칸, 깨진 이미지 이름)은 건너뛰거나 기본값으로 바꿉니다. 날짜가 없는 행은 '전체' 탭에만 "기간 미정" 으로 나오고 진행 중·예정·이번 주 목록에서는 빠집니다.
- 이미지는 `images` 칸의 파일 이름을 `https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/static/uploads/<이름>` 으로 바꿔 씁니다. 첫 번째가 포스터이고, 없거나 깨지면 기본 그림을 씁니다.

## 로컬 실행

```bash
cd web
npm install
npm run dev          # http://localhost:3000  (서비스 워커는 production 에서만 켜짐)
```

환경변수 없이도 GitHub 공개 데이터로 바로 동작합니다. Supabase 를 쓰려면:

```bash
cp .env.example .env.local
# SUPABASE_URL=https://xxxx.supabase.co
# SUPABASE_ANON_KEY=<anon public 키>
```

배포와 같은 모드로 확인:

```bash
npm run build
npm run start -- -p 3100
```

## Vercel 배포

1. https://vercel.com → **Add New… > Project** → GitHub 저장소 `ANI-WHERE` 를 Import.
2. **Root Directory** 를 `web` 으로 바꿉니다 (Framework Preset 은 Next.js 로 자동 인식). Build/Install 명령은 기본값 그대로 둡니다.
3. **Environment Variables** (선택 — 비우면 GitHub 공개 데이터로 동작):
   - `SUPABASE_URL` = `https://xxxx.supabase.co`
   - `SUPABASE_ANON_KEY` = Supabase 대시보드 > Project Settings > API 의 **anon public** 키
   - **service_role 키는 절대 넣지 않습니다.** RLS 를 건너뛰어 수정·삭제까지 됩니다. 이 웹은 읽기만 하므로 anon 키로 충분합니다.
   - `NEXT_PUBLIC_` 접두사를 붙이지 않습니다.
   - `SITE_URL` = `https://ani-where.vercel.app` (공유 미리보기 · 간편 로그인 Redirect URI `{SITE_URL}/auth`)
   - `AUTH_SECRET` = Streamlit Secrets 의 `AUTH_SECRET` 과 **같은 값** (16자 이상)
   - `REVIEW_NICK_SALT` = Streamlit 에 넣었다면 같은 값 (안 넣었다면 비움 — 둘 다 기본값)
   - `KAKAO_LOGIN_CLIENT_ID` · `KAKAO_LOGIN_CLIENT_SECRET` · `NAVER_LOGIN_CLIENT_ID` · `NAVER_LOGIN_CLIENT_SECRET` = Streamlit 과 같은 앱 키. 카카오·네이버 개발자 콘솔의 Redirect(Callback) URI 에 `https://ani-where.vercel.app/auth` 를 추가 등록 (네이버는 서비스 URL 에 `https://ani-where.vercel.app` 도)
   - (선택) `ADMIN_MEMBER_KEYS` = Streamlit 과 같게
   - `WEB_STORAGE` · `WEB_DATA_DIR` · `WEB_OAUTH_MOCK` 은 **넣지 않습니다** (시험용)
   - (선택) `NEXT_PUBLIC_KAKAO_JS_KEY` = 카카오 개발자 콘솔 > 내 애플리케이션 > 앱 키 > **JavaScript 키**. 브라우저에 그대로 보이는 공개용 키라 `NEXT_PUBLIC_` 을 붙이는 유일한 값입니다 (REST API 키·Admin 키는 넣지 않음). 같은 콘솔 > 플랫폼 > **Web 사이트 도메인**에 `https://ani-where.vercel.app` 을 등록해야 지도가 뜹니다. 비우거나 도메인이 등록되지 않으면 `/map` 은 OpenStreetMap 지도로 대신 보입니다. 빌드 때 코드에 들어가므로 바꾼 뒤에는 다시 배포합니다.
   - (선택, 11/20) `GITHUB_TOKEN` = 저장소를 **비공개**로 바꿀 때만. 공개 백업 데이터 · 예전 사진(`/img/…`)을 서버가 읽을 때 쓰는 읽기 전용 토큰(Contents: Read). `GITHUB_RAW` 로 원본 주소도 바꿀 수 있다 (기본은 지금 저장소). 둘 다 서버 전용 — 브라우저에는 깃허브 주소가 나오지 않는다
4. Deploy. 이후 `main` 에 push 하면 자동 배포됩니다. 데이터는 배포 없이도 10분마다 새로 읽습니다. `WEB_REVALIDATE_SECRET` 을 넣어 두면 Streamlit · GitHub Actions 가 Notion 에서 새 팝업을 넣은 직후 `POST /api/revalidate` 로 캐시를 비워 바로 보입니다 (11/25).
5. Supabase 를 쓴다면 `supabase/migrations/002_public_views.sql` 이 먼저 적용돼 있어야 합니다 (`popups_current`, `popup_ratings` 뷰). 없으면 자동으로 GitHub 데이터로 내려가고 화면 아래에 이유가 표시됩니다.

`vercel.json` 은 필요 없습니다 (헤더 설정은 `next.config.ts` 에 있음).

## PWA 확인 방법

1. `npm run build && npm run start -- -p 3100` 후 Chrome 으로 http://localhost:3100 접속 (localhost 는 https 가 아니어도 서비스 워커가 동작).
2. DevTools(F12) > **Application**
   - **Manifest**: 이름 ANI:WHERE, 아이콘 192/512/maskable, `display: standalone`, 오류 없음 확인. "Maskable icon" 미리보기로 잘림 확인.
   - **Service Workers**: `/sw.js` 가 *activated and is running* 인지 확인.
   - **Cache Storage**: `aniwhere-static-v1`, `aniwhere-pages-v1`, `aniwhere-images-v1` 가 생기는지 확인.
3. **오프라인**: Network 탭에서 *Offline* 체크 → 한 번 열어 본 팝업 상세는 그대로 열리고, 안 가 본 주소는 `/offline` 안내가 뜨는지 확인.
4. **Lighthouse** > Categories 에서 PWA(또는 최신 Chrome 은 *Installable* 항목) 실행.
5. 휴대폰: Android Chrome 은 하단에 "홈 화면에 추가 / 설치" 배너가 뜹니다. iPhone Safari 는 배너에 "공유 → 홈 화면에 추가" 방법이 나옵니다. 닫으면 그 브라우저에서는 다시 뜨지 않습니다 (localStorage).

서비스 워커를 고쳤으면 `public/sw.js` 의 `VERSION` 을 올립니다. 새 버전이 켜질 때 예전 캐시를 지웁니다.

## 파일

```
web/
├─ app/
│  ├─ layout.tsx          메뉴바(Gnb)·바닥글(데이터 출처)·설치 안내·SW 등록 · 글꼴(Jua · 나눔스퀘어라운드 · Pretendard)
│  ├─ page.tsx            / 홈 (스토리 · 랭킹 · 신규 · 이번 주 · 사전예약)
│  ├─ map/page.tsx        /map 지도로 보기
│  ├─ list/page.tsx       /list 리스트로 보기
│  ├─ popup/[id]/page.tsx 상세 (generateMetadata: 제목·설명·OG 포스터)
│  ├─ this-week/page.tsx  이번 주
│  ├─ offline/page.tsx    오프라인 안내
│  ├─ not-found.tsx       404 안내
│  ├─ manifest.ts         웹 앱 매니페스트
│  └─ icon.png, apple-icon.png
├─ components/            Gnb · Footer · cards(포스터 카드) · HScroll · home/(랭킹·신규·이번 주) · browse/(필터·리스트·지도) · detail/Gallery …
├─ lib/
│  ├─ data.ts             데이터 읽기 (서버 전용, Supabase → GitHub 대체)
│  └─ popup.ts            날짜·상태·지역 등 순수 함수
├─ public/
│  ├─ sw.js               서비스 워커 (직접 작성)
│  ├─ icons/              PWA 아이콘 (scripts/make_icons.py 로 생성)
│  └─ logo_mint.png(앱 static/ 과 같은 파일), logo_mint_sm.webp(메뉴바용), default_poster.webp(앱 기본 포스터를 줄인 것)
└─ scripts/make_icons.py  ../static/logo_mint.png 에서 아이콘 만들기 (Pillow, scipy)
```

아이콘을 다시 만들려면 저장소 루트에서 `python web/scripts/make_icons.py`.

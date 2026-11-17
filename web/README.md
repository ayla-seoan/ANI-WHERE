# ANI:WHERE 공개 웹 (`web/`)

애니 팝업스토어·콜라보 카페를 **찾고 → 가기 전에 판단하는** 읽기 전용 웹입니다. Next.js(App Router) + PWA 라서 휴대폰 홈 화면에 앱처럼 설치됩니다.

## 왜 따로 만들었나

| | Streamlit 앱 (`app_cafemap.py`) | 공개 웹 (`web/`) |
|---|---|---|
| 하는 일 | 등록·수정·리뷰·검수 (쓰기) | 찾기·확인 (읽기만) |
| 사용자 | 운영자, 정보를 고치는 팬 | 현장에 가려는 모든 팬 |
| 속도 | 서버가 깨어나는 데 수십 초, 화면마다 파이썬 실행 | 미리 만든 HTML(ISR) 을 바로 보냄 |
| 휴대폰 | 브라우저 탭 | 홈 화면 설치, 한 번 본 화면은 오프라인에서도 열림 |

- 팝업은 **현장에 가는 것**이 목적이라, 사용자는 이동 중에 휴대폰으로 "지금 열려 있나, 언제까지인가, 어디인가, 특전이 뭔가"만 빨리 확인하면 됩니다. 이 순간에 Streamlit 의 느린 첫 로딩은 이탈 원인이 됩니다.
- 쓰기 기능을 빼면 로그인·스팸·권한 문제를 이 웹에서 신경 쓸 필요가 없습니다. 수정·리뷰는 상세 화면의 **"리뷰·수정은 ANI:WHERE 앱에서"** 링크로 Streamlit 앱(`?cafe=<id>`)에 넘깁니다.
- 데이터 출처는 화면 아래에 항상 표시합니다 (`데이터: Supabase` / `데이터: GitHub 공개 데이터`). "AI 산출 / 규칙 기반 대체" 를 늘 표시하는 프로젝트 원칙과 같은 이유입니다.

## 화면

| 주소 | 내용 |
|---|---|
| `/` | 검색(작품·캐릭터·매장·주소) + 상태 탭(진행 중 / 예정 / 전체) + 지역 칩. 진행 중이 먼저, 그다음 시작일 순. 조건에 맞는 게 없으면 빈 화면 대신 "조건을 줄여 보세요 / 앱에서 직접 등록" 안내 |
| `/popup/[id]` | 포스터, 작품·캐릭터·매장, 기간·상태, 주소 + 카카오맵, 특전·굿즈, 참고 링크(recal.kr 은 맨 뒤), 소개, 별점 평균, 앱 링크. 없는 id 는 404 안내 화면 |
| `/this-week` | 오늘~이번 주 일요일과 기간이 겹치는 팝업을 지역별로. "현장 가기 전" 화면 |
| `/offline` | 인터넷이 끊겼고 그 화면이 저장돼 있지 않을 때 서비스 워커가 보여 주는 화면 |

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
   - (선택) `SITE_URL` = 실제 도메인. 공유 미리보기(OG) 주소에 씁니다. 비우면 Vercel 의 production 주소를 씁니다.
4. Deploy. 이후 `main` 에 push 하면 자동 배포됩니다. 데이터는 배포 없이도 10분마다 새로 읽습니다.
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
│  ├─ layout.tsx          헤더·푸터(데이터 출처)·설치 안내·SW 등록
│  ├─ page.tsx            / 찾기
│  ├─ popup/[id]/page.tsx 상세 (generateMetadata: 제목·설명·OG 포스터)
│  ├─ this-week/page.tsx  이번 주
│  ├─ offline/page.tsx    오프라인 안내
│  ├─ not-found.tsx       404 안내
│  ├─ manifest.ts         웹 앱 매니페스트
│  └─ icon.png, apple-icon.png
├─ components/            PopupBrowser(검색·탭·칩, 클라이언트), PopupCard, InstallHint, SWRegister …
├─ lib/
│  ├─ data.ts             데이터 읽기 (서버 전용, Supabase → GitHub 대체)
│  └─ popup.ts            날짜·상태·지역 등 순수 함수
├─ public/
│  ├─ sw.js               서비스 워커 (직접 작성)
│  ├─ icons/              PWA 아이콘 (scripts/make_icons.py 로 생성)
│  └─ logo.png, poster-placeholder.svg
└─ scripts/make_icons.py  ../static/logo_mint.png 에서 아이콘 만들기 (Pillow, scipy)
```

아이콘을 다시 만들려면 저장소 루트에서 `python web/scripts/make_icons.py`.

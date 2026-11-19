# DB 설계 — Supabase (PostgreSQL + RLS)

ANI:WHERE 의 카페·리뷰·북마크를 Supabase 에 저장하는 방법과, 앱 규칙을 DB 에서 한 번 더 지키게 만든 장치를 정리한다.

- 스키마: [`supabase/migrations/001_init.sql`](supabase/migrations/001_init.sql)
- 앱 연결: `common/storage.py` (`STORAGE_MODE=supabase`)
- 옮기기: `scripts/migrate_to_supabase.py`
- 검증: `scripts/check_supabase_rls.py`

## 1. 왜 Supabase 인가

| 문제 | 로컬 JSON (`data/*.json`) | Google Sheets | Supabase |
|---|---|---|---|
| Streamlit Cloud 재배포 | 저장소의 처음 상태로 돌아감. 그 사이 쓴 리뷰·북마크가 사라짐 | 남음 | 남음 |
| 규칙을 어디서 지키나 | 앱 코드만 | 앱 코드만. 시트 권한이 있으면 누구나 칸을 고침 | 앱 코드 + **DB 정책(RLS)·제약** |
| 동시 수정 | 파일 덮어쓰기 경합 | 행 순서 경합 | `unique(entry_id, revision)` 으로 충돌 거부 |
| 추가 의존성 | 없음 | gspread, google-auth | 없음 (`requests` 로 REST 호출) |

무료 요금제로 충분하고, PostgREST(REST API)가 붙어 있어 SDK 없이 `requests` 만으로 읽고 쓸 수 있다.

## 2. 표 구조

세 표 모두 **한 행 = 한 기록(revision)** 이다. 같은 글은 `entry_id` 로 묶이고, `revision` 이 가장 큰 행이 현재 상태다.

```
cafes (팝업 카페)                reviews (리뷰·답글)              favorites (북마크)
─────────────────────           ─────────────────────           ─────────────────────
row_id      PK                  row_id      PK                  row_id      PK
entry_id    ┐ unique            entry_id    ┐ unique            entry_id    ┐ unique  ('<user>:<cafe_id>')
revision    ┘                   revision    ┘                   revision    ┘
status  active|deleted          status  active|deleted          status  active|deleted
updated_at  timestamptz         updated_at  timestamptz         updated_at  timestamptz
cafe_name, work, characters     cafe_id ──────────▶ cafes.entry_id   cafe_id ───▶ cafes.entry_id
address, lat, lng (double)      parent_id ──▶ reviews.entry_id  user (IP 해시)
start_date, end_date            kind, nickname, body
perks, goods, source, note      rating  '' 또는 '1'~'5'
images, tags, links, editor     images
intro, intro_src
```

- 칸 이름·순서는 `storage.HEADERS`, `review.HEADERS`, `favorite.HEADERS` 와 같다.
- 대부분 `text` 이고 빈 값은 `''` 다 (앱의 JSON 과 같은 모양). 숫자는 `revision`(int), `lat`·`lng`(double, 없으면 null)뿐이다. 앱으로 돌려줄 때 null 좌표는 `''`, 별점은 int 또는 `''` 로 바꾼다.
- `cafe_id`·`parent_id` 는 외래키를 걸지 않았다. 가리키는 대상이 `entry_id`(행이 여러 개)라 PK 가 아니고, 카페가 지워져도(`status=deleted` 행 추가) 리뷰 이력은 남아야 하기 때문이다.
- 인덱스: `entry_id`, `(updated_at, revision)` (앱이 이 순서로 읽는다), `reviews.cafe_id`.

## 3. append-only 를 DB 가 지킨다

앱 규칙은 "기존 행을 덮어쓰거나 지우지 않는다. 수정·삭제도 새 행을 쌓는다" 이다. 지금까지는 앱 코드만 이 약속을 지켰다. Supabase 에서는 DB 가 같이 막는다.

1. 세 표 모두 **RLS 를 켰다**. 정책이 없는 동작은 전부 거부된다.
2. `anon` 역할에는 **SELECT 정책과 INSERT 정책만** 만들었다. UPDATE·DELETE 정책은 없다.
3. 정책과 별개로 `revoke update, delete, truncate ... from anon, authenticated` 로 권한 자체도 뺐다. 그래서 시도하면 0행으로 조용히 끝나지 않고 `permission denied` 에러가 난다.

되돌리기(`revert`)·버전 고르기(`restore`)·삭제(`soft_delete`)는 모두 예전 내용을 **새 행으로 다시 쌓는** 방식이라 INSERT 만으로 그대로 동작한다.

## 4. 정책·제약 목록과 막는 것

| 이름 | 종류 | 표 | 막는 것 |
|---|---|---|---|
| `*_select` | RLS 정책 (`using true`) | 세 표 | 막지 않음. 지도·리뷰는 공개 정보 |
| `cafes_insert`, `favorites_insert` | RLS 정책 (`with check true`) | cafes, favorites | 막지 않음. 누구나 등록·북마크 |
| (UPDATE·DELETE 정책 없음 + revoke) | RLS + 권한 | 세 표 | 기존 행 덮어쓰기, 지우기, 표 비우기 |
| `reviews_insert` → `review_owner_ok()` | RLS 정책 `with check` | reviews | **남의 리뷰 수정·삭제.** 이미 있는 `entry_id` 에 새 revision 을 쌓을 때 닉네임 끝 `#네 글자` 가 그 글 revision 1 과 다르면 거부. 앱의 `review.can_delete` 와 같은 규칙 |
| `unique (entry_id, revision)` | 제약 | 세 표 | 두 사람이 동시에 같은 글을 고쳐 같은 revision 이 두 번 생기는 것 |
| `cafes_no_sensitive` | check + `has_sensitive()` | cafes (`cafe_name`, `note`, `intro`, `perks`, `goods`) | 주민번호·카드번호·휴대전화·유선전화·이메일 |
| `reviews_no_sensitive` | check + `has_sensitive()` | reviews (`body`) | 위와 같음 |
| `rating in ('', '1'..'5')` | check | reviews | 범위 밖 별점 |
| `status in ('active','deleted')`, `revision >= 1` | check | 세 표 | 이상한 상태값 |

- `has_sensitive()` 는 `common/guard.py` 의 `PATTERNS` 중 주민번호·카드번호·전화번호·유선전화·이메일을 PostgreSQL 정규식으로 옮긴 것이다. 앱은 저장 전에 이미 `guard.mask()` 로 가리므로 정상 사용에서는 걸리지 않는다. 앱을 거치지 않고 REST 로 직접 넣는 경우를 막는 두 번째 벽이다. 계좌번호 패턴은 앞뒤 조건(lookahead/lookbehind)이 PostgreSQL 정규식으로 옮겨지지 않아 DB 에서는 빼고 앱에서만 막는다.
- 앞뒤에 숫자·영문이 붙은 숫자열은 보지 않는다. `note` 끝 `| notion:<번호>`(16진수 32자) 가 전화번호로 잘못 걸리지 않게 하려는 것이다.
- `review_owner_ok()` 는 `security definer` 함수다. 정책 안에서 같은 표를 다시 읽으면 RLS 가 다시 걸리므로, 함수 권한으로 원글만 읽는다.

## 5. 앱의 동작 (common/storage.py)

- `STORAGE_MODE=supabase` 이면 `SUPABASE_URL`, `SUPABASE_KEY` 로 `{URL}/rest/v1/<표>` 에 연결한다.
- **시작할 때 실패**(URL·키 없음, 표 없음, 네트워크): sheets 모드와 똑같이 조용히 `local` 로 내려가고 이유는 `fallback_reason` 에 남는다. 앱은 멈추지 않는다.
- **읽기**: `updated_at, revision, row_id` 순으로 1000행씩 끊어 모두 읽는다 (PostgREST 기본 한도가 1000행). 한 화면을 그리는 동안 여러 번 읽지 않게 3초 캐시를 두고, 쓰면 캐시를 비운다.
- **쓰기 실패**: 로컬로 대신 쓰지 않고 `StorageWriteError` 를 낸다. 로컬 파일은 재배포 때 사라지고 DB 와 내용이 갈라지므로, 조용히 내려가면 "저장됐다" 고 믿은 기록을 잃는다. 실패를 바로 알리는 쪽이 안전하다고 판단했다. RLS 거부(남의 리뷰), 민감정보 거부, revision 충돌도 이 에러로 온다.
- 쓰기는 INSERT(`POST`) 하나뿐이다. PATCH·DELETE 를 보내는 코드는 없다.
- Notion 자동 가져오기(`scripts/notion_import.py`, GitHub Actions)는 지금처럼 `local` 모드로 `data/cafes.json` 을 고친다. 그 결과를 DB 에 반영하려면 `migrate_to_supabase.py` 를 한 번 더 돌리면 된다 (새 row_id 만 올라간다).

## 6. 옮기는 순서

1. **프로젝트 만들기**: https://supabase.com 에서 New project. 지역은 Northeast Asia (Seoul).
2. **표 만들기**: 대시보드 > SQL Editor > New query 에 `supabase/migrations/001_init.sql` 을 통째로 붙여넣고 Run. 여러 번 돌려도 된다.
3. **키 넣기**: Project Settings > API 에서 Project URL 과 `anon` `public` 키를 복사한다.
   - 로컬: `.env` 에
     ```
     STORAGE_MODE=supabase
     SUPABASE_URL=https://xxxx.supabase.co
     SUPABASE_KEY=<anon 키>
     ```
   - Streamlit Cloud: App settings > Secrets 에 **섹션 없이 맨 위 칸**으로 넣는다. `[supabase]` 같은 표 아래 넣으면 환경변수로 보이지 않아 앱이 local 로 내려간다.
     ```toml
     STORAGE_MODE = "supabase"
     SUPABASE_URL = "https://xxxx.supabase.co"
     SUPABASE_KEY = "<anon 키>"
     ```
4. **데이터 옮기기**:
   ```
   python scripts/migrate_to_supabase.py --dry-run   # 올릴 건수 확인
   python scripts/migrate_to_supabase.py             # 실제로 올리기 (중복 row_id 는 건너뜀)
   ```
5. **RLS 확인**:
   ```
   python scripts/check_supabase_rls.py
   ```
   UPDATE·DELETE·리뷰 사칭·전화번호·이메일·별점 9점이 모두 "거부 / 통과" 로 나와야 한다.
6. 앱을 껐다 켜서 지도·리뷰가 그대로 보이는지, 리뷰를 하나 쓰고 재배포한 뒤에도 남아 있는지 본다.

## 7. 한계와 선택한 것

- **사용자 인증이 아니다.** "내 글" 은 IP 해시(`#네 글자`)로 정한다. 키를 가진 사람이 REST 로 직접 남의 `#네 글자` 를 적어 넣으면 DB 는 구별하지 못한다. RLS 가 막는 것은 "다른 태그로 남의 글을 고치는 것" 까지다. 제대로 막으려면 Supabase Auth 로 로그인을 붙이고 정책을 `auth.uid()` 기준으로 바꿔야 한다.
- **키는 서버에만 있다.** Streamlit 은 서버에서 파이썬이 DB 를 부르므로 키가 브라우저로 내려가지 않는다. 그래도 anon 키는 "공개돼도 되는 키" 로 보고 설계했다. 새어 나가도 할 수 있는 것은 읽기와 규칙을 지키는 추가뿐이다.
- **anon 키 vs service_role 키.** service_role 키는 RLS 를 건너뛰어 UPDATE·DELETE 도 된다. 앱·`.env`·Secrets 에는 anon 키만 넣는다. `check_supabase_rls.py` 도 anon 키로 돌려야 의미가 있다.
- **스팸은 못 막는다.** INSERT 가 열려 있어 많이 쓰는 것 자체는 막지 않는다. 필요하면 Supabase 의 요청 제한이나 Edge Function 을 앞에 둔다.
- **읽기는 매번 전체.** 앱이 `all_rows()` 로 모든 이력을 읽어 파이썬에서 최신 revision 을 고른다. 지금 규모(수백 행)에는 문제없지만, 수만 행이 되면 "entry_id 별 최신 행" 뷰를 DB 에 두고 그것만 읽는 편이 낫다.
- **텍스트 날짜.** `start_date`·`end_date` 는 앱의 JSON 과 맞추려고 `text` 로 두었다. DB 에서 날짜 계산을 하려면 `::date` 로 바꿔 쓴다.

## 8. 공개 뷰와 Notion → Supabase 이관 (002)

`supabase/migrations/002_public_views.sql` 을 001 다음에 SQL Editor 에서 돌린다.

| 뷰 | 내용 | 누가 읽나 |
| --- | --- | --- |
| `popups_current` | 팝업별 최신 revision 중 `active` 만. `note`·`editor`·`source`(운영용)는 빼고 내보냄 | 공개 웹(`web/`, Next.js 서버에서만), MCP 서버 |
| `popup_ratings` | 팝업별 다녀온 후기 평균 별점과 개수. 리뷰 본문·닉네임은 빼고 내보냄 | 공개 웹 상세 |

- 두 뷰 모두 `security_invoker = true` 라서 뷰를 거쳐도 표의 RLS 가 그대로 걸린다. 뷰에는 SELECT 권한만 있다.
- 공개 웹은 anon 키를 **서버(Server Component)에서만** 쓴다 (`NEXT_PUBLIC_` 접두사 금지). 브라우저에 키가 내려가면 누구나 INSERT 정책으로 글을 쌓을 수 있기 때문이다.

### 이관 흐름

```
Notion 트래커 DB ──(매일 08:40 GitHub Actions + 예비 3번, scripts/notion_import.py)──▶ Supabase cafes (append-only INSERT)
                                                                         └─▶ data/cafes.json 거울 커밋
Supabase popups_current ──▶ Next.js 공개 웹 (ISR 10분) · MCP 서버 · Streamlit(STORAGE_MODE=supabase)
```

- 저장소 Secret 에 `SUPABASE_URL` · `SUPABASE_KEY` 를 넣으면 Actions 가 자동으로 `STORAGE_MODE=supabase` 로 돈다. 비우면 예전처럼 `data/cafes.json` 에만 쓴다.
- 처음 한 번은 `python scripts/migrate_to_supabase.py` 로 지금까지 쌓인 `data/*.json` 을 올린다 (6절).
- Supabase 로 쓴 뒤에도 `data/cafes.json` 을 거울로 남기는 이유: 공개 웹의 키 없는 대체 경로, Apps Script 브리핑, 검색 평가가 이 파일을 읽는다.

## 9. 프로젝트 만들 때 고를 것 (11/17)

| 칸 | 고를 값 | 이유 |
| --- | --- | --- |
| Project name | `ani-where` | |
| Database password | **Generate a password** → 비밀번호 관리자에 보관 | 앱은 이 비밀번호를 쓰지 않는다 (REST + anon 키). 나중에 DB 에 직접 붙을 때만 필요 |
| Region | **Northeast Asia (Seoul)** | 사용자·서버가 한국 |
| Enable Data API | **켬** | 앱·공개 웹·MCP 가 `/rest/v1` 로 읽고 쓴다. 끄면 아무것도 안 됨 |
| Automatically expose new tables | **끔** (Supabase 권장) | 권한을 `004_grants.sql` 로 필요한 만큼만 직접 준다 |
| Enable automatic RLS | **켬** | 마이그레이션에서도 켜지만, 새 표를 만들 때 잊어도 RLS 가 걸리게 한 겹 더 |

SQL Editor 에서 `001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011 → 012 → 013` 순서로 돌린다. (005 = 아이디·비밀번호 가입, `docs/login.md` · 006·007 = 관리자 표, 10절)

## 10. 관리자 표 (006, 11/18)

`supabase/migrations/006_admin.sql`. 세 표 모두 다른 표와 같은 append-only (anon 은 SELECT·INSERT 만, 처리·수정·삭제도 새 행).

| 표 | 한 행 | 주요 칸 | 쓰는 곳 |
| --- | --- | --- | --- |
| `del_requests` | 삭제 요청 1건의 한 상태 | `target_type`(review/cafe) · `target_id` · `reason`(≤300자) · `requester`(회원 번호) · `decision`(pending/approved/rejected) · `admin_reason` | 일반 회원 `삭제 요청` → 관리자 승인/거부 |
| `notices` | 알림 1건 | `target`('all' = 전체 공지, 아니면 회원 번호) · `kind`(공지/삭제 승인/삭제 거부) · `title`(≤60) · `body`(≤500) | 종 알림 · 내 캘린더 알림 내역 · 관리자 알림 관리 |
| `visits` | 회원 × 날짜 1행 (`entry_id` = `<회원 번호>:<날짜>`) | `member` · `day` | 관리자 이용 지표의 일별 접속 회원 |

- `reason`·`admin_reason`·`title`·`body` 는 `has_sensitive()` 검사로 전화번호·이메일 등을 막는다.
| `alert_rules` (007) | 자동 알림 규칙 1개의 한 설정 (`entry_id` = 규칙 번호) | `enabled`(0/1) · `days`(며칠 전부터) · `max_items`(최대 노출 개수). 끄기 = `status=deleted` 행 | 관리자 알림 관리 → 종 알림·알림 내역·삭제 결과 알림 |

- 계산(주별 칸반·간트·일별 수·자동 알림 규칙 `RULES`·`rule_settings`)은 `common/admin.py` 한곳. 007 을 돌리기 전에는 표가 없어 기본값(오픈·종료 3일 전, 북마크 8개, 주변 3개, 공지 14일·5개)으로 동작한다.

## 11. 회원 프로필 사진 (008, 11/18)

`members.avatar` 칸 하나를 더한다 (선택). 값은 카카오·네이버 프로필 사진 https 주소, 직접 올린 사진 파일 이름(`static/uploads`), `none`(기본 그림을 고름), `''`(아직 안 정함) 중 하나이고 DB 제약으로 그 밖의 값은 막는다.

- 간편 로그인으로 처음 가입하면 카카오·네이버가 준 사진 주소를 넣는다. 이미 가입한 회원이 사진을 정한 적 없으면(`''`) 다음 로그인 때 채운다.
- 마이페이지에서 사진을 올리거나 기본 그림으로 바꿀 수 있다 (새 행으로 쌓임).
- 리뷰에는 닉네임 끝 `#m네 글자`로 회원을 찾아 사진을 보여 준다. 화면에는 꼬리표 없이 닉네임만 보인다 (꼬리표는 '내 글' 확인용으로 저장에만 남김).
- **주의:** 앱 코드가 `avatar` 칸을 쓰므로 배포 전에 008 을 먼저 돌린다. 안 돌리면 Supabase 모드에서 가입·닉네임 변경이 실패한다.

## 12. 탈퇴 회원 개인정보 파기 (009, 11/18)

저장소는 append-only 라 탈퇴(`status=deleted` 행)해도 예전 행에 닉네임·사진이 남는다. 개인정보 보호법의 파기 의무 때문에 **이 함수만 예외로 예전 행을 고친다.**

| 함수 | 누가 | 하는 일 |
| --- | --- | --- |
| `purge_withdrawn(회원 번호)` | 앱 (탈퇴 직후, anon 실행 가능) | 그 회원의 마지막 기록이 탈퇴일 때만: `members` 닉네임·사진 빈 값, `reviews` 작성자 '탈퇴한 회원#m…', `del_requests` 요청자 닉네임 비움, `visits`·받은 `notices`·`member_credentials` 삭제 |
| `purge_expired()` | 매일 04:00 KST pg_cron (anon 실행 불가) | 탈퇴 회원 전체 다시 정리 + 1년 지난 접속 기록 삭제 |

- 탈퇴하지 않은 회원은 `purge_withdrawn` 으로 지울 수 없다 (마지막 기록이 탈퇴인지 먼저 본다).
- pg_cron 을 켤 수 없으면 SQL Editor 에서 `select public.purge_expired();` 를 직접 돌린다.
- 로컬(개발) 모드는 `auth.purge_withdrawn` 이 `data/*.json` 을 같은 규칙으로 고친다.

## 13. 외부 API 호출 수 (010, 11/18)

`api_usage` 표 — 블로그 검색(NAVER API HUB)을 **한 달 30,000번**까지만 부르려고 센다 (`common/blog.py`).

- 한 줄 = 25번 호출 묶음 (`api='blog'`, `month='2026-11'`, `calls=25`). 이번 달 합계 = `calls` 의 합 + 아직 안 적은 수.
- 합계가 30,000 이상이면 부르지 않는다. 표를 못 읽으면(010 전·연결 실패) 안전하게 부르지 않는다.
- append-only (anon 은 SELECT·INSERT 만).

## 14. 사진 저장소 (011, 11/19)

공개 웹(Vercel)에는 파일을 둘 곳이 없어서, 웹에서 올리는 프로필 · 리뷰 · 포스터 사진은 **Supabase Storage 공개 버킷 `uploads`** 에 둔다.

- 서버(Next.js 서버 액션)가 **anon 키로만** 올린다. 올리기 전에 위치·기기 정보(EXIF)를 지우고 픽셀만 다시 저장한다 (`web/lib/server/upload.ts`, `common/images.py` 와 같은 규칙. 프로필은 가운데 256px webp).
- 이름은 무작위 12자 + 확장자. 정책은 **새 파일 넣기(insert) 하나뿐** — 이 버킷 · 이름 모양만. 종류(png·jpg·webp·gif)와 크기(20MB)는 버킷 설정으로 막는다. 고치기·지우기 정책은 없어서 anon 으로는 남의 사진을 바꾸거나 지울 수 없다.
- 저장 칸(`members.avatar` · `reviews.images` · `cafes.images`)에는 공개 주소 `https://<프로젝트>.supabase.co/storage/v1/object/public/uploads/<이름>` 을 그대로 넣는다. Streamlit 은 `common/images.py` 의 `Remote` 로 이 주소를 보여 준다.
- 한계: 리뷰를 지워도 Storage 의 사진 파일은 남는다 (지우기 정책을 열면 아무나 지울 수 있어서). 주소는 무작위라 추측하기 어렵지만, 꼭 지워야 하면 관리자가 Supabase 대시보드 Storage 에서 지운다.
  → 11/19 (012) 부터는 **어느 기록도 쓰지 않는 · 하루 지난** 파일만 anon 이 보고 지울 수 있고(`upload_in_use`), 매일 가져오기 작업이 `scripts/storage_sweep.py` 로 지운다. 쓰고 있는 사진은 여전히 anon 으로 지울 수 없다.

## 15. 내린 팝업 주간 정리 (012, 11/19)

append-only 의 두 번째 예외 (첫 번째는 009 탈퇴 회원 파기). 사용자 결정 11/19.

- **언제:** 매주 월요일 00:10 KST, Supabase pg_cron `aniwhere-purge-popups` (`10 15 * * 0` UTC) 가 `purge_ended_popups()` 를 부른다. anon 은 부를 수 없다.
- **무엇을:** '이번 주 월요일' 보다 앞에 내려간 팝업 — 종료일이 지난주 일요일 이전이거나, 마지막 기록이 `deleted`(삭제 요청 승인 등)이고 그 기록이 이번 주 월요일 전. 그 팝업의 **모든 revision** + 리뷰(답글 포함) · 북마크 · 삭제 요청 기록을 지운다.
- **다시 들어오지 않게:** 기간이 남았는데 내린 팝업은 `purged_popups` 에 Notion 번호만 남기고, `notion_sync.import_rows` 가 그 번호를 건너뛴다. 기간이 끝나 지운 팝업은 남기지 않는다 (Notion 에서 기간이 늘면 다시 들어오는 게 맞아서).
- **사진 파일:** SQL 로는 Storage 파일을 지울 수 없다 (Supabase 문서). 14절의 '안 쓰는 파일' 정책 + `scripts/storage_sweep.py`.
- **영향:** 되돌릴 수 없다. `/stats` 완결률의 예전 값(10/30 이전 60건 70.0%)은 남은 기록으로 다시 계산돼 바뀐다 — 발표 숫자는 `docs/metrics-log.md` 에 남긴 값을 쓴다. 관리자 간트 · 내 캘린더 지난 달 · 다녀온 팝업에서도 빠진다.
- **시험 (11/19):** 운영 DB 에서 함수를 돌리고 일부러 오류를 내 되돌림 → 그 시점 기준 팝업 59곳(기록 169줄) · 리뷰 13 · 북마크 42 · 다시 가져오기 막음 1. 실제로 지워진 것 없음 확인.
- 손으로 돌리기: SQL Editor 에서 `select public.purge_ended_popups();`

## 16. 블로그 후기 저장 (013, 11/19)

예전엔 상세를 열 때마다(서버마다 하루 한 번) 네이버 블로그 검색을 다시 불러 하루 한도(429)를 다 썼다. 사용자 제안: "불러온 거 저장해 놓고 보이게 하고 추가된 것만 새로 불러오면 되잖아".

- `blog_posts`: 찾은 글 (`cafe_id · link · title · descr · blogger · day · thumb`, entry_id = `<팝업 id>:<링크 sha1 앞 12자>`). 화면(두 사이트)은 여기서 바로 읽고, '블로그 후기 (N)' 의 N 도 저장된 글 수라 네이버를 부르지 않는다.
- `blog_checks`: 팝업마다 네이버에 물어본 날 (`<팝업 id>:<YYYY-MM-DD>`). 오늘 표시가 있으면 다시 묻지 않는다 → 팝업마다 하루 최대 1번.
- 처음엔 정확도순(sort=sim)으로, 그다음부터는 최신순(sort=date)으로 물어 **아직 없는 링크만** 더한다. 대표 사진(og:image)도 새 글만 한 번 받아 저장한다.
- 실패(한도 · 연결 실패)여도 저장해 둔 글은 그대로 보여 준다. 코드: `common/blog.py` `refresh` · `web/lib/server/blog.ts` `refresh`.
- append-only, anon 은 읽기 · 쌓기만. 주간 정리(012 → 013 에서 다시 만듦)가 내린 팝업의 글 · 확인 기록도 함께 지운다.

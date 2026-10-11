# CROWN BOARD — 왕관과 금화 인게임 대시보드

최종 업데이트: 2026-10-11

GA4 → BigQuery → GitHub Actions(Python) → `docs/data/*.json` → GitHub Pages + 바닐라 JS.
빌드 없음, 프레임워크 없음, 런타임 의존성은 `google-cloud-bigquery` 하나.

설계 근거는 게임 레포의 [`docs/INTEGRATION_SPEC.md` §12](../crown-and-coin/docs/INTEGRATION_SPEC.md) 이고,
이 리포는 `secondact-dashboard` 를 **왕관과 금화 좌표로 옮긴 것**이다.

---

## 지금 상태 — 파이프라인은 뚫렸고, 데이터가 아직 없다 (출시 전)

2026-10-11 실제 데이터셋에 붙여 **양쪽 수집기 완주 확인**. 다만 `events_20261010`
한 장 11행(릴리스 빌드 시험 흔적)뿐이라 지표는 전부 0 이다. **비어 있는 게 정상이다.**

| | 필요한 것 | 상태 |
|---|---|---|
| ① | 서비스계정 + 키 | ✅ 완료 (Data Viewer + Job User) |
| ② | 로컬 수집 검증 | ✅ `ingame.py`·`realtime.py` 완주 |
| ③ | GitHub Secret **`GCP_SA_KEY`** 등록 | ⬜ 리포를 올린 뒤 `gh secret set GCP_SA_KEY < ~/dev/keystore/crowncoin-bq.json` |
| ④ | 앱이 Play 에 올라가 **실제 유저 이벤트**가 쌓인다 | ⬜ 🧑 |

②가 **스위치 역할을 겸한다** — 시크릿이 없으면 모든 워크플로가 `if: env.GCP_SA_KEY != ''`
에서 걸려 **초록색으로 아무것도 안 하고** 끝난다. 그래서 스케줄을 미리 켜 둬도 안전하고,
출시일에 시크릿만 넣으면 그때부터 자동으로 돈다. 따로 켤 일이 없다.

서비스계정 권한은 **BigQuery Data Viewer + Job User 둘뿐**이다. 그 이상 주지 않는다.

## 좌표

| | 값 |
|---|---|
| GCP 프로젝트 | `crownandcoin` |
| BigQuery 데이터셋 | `analytics_558372672` |
| 리전 | `asia-northeast3` ★클라이언트에 **명시**해야 한다. 안 맞으면 잡이 실패한다 |
| 서비스계정 키(로컬) | `~/dev/keystore/crowncoin-bq.json` ✅ 발급·검증 완료 (`crowncoin-bq@crownandcoin.iam.gserviceaccount.com`) |

## 수집기

| 스크립트 | 테이블 | 출력 | 주기 |
|---|---|---|---|
| `tools/ingame.py` | 일별만 | `docs/data/ingame.json` | 하루 2회 (18:00 / 22:00 KST) |
| `tools/realtime.py` | 스트리밍만 | `docs/data/realtime.json` | 매시 4회 (:08 :23 :38 :53) |
| `tools/probe.py` | — | stdout | 수동 진단 |

`ingame` 을 **하루 2회** 돌리는 건 GA4 일별 테이블의 landing 시각이 날마다 흔들리기 때문이다.
값이 같으면 커밋하지 않으므로 두 번 돌아도 부담이 없다.
cron 분을 **0이나 5로 두지 않는다** — GitHub 스케줄은 best-effort라 정시 근처가 잘 드롭된다.

## 원작과 달라진 곳 (옮기면서 바꾼 것)

| | 인생 2막 | 왕관과 금화 | 왜 |
|---|---|---|---|
| `CITY_BUILD` | `1.0 (v965)` | **빈 값**(= 전 빌드) | 원작은 2부를 나중에 얹어 '자격은 됐는데 빌드를 못 받은 사람'을 갈라야 했다. 여기는 **2부가 v1부터** 들어 있어 그 구분이 없다 |
| `DIAG_START` | `20260923` | `20260101`(= 전 구간) | 원작은 진단 이벤트를 중간에 넣어 이전 구간을 잘라야 했다. 포크는 처음부터 다 들어 있다 |
| 뷰 | 매출·인게임·실시간·광고·전체가입자 | **인게임·실시간 둘뿐** | 아래 |

### 일부러 안 넣은 것

- **매출·마케팅비 뷰** — 아직 매출도 광고비도 없다. 출시 후 `secondact-dashboard` 의
  `app.js`·`sync.py`·`iap.py` 를 가져온다.
- **전체 가입자(`users.py`)·어뷰징(`anomaly.py`)** — ★**전 이력 무윈도우 스캔**이라
  앱 나이에 비례해 스캔량이 **영원히 증가한다**. 레퍼런스 실측 anomaly 8.2GB/회 ·
  users 1.66GB/회 → 월 ~250GB(무료 1TB의 1/4). 사양(§12.3)이 "그대로 복사하면 언젠가
  터진다 — 출시 전에 재검토할 것"이라고 못박았다. **데이터가 쌓인 뒤 윈도우를 다시 설계해
  넣는다.** 지금 복사해 두면 '나중에 고치자'가 영영 안 온다.

## 로컬 실행

```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/dev/keystore/crowncoin-bq.json
python3 -m pip install --quiet google-cloud-bigquery
python3 tools/ingame.py        # → docs/data/ingame.json
python3 tools/realtime.py      # → docs/data/realtime.json
python3 -m http.server -d docs 8080
```

## 검사

```bash
python3 -m http.server -d docs 8099 &
node tools/pagetest.js      # 모든 탭을 **눌러 보고** JS 예외·빈 뷰를 잡는다
```

Pages 가 200 을 줘도 화면이 그려지는 건 아니다. 스크립트 하나가 터지면 흰 화면이 뜨는데
배포는 "성공"으로 남는다. 실제로 이 검사가 첫 구축 때 버그를 잡았다 — 매출 뷰를 빼면서
`userrow.js` 도 같이 뺐는데 `realtime.js` 가 `window.UserRow` 를 쓰고 있어 **실시간 탭이
통째로 죽어** 있었다. 파일 목록만 봐서는 안 보이고 탭을 눌러 봐야 보인다.

## 운영 규약 (사양 §12.5)

- 모든 산출물에 `updated` + `scan_mb` 를 싣고 화면에 표시한다.
  **자동화는 조용히 실패하므로 화면이 그걸 말해야 한다** — 갱신 시각이 멈춰 있으면
  숫자를 의심하기 전에 수집을 의심한다.
- 캐시 무효화 3층: 코드 자산 `?v=<md5>` · `fetch(cache:'no-store')` · CDN 우회 `?t=<분>`.
- 공개 리포에 원시 `user_pseudo_id` 를 내보내지 않는다(MD5 앞 6자로 가명화).

## 함정

- **스캔 비용을 자기보고하게 한다.** 각 수집기가 `total_bytes_billed` 를 누적해 `scan_mb` 로 싣는다.
  ★`ingame.py` 는 원작에도 이게 **빠져 있었다**(realtime/users/anomaly 만 있었다). 매일 도는
  주 수집기라 제일 필요한 자리여서 여기 넣었다. 넣자마자 바로 알려 준 사실 —
  **데이터 11행인데 스캔 170MB** 다. BigQuery 가 쿼리당 **10MB 를 최소 과금**하는데 쿼리가
  17개라 그렇다. 즉 **데이터가 0이어도 하루 2회 × 170MB = 340MB** 가 바닥값으로 나간다
  (월 ~10GB, 무료 1TB의 1%). 쿼리 개수를 늘릴 땐 이 바닥값도 같이 는다는 걸 기억할 것.
- `events_*` 와일드카드는 **`events_intraday_*` 도 같이 잡는다.** 날짜를 비교하는 자리에서
  `_TABLE_SUFFIX` 를 그냥 쓰면 `intraday_20261010` 이라 비교가 전부 어긋나고, 막지 않으면
  그 날짜가 **두 번** 세어진다.
- 로봇 제외는 `IFNULL(geo.country,'') != ''` — Play 사전 출시 보고서 기기는 국가가 빈다.
  BigQuery 에서 `NULL != ''` 은 TRUE 가 아니므로 `IFNULL` 로 감싸야 둘 다 걸린다.
- 유저 속성은 `UNNEST(user_properties)` — `event_params` 가 **아니다**.

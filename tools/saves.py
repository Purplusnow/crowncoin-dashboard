#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""클라우드 세이브(Firestore `saves/{uid}`) 조회 — 유저별 보유 다이아·현금·결제 상태.

왜 필요한가: 결제 문의가 오면 Play 주문(orderId)과 세이브를 이어야 하는데,
GA4 `set_user_id` 가 설정돼 있지 않아 **user_pseudo_id ↔ Firebase uid 고리가 없다.**
세이브 문서 필드는 `blob`(세이브 JSON 전문) · `saved_at`(unix) · `v`(save_version) 뿐이라
orderId 도 이메일도 없다. 그래서 **`saved_at` 이 결제 시각과 거의 같다**는 성질로 좁힌다
(`SaveSystem.save_game(true)` 가 결제 직후 스로틀을 무시하고 즉시 업로드한다).

⚠ 이건 유저 개인 데이터다. 필요한 만큼만 뽑고, 출력을 레포에 커밋하지 않는다.

사용:
  export GOOGLE_APPLICATION_CREDENTIALS=~/dev/keystore/crowncoin-bq.json
  python3 tools/saves.py                      # 전체 — 다이아 많은 순
  python3 tools/saves.py --sort saved          # 최근 저장 순
  python3 tools/saves.py --near "2026-10-27 23:24:25" --window 120
                                               # 그 시각 ±120초 저장분만(결제 대조용)
  python3 tools/saves.py --uid 6b055f71        # uid 접두어로 한 명
  python3 tools/saves.py --csv out.csv         # 표로 저장

필요 권한: 서비스계정에 Firestore 읽기(roles/datastore.viewer).
없으면 403 이 뜨므로 Firebase Console → IAM 에서 부여한다.
"""
import argparse, csv as csvmod, datetime, json, os, sys, urllib.error, urllib.request

PROJECT = os.environ.get("FB_PROJECT", "crownandcoin")
COLLECTION = "saves"
SCOPES = ["https://www.googleapis.com/auth/datastore"]


def token() -> str:
    from google.oauth2 import service_account
    import google.auth.transport.requests
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not path:
        sys.exit("GOOGLE_APPLICATION_CREDENTIALS 를 설정하세요")
    cr = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    cr.refresh(google.auth.transport.requests.Request())
    return cr.token


def fetch_all(tok: str) -> list:
    """컬렉션 전량 — 페이지네이션. 문서 수가 많아지면 --near 로 좁혀 쓸 것."""
    base = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
            f"/databases/(default)/documents/{COLLECTION}")
    out, page = [], ""
    while True:
        url = f"{base}?pageSize=300" + (f"&pageToken={page}" if page else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        try:
            d = json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:400]
            sys.exit(f"⛔ Firestore {e.code}: {body}\n"
                     f"   403 이면 서비스계정에 roles/datastore.viewer 가 없다.")
        out += d.get("documents", [])
        page = d.get("nextPageToken", "")
        if not page:
            return out


def row_of(doc: dict) -> dict:
    f = doc.get("fields", {})
    uid = doc["name"].rsplit("/", 1)[-1]
    saved = float(f.get("saved_at", {}).get("doubleValue", 0) or 0)
    blob = f.get("blob", {}).get("stringValue", "")
    try:
        b = json.loads(blob) if blob else {}
    except Exception:
        b = {}
    paid = list(b.get("starter_tiers_bought", []) or []) + list(b.get("founder_tiers_bought", []) or [])
    return {
        "uid": uid,
        "saved_at": saved,
        "saved_kst": datetime.datetime.fromtimestamp(saved).strftime("%Y-%m-%d %H:%M:%S") if saved else "",
        "gems": int(b.get("gems", 0) or 0),
        "cash": float(b.get("cash", 0) or 0),
        "class": int(b.get("class_level", 0) or 0),
        "rebirth": int(b.get("rebirth_count", 0) or 0),
        "paid_tiers": ",".join(paid),
        "v": int(f.get("v", {}).get("integerValue", 0) or 0),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sort", choices=["gems", "saved", "cash"], default="gems")
    ap.add_argument("--near", help='기준 시각 "YYYY-MM-DD HH:MM:SS" (로컬)')
    ap.add_argument("--window", type=int, default=120, help="--near 의 ±초 (기본 120)")
    ap.add_argument("--uid", help="uid 접두어")
    ap.add_argument("--paid-only", action="store_true", help="결제 이력 있는 유저만")
    ap.add_argument("--csv")
    a = ap.parse_args()

    rows = [row_of(d) for d in fetch_all(token())]
    total = len(rows)

    if a.uid:
        rows = [r for r in rows if r["uid"].startswith(a.uid)]
    if a.near:
        t0 = datetime.datetime.strptime(a.near, "%Y-%m-%d %H:%M:%S").timestamp()
        rows = [r for r in rows if abs(r["saved_at"] - t0) <= a.window]
    if a.paid_only:
        rows = [r for r in rows if r["paid_tiers"]]

    key = {"gems": lambda r: r["gems"], "saved": lambda r: r["saved_at"],
           "cash": lambda r: r["cash"]}[a.sort]
    rows.sort(key=key, reverse=True)

    print(f"세이브 문서 {total}개 · 출력 {len(rows)}개 · 정렬 {a.sort}\n")
    print(f"{'uid':34} {'💎':>8} {'현금':>16} {'신분':>4} {'환생':>4} {'저장(로컬)':19}  결제")
    for r in rows:
        print(f"{r['uid']:34} {r['gems']:>8,} {r['cash']:>16,.0f} {r['class']:>4} "
              f"{r['rebirth']:>4} {r['saved_kst']:19}  {r['paid_tiers']}")
    if rows:
        print(f"\n합계 💎{sum(r['gems'] for r in rows):,} · 결제 이력 보유 {sum(1 for r in rows if r['paid_tiers'])}명")
    if a.csv:
        with open(a.csv, "w", encoding="utf-8", newline="") as f:
            w = csvmod.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["uid"])
            w.writeheader()
            w.writerows(rows)
        print(f"→ {a.csv}")


if __name__ == "__main__":
    main()

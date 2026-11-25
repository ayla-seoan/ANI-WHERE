"""후기 도장 랭크 (common/stamp.py) — 웹 web/lib/stamp.ts 와 같은 규칙."""
from common import stamp


def _r(nick, cafe, kind="다녀온 후기", parent="", status="active"):
    return {"nickname": nick, "cafe_id": cafe, "kind": kind, "parent_id": parent, "status": status}


def test_counts_one_per_popup_and_only_visited():
    rows = [_r("토끼#m1a2b", "a"), _r("토끼#m1a2b", "a"),          # 같은 팝업 두 번 → 1개
            _r("토끼#m1a2b", "b"), _r("토끼#m1a2b", "c", kind="기대평"),  # 기대평 제외
            _r("토끼#m1a2b", "d", parent="x"),                      # 답글 제외
            _r("토끼#m1a2b", "e", status="deleted"),                # 지운 후기 제외
            _r("손님#a3f9", "a"),                                   # 손님(IP 꼬리표) 제외
            _r("탈퇴한 회원#m9zzz", "a")]                            # 탈퇴 제외
    assert stamp.counts(rows) == {"m1a2b": 2}


def test_tier_thresholds():
    assert stamp.tier_of(0) is None
    assert [stamp.tier_of(n).lv for n in (1, 2, 3, 9, 10, 24, 25, 49, 50, 99)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    assert stamp.next_tier(0)[1] == 1 and stamp.next_tier(3) == (stamp.TIERS[2], 7) and stamp.next_tier(50) is None
    assert stamp.lv_of("토끼#m1a2b", {"m1a2b": 3}) == 2 and stamp.lv_of("익명", {}) == 0

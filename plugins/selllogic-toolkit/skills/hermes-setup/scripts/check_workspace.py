"""헤르메스 봇 토큰이 '붙이려던 워크스페이스'에 설치됐는지 확인한다.

슬랙 앱 생성 화면은 브라우저에 로그인된 워크스페이스를 기본으로 고른다.
스터디 워크스페이스에 로그인한 채로 만들면 고객 슬랙이 아니라 스터디에 설치된다.
게이트웨이를 켜기 전에 이 스크립트가 통과해야 한다.

사용:
  python check_workspace.py --profile <프로필명> --expect <고객 슬랙 주소 또는 팀 ID>
  예) python check_workspace.py --profile acme --expect acme-corp.slack.com
종료코드: 0 = 일치, 1 = 불일치·스터디 워크스페이스·토큰 없음
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# 스터디 워크스페이스에는 개인·고객 봇을 설치하지 않는다
BLOCKED_TEAMS = {"T075CA1L0KT": "Claude Code Study"}


def hermes_homes():
    if os.environ.get("HERMES_HOME"):
        yield Path(os.environ["HERMES_HOME"])
    if os.environ.get("LOCALAPPDATA"):
        yield Path(os.environ["LOCALAPPDATA"]) / "hermes"
    yield Path.home() / ".hermes"


def find_env(profile):
    for home in hermes_homes():
        env = home / ".env" if profile == "default" else home / "profiles" / profile / ".env"
        if env.exists():
            return env
    return None


def read_token(env):
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("SLACK_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def auth_test(token):
    req = urllib.request.Request("https://slack.com/api/auth.test", data=b"",
                                 headers={"Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(req, timeout=15))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--expect", required=True, help="붙이려던 워크스페이스 주소(xxx.slack.com) 또는 팀 ID(T...)")
    a = ap.parse_args()

    env = find_env(a.profile)
    if not env:
        print(f"[중단] 프로필 '{a.profile}' 의 .env 를 찾지 못했습니다.")
        return 1
    token = read_token(env)
    if not token:
        print(f"[중단] {env} 에 SLACK_BOT_TOKEN 이 없습니다.")
        return 1

    r = auth_test(token)
    if not r.get("ok"):
        print(f"[중단] 토큰 확인 실패: {r.get('error')}")
        return 1

    team_id, team, url = r["team_id"], r.get("team", ""), r.get("url", "")
    print(f"이 봇이 설치된 워크스페이스: {team} ({team_id}) {url}")

    if team_id in BLOCKED_TEAMS:
        print(f"[중단] {BLOCKED_TEAMS[team_id]} 워크스페이스에 설치됐습니다. 여기는 봇을 붙이는 곳이 아닙니다.")
        print("  → api.slack.com/apps 에서 이 앱의 Install App 을 취소(Uninstall)하고,")
        print("    붙일 워크스페이스에 로그인한 브라우저에서 앱을 새로 만드세요.")
        return 1

    want = a.expect.strip().lower().removeprefix("https://").rstrip("/")
    if want not in (team_id.lower(), url.lower().removeprefix("https://").rstrip("/")):
        print(f"[중단] 붙이려던 곳은 '{a.expect}' 인데 설치된 곳은 '{team}' 입니다.")
        return 1

    print("[통과] 붙이려던 워크스페이스가 맞습니다. 게이트웨이를 켜도 됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

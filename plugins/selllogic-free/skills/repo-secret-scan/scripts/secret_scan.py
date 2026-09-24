# -*- coding: utf-8 -*-
"""저장소를 남에게 주거나 공개하기 전에 비밀키·고객명·내부 경로를 찾는다.

받는 사람은 저장소 전체(커밋 이력 포함)를 받는다. 그래서 지금 파일, 커밋 이력에 추가됐던 줄,
커밋 작성자·메시지를 모두 본다. 찾은 값은 앞 4글자만 남기고 가린다(보고서가 또 하나의 유출 경로가 되지 않게).

  python secret_scan.py <저장소 경로> [<경로> ...]
  python secret_scan.py . --config ~/.secret-scan.json
  python secret_scan.py . --no-history          지금 파일만
  python secret_scan.py --init                  설정 예시를 ~/.secret-scan.json 으로 만든다
  python secret_scan.py --print-gitignore       .gitignore 에 넣을 기본 블록을 출력한다

종료 코드: 0 = 0건, 1 = 찾은 것이 있음, 2 = 실행 오류. 공개 직전 게이트로 쓸 수 있다.
설정 파일에는 고객사명 같은 민감 목록이 들어가므로 검사할 저장소 밖(홈 폴더)에 둔다.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # ok-silent: 오래된 파이썬은 reconfigure 가 없고 기본 인코딩으로 출력해도 된다
        pass

# 모양만으로 알아볼 수 있는 비밀값. 누구에게나 같다.
SECRET = {
    "OpenAI류 키": r"(?<![A-Za-z0-9_-])sk-(?!ant-)[A-Za-z0-9_\-]{20,}",
    "Anthropic 키": r"(?<![A-Za-z0-9_-])sk-ant-[A-Za-z0-9_\-]{20,}",
    "슬랙 토큰": r"xox[abposrce]-[A-Za-z0-9\-]{10,}",
    "슬랙 앱 토큰": r"xapp-\d-[A-Za-z0-9\-]{10,}",
    "구글 API 키": r"AIza[0-9A-Za-z_\-]{30,}",
    "구글 OAuth 시크릿": r"GOCSPX-[A-Za-z0-9_\-]{10,}",
    "깃허브 토큰": r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}",
    "메타 토큰": r"EAA[A-Za-z0-9]{40,}",
    "AWS 키": r"AKIA[0-9A-Z]{16}",
    "개인키": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "refresh_token 값": r"\"refresh_token\"\s*:\s*\"[^\"]{10,}\"",
    "비밀번호 대입": r"(?i)(password|passwd|pwd|secret|api_key|apikey)\s*[=:]\s*[\"'][^\"'\s]{6,}[\"']",
    "웹훅 주소": r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+|discord(?:app)?\.com/api/webhooks/\S+",
}
# 한국 개인정보 모양. 설정의 allow 로 예시값을 빼 줄 수 있다.
PERSONAL = {
    "휴대폰 번호": r"(?<!\d)01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)",
    "주민등록번호": r"(?<!\d)\d{6}-[1-4]\d{6}(?!\d)",
}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".mp3", ".wav", ".zip",
            ".pdf", ".ico", ".ttf", ".otf", ".woff", ".woff2", ".exe", ".dll", ".pyc"}
MAX_BYTES = 2_000_000

# 받는 사람이 비밀 파일을 실수로 커밋하지 않게 .gitignore 에 두는 기본 블록
GITIGNORE_BLOCK = """# --- 비밀값·로컬 데이터 (secret_scan 기본 블록) ---
.env
.env.*
!.env.example
*.db
*.sqlite
*.sqlite3
*.pem
*.key
token*.json
*_token.json
credentials*.json
client_secret*.json
service_account*.json
"""
# 위 블록이 실제로 먹는지 확인할 표본 파일명
IGNORE_SAMPLES = [".env", ".env.local", "data.db", "cache.sqlite", "token.json", "credentials.json",
                  "client_secret.json", "service_account.json", "server.pem"]

EXAMPLE_CONFIG = {
    "_설명": "names 의 값은 정규식이다. 여러 개는 | 로 잇는다. 이 파일은 검사할 저장소 안에 두지 않는다.",
    "names": {
        "고객사명": "고객사A|고객사B|client-a",
        "내 실명·계정": "홍길동|myid123|me@example.com",
        "내부 경로": "C:[\\\\/]+Users[\\\\/]+myname|/Users/myname|/home/myname",
        "사업자번호": "123-45-67890",
    },
    "allow": ["010-0000-0000", "example\\.com"],
    "skip_paths": ["tests/fixtures/*"],
}


def mask(s):
    # 앞 4글자까지만 보인다. 짧은 값(고객사명 등)은 절반 이상을 가린다
    keep = min(4, len(s) // 2)
    return s[:keep] + "*" * min(8, max(1, len(s) - keep))


class Scanner:
    def __init__(self, cfg):
        self.patterns = []
        for group in (SECRET, PERSONAL, cfg.get("names", {})):
            for label, pat in group.items():
                if not pat:
                    continue
                self.patterns.append((label, re.compile(pat)))
        self.allow = [re.compile(a) for a in cfg.get("allow", [])]
        self.skip_paths = cfg.get("skip_paths", [])

    def skip(self, path):
        p = path.replace("\\", "/")
        return Path(p).suffix.lower() in SKIP_EXT or any(fnmatch.fnmatch(p, g) for g in self.skip_paths)

    def find(self, text):
        for label, rx in self.patterns:
            for m in rx.finditer(text):
                v = m.group(0)
                if any(a.search(v) for a in self.allow):
                    continue
                yield label, v

    def guard(self, line):
        """최종 출력 직전에 한 번 더 가린다. 파일명·커밋 메시지에 섞여 들어온 값도 여기서 걸린다."""
        for _, v in list(self.find(line)):
            line = line.replace(v, mask(v))
        return line


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} 실패: {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout.decode("utf-8", "replace")


def read_text(p):
    try:
        if p.stat().st_size > MAX_BYTES:
            return None
        return p.read_text("utf-8", "replace")
    except OSError as e:
        print(f"   [경고] 읽기 실패 {p.name}: {e.__class__.__name__}")
        return None


def scan_repo(repo, sc, history=True):
    head, hist, meta = [], [], []
    is_git = (repo / ".git").exists()
    files = git(repo, "ls-files").splitlines() if is_git else [
        str(p.relative_to(repo)) for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]
    for f in files:
        for label, v in sc.find(f):
            head.append((label, f + " (파일명)", v))
        if sc.skip(f):
            continue
        text = read_text(repo / f)
        if text is None:
            continue
        for label, v in sc.find(text):
            head.append((label, f, v))
    if is_git and history:
        cur, commit = "?", "?"
        log = git(repo, "log", "-p", "--all", "--no-color", "--no-ext-diff", "--no-textconv", "--format=@@COMMIT %h")
        for line in log.splitlines():
            if line.startswith("@@COMMIT"):
                commit = line.split()[1]
            elif line.startswith("+++ b/"):
                cur = f"{commit}:{line[6:]}"
            elif line.startswith("+") and not line.startswith("+++") and not sc.skip(cur.split(":", 1)[-1]):
                for label, v in sc.find(line):
                    hist.append((label, cur, v))
        # 작성자 이름·메일과 커밋 메시지도 받는 사람에게 그대로 간다
        for line in git(repo, "log", "--all", "--format=%h%x09%an <%ae>%x09%s %b").splitlines():
            h = line.split("\t", 1)[0]
            for label, v in sc.find(line):
                meta.append((label, f"{h} (작성자·메시지)", v))
    head_vals = {(l, v) for l, _, v in head}
    only_hist = [x for x in hist if (x[0], x[2]) not in head_vals]
    return head, only_hist, meta


def check_gitignore(repo):
    """표본 파일명이 무시되는지, 이미 추적 중인 비밀 모양 파일이 있는지 본다."""
    if not (repo / ".git").exists():
        return [], []
    missing = []
    for s in IGNORE_SAMPLES:
        r = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--no-index", s], capture_output=True)
        if r.returncode != 0:
            missing.append(s)
    globs = [g for g in GITIGNORE_BLOCK.splitlines() if g and not g.startswith(("#", "!"))]
    tracked = [f for f in git(repo, "ls-files").splitlines()
               if any(fnmatch.fnmatch(Path(f).name, g) for g in globs) and not f.endswith(".env.example")]
    return missing, tracked


def load_config(path):
    cands = [Path(path).expanduser()] if path else [Path.home() / ".secret-scan.json"]
    for c in cands:
        if c.exists():
            return json.loads(c.read_text("utf-8")), c
    if path:
        raise SystemExit(f"설정 파일이 없다: {path}")
    return {}, None


def main():
    ap = argparse.ArgumentParser(description="공개 전 비밀키·민감 이름 검사")
    ap.add_argument("repos", nargs="*", default=["."])
    ap.add_argument("--config")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--print-gitignore", action="store_true")
    a = ap.parse_args()

    if a.print_gitignore:
        print(GITIGNORE_BLOCK)
        return 0
    if a.init:
        dest = Path(a.config).expanduser() if a.config else Path.home() / ".secret-scan.json"
        if dest.exists():
            print(f"이미 있다: {dest} (덮어쓰지 않음)")
            return 2
        dest.write_text(json.dumps(EXAMPLE_CONFIG, ensure_ascii=False, indent=2), "utf-8")
        print(f"만들었다: {dest}  → names 에 내 고객사명·계정·경로를 넣는다")
        return 0

    cfg, cfg_path = load_config(a.config)
    sc = Scanner(cfg)
    out = lambda s: print(sc.guard(s))  # 모든 출력은 이 한 곳을 지난다
    print(f"설정: {cfg_path or '없음 (비밀키 모양·개인정보 모양만 검사)'}")
    total = 0
    for rp in a.repos:
        repo = Path(rp).expanduser().resolve()
        if cfg_path and repo in cfg_path.resolve().parents:
            out(f"[경고] 설정 파일이 검사 대상 저장소 안에 있다. 민감 목록이 같이 공개된다: {cfg_path.name}")
        try:
            head, only_hist, meta = scan_repo(repo, sc, history=not a.no_history)
            missing, tracked = check_gitignore(repo)
        except RuntimeError as e:
            out(f"== {repo.name}: 실행 오류 {e}")
            return 2
        n = len(head) + len(only_hist) + len(meta) + len(tracked)
        total += n
        out(f"== {repo.name}: 현재 파일 {len(head)}건 · 이력에만 {len(only_hist)}건 · 작성자·메시지 {len(meta)}건 · 추적 중인 비밀 모양 파일 {len(tracked)}개")
        seen = set()
        for tag, rows in (("현재", head), ("이력", only_hist), ("메타", meta)):
            for label, where, val in rows:
                key = (tag, label, where.split(":")[-1], val)
                if key in seen:
                    continue
                seen.add(key)
                out(f"   [{tag}] {label:12} {where[:80]} -> {mask(val)}")
        for f in tracked:
            out(f"   [추적] 비밀 모양 파일  {f}  (git rm --cached 후 .gitignore)")
        if missing:
            out(f"   [.gitignore] 무시되지 않는 표본: {', '.join(missing)}  (--print-gitignore 블록을 넣는다)")
    out(f"\n합계 {total}건")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

---
name: windows-task-scheduler-silent-fail
description: 윈도우 작업 스케줄러에 등록한 자동화(파이썬·bat·PowerShell)가 "마지막 실행 결과 0" 인데 실제로는 안 돌았거나, 손으로 돌리면 되는데 예약 실행만 실패할 때 쓴다. "스케줄러가 안 돌아", "예약 작업 결과는 성공인데 로그가 없어", "노트북에서 자동화가 가끔 빠져", "0xC000013A", "267011", "검은 창이 떠", "새 예약 작업 등록해줘" 요청 시 사용. 조용히 안 도는 원인과 등록·검증 절차가 들어 있다.
---

# 윈도우 작업 스케줄러가 조용히 안 도는 경우

**`LastTaskResult = 0` 은 실행 성공의 근거가 아니다.** `schtasks /run` 도 rc=0 을 돌려준다. 판정은 항상 두 개를 같이 본다: 결과 코드 + **로그 파일(또는 산출물)의 수정 시각이 방금으로 바뀌었는가.**

## 1. 증상 → 원인

| 증상 | 원인 | 고치는 법 |
|---|---|---|
| 노트북에서만 가끔 안 돈다. 실행 기록조차 없다(`LastRunTime` 이 1999-11-30, 결과 `267011`) | 설정 `DisallowStartIfOnBatteries` 기본값이 True. 배터리 상태면 예약 시각에 조용히 건너뛴다 | 등록 때 `-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable` |
| 결과 0 인데 아무 일도 안 일어났다 | 실행 경로(Execute)에 한글이 들어 있다 | 경로에서 한글을 뺀다. 못 빼면 `mklink /J C:\jobs\myjob "<한글 경로>"` 로 영문 정션을 만들어 그 경로로 등록 |
| `0x80070002`(파일 없음), 어제까지는 됐다 | Execute 에 `py` 나 `python` 만 적었다. `py` 는 사용자 PATH 전용 바로가기라 스케줄러 환경에서 간헐적으로 못 찾는다. 다른 프로그램 설치가 PATH 맨 앞을 바꿔도 전부 깨진다 | 파이썬 **실행 파일 전체 경로**로 등록(`where python` 첫 줄 말고 실제 설치 경로) |
| `0xC000013A`(3221225786), 손으로 돌리면 0 | 콘솔 창(`python.exe`)이 강제 종료됨 | `pythonw.exe` 로 등록. 아래 pythonw 함정도 같이 처리 |
| `pythonw` 로 바꿨더니 결과 1, 로그 없음 | `pythonw` 는 `sys.stdout`·`sys.stderr` 가 `None` 이다. 첫 줄의 `sys.stdout.reconfigure(...)` 나 `print` 에서 즉사 | 진입부에 `if sys.stdout is None: sys.stdout = open(os.devnull, "w")`(stderr 도). 실행 기록은 화면이 아니라 파일에 쓴다 |
| 결과 `267009`(실행 중)가 몇 시간째 그대로 | `pythonw` 가 띄운 자식 프로세스(PowerShell 등)가 표준입력을 기다리며 멈췄다. `subprocess` 의 timeout 도 안 먹는다 | 자식은 `creationflags=subprocess.CREATE_NO_WINDOW` + `stdin=subprocess.DEVNULL`, PowerShell 은 `-NonInteractive` |
| bat 이 손으로는 되는데 예약으로는 `2`·`0xC0000142`·`0xC000013A` 를 번갈아 낸다 | cmd 가 bat 을 시스템 코드페이지(한국어 윈도우 = CP949)로 읽는다. UTF-8·LF 로 저장한 bat 은 한글 경로 줄부터 파싱이 어긋나 작업 폴더가 System32 로 남는다 | **스케줄러에 bat 을 쓰지 않는다.** `pythonw.exe <래퍼>.py` 를 직접 등록한다. 꼭 bat 이면 CP949 + CRLF 로 저장하고 경로는 `%~dp0` 상대경로로 |
| 한글이 든 ps1 이 관리자 권한으로 띄우자마자 창이 닫힌다 | Windows PowerShell 5.1 은 BOM 없는 파일을 CP949 로 읽는다. 한글이 깨져 파스 에러로 즉시 종료 | ps1 은 **UTF-8 BOM** 으로 저장(에디터·AI 도구가 BOM 없이 쓰는 경우가 많다). 실행 전 `[System.Management.Automation.Language.Parser]::ParseFile` 로 파스 검증 |
| 절전에서 깨어난 직후의 실행만 `getaddrinfo failed` 로 전멸 | 밀린 작업이 복귀 순간에 한꺼번에 도는데 그때는 네트워크가 아직 안 붙었다 | 스크립트 진입부에서 대상 도메인 `socket.getaddrinfo` 가 될 때까지 15초 간격으로 최대 5분 기다린다 |
| 두 작업이 동시에 밀려 돌면 하나가 로그 한 줄 없이 결과 1 | 두 작업이 같은 로그 파일에 `>>` 리디렉션한다. 한쪽이 파일을 못 연다 | **작업마다 로그 파일을 따로 준다** |
| ps1 에 넘긴 인자가 사라졌다(`--dry` 가 빠진 채 실행 등) | 파라미터 이름을 `$Args` 로 지었다. PowerShell 자동변수와 충돌해 값이 빈다 | `$Mode` 같은 고유한 이름. 등록 뒤 `(Get-ScheduledTask 이름).Actions[0].Arguments` 를 눈으로 대조 |
| 예약 작업 등록이 "액세스가 거부되었습니다" | `/RL HIGHEST` 로 등록하려면 등록하는 쪽이 관리자여야 한다 | 관리자 권한이 필요 없는 작업이면 `/RL` 을 뺀다. 이미 Highest 로 등록된 작업은 수정·삭제도 관리자 권한에서 |

## 2. 새 작업 등록 절차

1. 실행 대상은 **`pythonw.exe` 전체 경로 + 스크립트 전체 경로**로 정한다. 창이 뜨지 않고, cmd 인코딩 문제가 없다
2. PowerShell `Register-ScheduledTask` 로 등록한다(`schtasks /Create` 는 배터리 기본값을 바꿀 수 없다)

```powershell
$act  = New-ScheduledTaskAction -Execute "C:\Path\To\pythonw.exe" -Argument "C:\jobs\myjob\run.py" -WorkingDirectory "C:\jobs\myjob"
$trg  = New-ScheduledTaskTrigger -Daily -At 7:30am
$set  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "MyJob" -Action $act -Trigger $trg -Settings $set
```

3. 등록 직후 인자를 눈으로 확인한다: `(Get-ScheduledTask MyJob).Actions[0] | Format-List Execute,Arguments,WorkingDirectory`
4. **밖으로 메일·메시지를 보내는 작업이면** 스크립트 기본값을 "보내지 않음(dry)"으로 두고 실제 발송은 `--send` 같은 명시 플래그로만 한다. 인자 확인 전에 `Start-ScheduledTask` 로 "시험"하면 그 시험이 실발송이 된다
5. `Start-ScheduledTask MyJob` → `Get-ScheduledTaskInfo MyJob` 의 `LastTaskResult` **그리고** 로그 파일 수정 시각이 방금으로 바뀌었는지 확인한다. 둘 다 맞아야 "됐다"
6. 스크립트는 실패하면 스스로 알린다(메일·메신저 1회). 스케줄러의 결과 코드는 아무도 보지 않는다

## 3. 기존 작업을 고칠 때

- 배터리 설정 전수 점검:

```powershell
Get-ScheduledTask | ? { $_.State -ne 'Disabled' } | % { "{0}  {1}" -f $_.TaskName, $_.Settings.DisallowStartIfOnBatteries }
```

- 고칠 때 `New-ScheduledTaskSettingsSet` 으로 설정을 통째로 바꾸면, 반복(Repetition) 트리거가 있는 작업에서 `0x80041319` 로 깨진다. **속성만 바꿔 넣는다:**

```powershell
$t = Get-ScheduledTask MyJob
$t.Settings.DisallowStartIfOnBatteries = $false
$t.Settings.StopIfGoingOnBatteries = $false
$t.Settings.StartWhenAvailable = $true
Set-ScheduledTask -InputObject $t
```

## 4. 프로세스가 살아 있는지 볼 때

`wmic process` 는 윈도우 11 에서 지원이 끊겨 **실제로 도는 프로세스를 빈 결과로 돌려줄 때가 있다.** 그걸 믿고 "죽었다"며 같은 작업을 또 띄우면 이중 실행이 된다.
`Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Select ProcessId,CommandLine` 으로 보고, 산출물(파일 수·로그 수정 시각)이 늘고 있으면 조회 결과보다 그쪽을 믿는다.

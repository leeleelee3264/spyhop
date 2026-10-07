# Spyhop

> 범고래가 수면 위로 머리만 내밀고 주변을 둘러보는 행동을 spyhop 이라고 부릅니다.

[Orca](https://github.com/stablyai/orca)에 떠 있는 모든 AI 코딩 세션(Claude Code · Codex)을 한 장의 보드로 보여줍니다.
세션마다 **지금 무슨 일을 하고 있는지, 어디까지 왔는지, 내가 답해야 하는지**를 한눈에 봅니다.

- **칸 묶기**: 기본은 오르카 워크스페이스(왼쪽 목록의 한 줄)마다 칸 하나. 설정에서 **AI topics** 를 고르면 요약 모델이 세션을 주제별로 최대 6개 그룹에 묶습니다. 한 번 정한 그룹은 유지되고, 카드를 다른 그룹으로 끌어 놓으면 그 배정이 고정됩니다(`~/.spyhop/groups.json`).
- **카드 = 세션**: 제목, 모델, 대기 시간, 단계 흐름(Done · Now · Next, 하던 일 도중 급히 처리한 일은 보라색 Intercept)을 보여줍니다.
- **내 차례 / 작업 중**: AI가 답을 마치고 나를 기다리는 세션을 위로 올립니다.
- **진전 없음**: 작업 중인데 대화 기록이 5분 넘게 그대로면 표시합니다.
- **상세 창**: 단계별 설명, 마지막 답, TODO 체크리스트, 마지막 요청과 답 원문(마크다운), 세션 ID(누르면 `claude --resume` 명령 복사).
- **조작**: 카드에서 바로 그 창으로 이동, 세션 끝내기, 다른 워크스페이스로 끌어다 옮기기(이어 열기).
- **설정(톱니바퀴)**: 요약 모델, 테마(Classic · Material Indigo · Teal · You · Dark · Blue Grey), 범고래 애니메이션 켜기·끄기, 갱신 주기(10·30·60초)를 고릅니다. 세션 재정리 간격은 주기에 맞춰 1·3·5분으로 정해집니다. 보드 자신의 CPU·메모리 사용량도 그래프로 보여줍니다. 값은 `~/.spyhop/config.json` 에 저장됩니다.
- **메뉴바 패널**(선택): [SwiftBar](https://github.com/swiftbar/SwiftBar)로 메뉴바에 내 차례 수와 작은 패널을 띄웁니다.

## 동작 방식

1. `orca terminal list` / `orca worktree ps` 로 떠 있는 세션과 상태를 읽습니다.
2. 세션마다 대화 기록을 찾습니다. Claude 는 `~/.claude/projects/`, Codex 는 `~/.codex/sessions/`.
3. 기록을 LLM 에 보내 제목 · 요약 · 단계 · TODO 를 JSON 으로 받습니다.
   - 처음 한 번만 전체를 읽고, 그 뒤로는 **지난 정리 + 새로 쌓인 대화만** 보내 이어서 고칩니다.
   - 끝낸 단계와 제목은 고정되어 매번 바뀌지 않습니다.
   - 바뀐 세션만, 세션당 1분에 한 번까지 다시 정리합니다.
4. `127.0.0.1:47613` 에 보드를 띄웁니다.

## 필요한 것

- macOS, Python 3.9+
- Orca 와 `orca` CLI
- 요약 모델 하나 이상. 보드 오른쪽 위 톱니바퀴(Settings)에서 고르며, 이 맥에서 실제로 쓸 수 있는 것만 보입니다. 고른 값은 `~/.spyhop/config.json` 에 저장됩니다.

| 제공자 | 고를 수 있는 모델 | 필요한 것 | 대화가 가는 곳 |
|---|---|---|---|
| DeepSeek (API) | DeepSeek flash | 키체인에 `deepseek-api` 키 | DeepSeek |
| Claude (claude CLI) | Haiku · Sonnet · Opus · Fable (현재 모델 + 이 맥 대화 기록에 쓰인 모델) | 로그인된 `claude` | Anthropic |
| Codex (codex CLI) | `~/.codex/models_cache.json` 에 있는 모델 (GPT-6.1-Sol 등) | 로그인된 `codex` | OpenAI |

```bash
# DeepSeek 키 등록
security add-generic-password -s deepseek-api -a "$USER" -w '<API 키>'
```

Claude·Codex CLI 로 요약할 때는 요약 호출이 새 대화로 저장되지 않게 하고(`--no-session-persistence`, `--ephemeral`), 도구 실행을 막습니다. 구독 사용량을 씁니다.
DeepSeek 모델 이름은 `PROGRESS_BOARD_MODEL` 환경변수로 바꿀 수 있습니다(기본 `deepseek-flash`).

## 실행

```bash
./spyhop            # 감시를 켜고, 오르카에 전용 프로젝트(~/.spyhop, 빈 git 저장소)와 "Spyhop" 워크스페이스를 만들어(없으면) 그 안의 브라우저 탭으로 보드를 연다. 내 코드 저장소는 건드리지 않는다
python3 board.py --ensure   # 감시만 켠다
```

- 보드: http://127.0.0.1:47613/
- 메뉴바 패널: http://127.0.0.1:47613/panel

### 켜지고 꺼지는 기준

- **켜짐**: `./spyhop` 실행 · 맥 로그인(설정의 Start at login 또는 `./spyhop --autostart`, 기본은 꺼짐) · Claude나 Codex가 떠 있을 때(메뉴바 플러그인이 5초마다 확인)
- **꺼짐**: 떠 있는 AI 세션이 30분 동안 하나도 없으면 스스로 끝납니다. 다시 Claude·Codex를 켜거나 `./spyhop`을 실행하면 켜집니다.
- 감시 프로세스는 하나만 뜹니다(중복 실행은 바로 종료).
- 오르카 탭은 `~/.spyhop/open.html` 을 엽니다. 서버가 꺼져 있으면 "Starting the board…"를 보여주고, 서버가 뜨면 보드를 띄웁니다.

```bash
./spyhop --autostart      # 맥 로그인 때 자동 시작 (LaunchAgent)
./spyhop --no-autostart   # 해제
```

### 메뉴바 (선택)

SwiftBar 플러그인 폴더에 `menubar/spyhop.5s.py` 를 링크합니다. 이 플러그인은 Claude·Codex 가 떠 있으면 감시 프로세스를 자동으로 켭니다.

```bash
ln -s "$PWD/menubar/spyhop.5s.py" "<SwiftBar 플러그인 폴더>/spyhop.5s.py"
```

## 데이터

- 대화 기록은 요약을 위해 설정한 LLM API 로 전송됩니다. 보내기 전에 AWS 키, API 토큰, JWT, `password=` 꼴 값 등을 정규식으로 가립니다. 완전한 차단은 아니니, 민감한 대화가 많다면 사내에서 허용된 모델로 바꿔 쓰세요.
- 정리 결과와 상태는 `/tmp/progress-board/` 에만 저장됩니다.
- 서버는 `127.0.0.1` 에만 열리고, 지금 보드에 있는 세션에 대해서만 이동·끝내기 요청을 받습니다.

## 파일

| 파일 | 역할 |
|---|---|
| `board.py` | 세션 수집 · 요약 · 보드 HTML 생성 · 로컬 서버 |
| `panel.html` | 메뉴바 패널 화면 |
| `menubar/spyhop.5s.py` | SwiftBar 플러그인 |
| `orca_art.py` | 범고래 아이콘(파비콘 · 메뉴바 · 헤더 애니메이션) |
| `spyhop` | 실행 스크립트 |

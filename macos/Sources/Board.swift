import Foundation

/// 보드 서버(board.py)와 이야기하는 곳. 서버는 지금 그대로 파이썬이고, 앱은 켜 주고 상태만 읽는다.
enum Board {
    static let port: UInt16 = 47613
    static let url = URL(string: "http://127.0.0.1:47613/")!
    static let panelURL = URL(string: "http://127.0.0.1:47613/panel")!
    static let base = "/tmp/progress-board"
    static let stateFile = base + "/state.json"
    static let pidFile = base + "/watch.pid"
    static let home = NSHomeDirectory() + "/.spyhop"
    static let python = "/usr/bin/python3"
    static var code: String { Bundle.main.resourcePath! + "/spyhop" }
    static var script: String { code + "/board.py" }

    /// 서버가 받아 주는가. 127.0.0.1 이라 막혀 있으면 바로 거절이 온다
    static func isUp() -> Bool {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { return false }
        defer { close(fd) }
        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")
        return withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) == 0 }
        }
    }

    /// 맥에 Xcode 명령줄 도구(파이썬)가 있는가. 없으면 /usr/bin/python3 가 설치 창을 띄운다
    static func toolsInstalled() -> Bool {
        run("/usr/bin/xcode-select", ["-p"]) == 0
    }

    /// 감시를 띄우거나 바꾸는 일은 한 줄로 세운다(앱이 뜨자마자 부른 것과 5초 확인이 겹치지 않게). 뒤에 온 것은 앞의 것이 띄운 서버를 보고 끝난다
    private static let queue = DispatchQueue(label: "spyhop.board")

    /// 감시가 없으면 띄운다. 감시는 앱과 따로 살아서 앱을 꺼도 계속 돈다(30분 동안 세션이 없으면 스스로 끝남).
    /// 이미 다른 경로(brew 설치본 등)의 감시가 돌고 있으면 건드리지 않는다: 서로 내리고 띄우는 다툼을 막는다.
    /// onlyIfAgents: 메뉴바 플러그인이 하던 대로, 세션(Claude·Codex·OMP)이 떠 있을 때만 다시 켠다
    static func ensure(onlyIfAgents: Bool = false) {
        queue.async {
            restartIfReplaced()
            if !isUp() && (!onlyIfAgents || agentsRunning()) { spawnOnOwn(python, [script, "--ensure"]) }
        }
    }

    /// 로그인 자동 시작(LaunchAgent)과 같은 PATH. Finder 로 연 앱은 PATH 가 최소라 orca·node 를 못 찾는다
    static var serverEnvironment: [String] {
        var env = ProcessInfo.processInfo.environment
        env["__CFBundleIdentifier"] = nil
        env["XPC_SERVICE_NAME"] = nil
        env["PATH"] = ["/usr/local/bin", "/opt/homebrew/bin", NSHomeDirectory() + "/.local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"].joined(separator: ":")
        return env.map { "\($0.key)=\($0.value)" }
    }

    /// 서버를 앱의 「책임 아래」가 아니라 스스로 책임지는 프로세스로 띄운다(로그인 자동 시작으로 뜬 서버와 같은 처지).
    /// 그래야 터미널 제어 권한을 묻고 기억하는 주체가 앱이 아니라 파이썬이 되어, 서명 없는 앱을 업데이트해도 권한이 풀리지 않는다
    static func spawnOnOwn(_ path: String, _ args: [String]) {
        var attr: posix_spawnattr_t?
        posix_spawnattr_init(&attr)
        defer { posix_spawnattr_destroy(&attr) }
        typealias Disclaim = @convention(c) (UnsafeMutablePointer<posix_spawnattr_t?>, Int32) -> Int32
        if let f = dlsym(UnsafeMutableRawPointer(bitPattern: -2), "responsibility_spawnattrs_setdisclaim") {  // RTLD_DEFAULT
            _ = unsafeBitCast(f, to: Disclaim.self)(&attr, 1)
        }
        // 앱(AppKit)은 SIGTERM 을 무시로 걸어 두는데 그게 자식에게 물려진다. 그러면 새 버전 서버가 옛 서버를 못 내린다(실제로 겪음).
        // 신호 처리를 기본값으로 되돌려서 띄운다
        var all = sigset_t(), none = sigset_t()
        sigfillset(&all)
        sigemptyset(&none)
        posix_spawnattr_setsigdefault(&attr, &all)
        posix_spawnattr_setsigmask(&attr, &none)
        posix_spawnattr_setflags(&attr, Int16(POSIX_SPAWN_SETSIGDEF | POSIX_SPAWN_SETSIGMASK))
        var fa: posix_spawn_file_actions_t?
        posix_spawn_file_actions_init(&fa)
        defer { posix_spawn_file_actions_destroy(&fa) }
        posix_spawn_file_actions_addopen(&fa, 0, "/dev/null", O_RDONLY, 0)
        posix_spawn_file_actions_addopen(&fa, 1, "/dev/null", O_WRONLY, 0)
        posix_spawn_file_actions_addopen(&fa, 2, "/dev/null", O_WRONLY, 0)
        let argv = ([path] + args).map { strdup($0) } + [nil]
        let envp = serverEnvironment.map { strdup($0) } + [nil]
        defer { argv.forEach { free($0) }; envp.forEach { free($0) } }
        var pid: pid_t = 0
        guard posix_spawn(&pid, path, &fa, &attr, argv, envp) == 0 else { return }
        var st: Int32 = 0
        waitpid(pid, &st, 0)
    }

    static var bundleVersion: String? { Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String }

    /// 앱을 새 버전으로 바꿔 끼웠는데 옛 코드 서버가 그대로 돌고 있으면 내리고 새로 띄운다
    /// (brew 설치본은 서버가 스스로 바꾸지만, 앱 안의 코드는 그 확인 대상이 아니다).
    /// 이 앱 안의 코드로 돈 서버만, 실제로 응답하고 있고 그 PID 가 정말 그 서버일 때만 내린다
    static func restartIfReplaced() {
        guard isUp(), let rec = try? String(contentsOfFile: pidFile, encoding: .utf8) else { return }
        // 「pid 경로 시작시각」. 경로에 빈칸이 있을 수 있어 앞뒤 칸으로 자른다
        let parts = rec.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: " ", omittingEmptySubsequences: false)
        guard parts.count >= 3, let pid = Int32(parts[0]), let started = Double(parts[parts.count - 1]), started > 0 else { return }
        let path = parts[1..<(parts.count - 1)].joined(separator: " ")
        let ours = (script as NSString).resolvingSymlinksInPath
        // 앱을 다른 자리로 옮겼으면(옛 자리에 코드가 없음) 그 서버를 넘겨받는다. 다른 자리에 앱이 따로 남아 있거나 brew 설치본이면 건드리지 않는다
        let moved = path != ours && path.hasSuffix(".app/Contents/Resources/spyhop/board.py") && !FileManager.default.fileExists(atPath: path)
        guard path == ours || moved else { return }
        // 이 서버가 쓴 state.json 이 있어야 판단한다(막 떠서 첫 화면을 만드는 중이거나, 지난번 다른 서버가 남긴 파일이면 건너뜀)
        guard let st = (try? JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: stateFile)))) as? [String: Any],
              let at = st["at"] as? Double, at >= started else { return }
        let running = st["version"] as? String  // 없으면 version 을 쓰기 전의 옛 코드
        let mod = ((try? FileManager.default.attributesOfItem(atPath: script))?[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0
        // 버전이 다르면(릴리즈 교체) 또는 같은 버전이라도 코드 파일이 서버보다 새것이면(개발 빌드) 바뀐 것이다
        guard moved || running != bundleVersion || mod > started + 1 else { return }
        // 번호가 다른 프로그램에 다시 쓰였을 수 있어 시작 시각과 실행 인자까지 서버가 남긴 기록과 맞춰 본다(board.py 와 같은 기준)
        guard let born = startTime(pid), abs(born - started) < 2,
              let args = output("/bin/ps", ["-o", "args=", "-p", String(pid)])?.trimmingCharacters(in: .whitespacesAndNewlines),
              args.hasSuffix(path + " --watch") else { return }
        kill(pid, SIGTERM)
        for _ in 0..<50 where kill(pid, 0) == 0 { usleep(100_000) }
        // 헤더 버전 배지가 「vX 에서 업데이트됨」을 보이게 brew 업그레이드 때와 같은 기록을 남긴다
        if let old = running, let new = bundleVersion, old != "dev", newer(new, than: old) {
            let rec: [String: Any] = ["from": old, "to": new, "at": Date().timeIntervalSince1970, "seen": false]
            if let d = try? JSONSerialization.data(withJSONObject: rec) { try? d.write(to: URL(fileURLWithPath: home + "/update.json")) }
        }
    }

    /// "1.2.10" > "1.2.9" 처럼 숫자로 비교한다(내려간 경우엔 「업데이트됨」 배지를 쓰지 않으려고)
    static func newer(_ a: String, than b: String) -> Bool {
        a.compare(b, options: .numeric) == .orderedDescending
    }

    /// 메뉴바가 하던 일: 감시가 꺼져 있을 때 Claude·Codex·OMP 가 떠 있으면 다시 켤 이유가 있다
    static func agentsRunning() -> Bool {
        for line in (output("/bin/ps", ["-axo", "comm="]) ?? "").split(separator: "\n") {
            let comm = String(line)
            let name = (comm as NSString).lastPathComponent
            if name == "claude" || name == "codex" || comm.range(of: #"/claude/versions/\d[\w.-]*$"#, options: .regularExpression) != nil {
                return true
            }
        }
        // OMP 는 상태 확장이 남긴 파일로 안다
        let dir = home + "/omp"
        for f in (try? FileManager.default.contentsOfDirectory(atPath: dir)) ?? [] where f.hasSuffix(".json") {
            // 서버(omp_sessions·agent_pids)와 같은 기준: 형식이 맞고, 그 번호의 프로그램이 기록된 시각에 시작했을 때만
            guard let d = FileManager.default.contents(atPath: dir + "/" + f),
                  let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
                  let pid = j["pid"] as? Int, pid > 0, let start = j["start"] as? Double,
                  j["busy"] is Bool, j["cwd"] is String, j["sid"] is String,
                  let born = startTime(pid_t(pid)), abs(born - start) < 5 else { continue }
            return true
        }
        return false
    }

    /// 그 번호 프로그램이 시작한 시각(epoch 초). 없으면 nil
    static func startTime(_ pid: pid_t) -> Double? {
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.stride
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
        guard sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0 else { return nil }
        let t = info.kp_proc.p_un.__p_starttime
        return Double(t.tv_sec) + Double(t.tv_usec) / 1_000_000
    }

    struct State {
        var wait = 0, busy = 0, stale = true
        var appearance = "system"
    }

    /// 메뉴바 숫자용. 서버가 쓰는 요약 파일을 읽기만 한다
    static func state() -> State {
        guard let d = FileManager.default.contents(atPath: stateFile),
              let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return State() }
        let look = j["appearance"] as? String ?? "system"
        let at = j["at"] as? Double ?? 0
        if Date().timeIntervalSince1970 - at > 120 { return State(appearance: look) }
        let ss = j["sessions"] as? [[String: Any]] ?? []
        let w = ss.filter { $0["status"] as? String == "wait" }.count
        return State(wait: w, busy: ss.count - w, stale: false, appearance: look)
    }

    static func output(_ path: String, _ args: [String]) -> String? {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: path)
        p.arguments = args
        let out = Pipe()
        p.standardOutput = out
        p.standardError = FileHandle.nullDevice
        guard (try? p.run()) != nil else { return nil }
        let data = out.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return String(decoding: data, as: UTF8.self)
    }

    @discardableResult
    static func run(_ path: String, _ args: [String]) -> Int32 {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: path)
        p.arguments = args
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        guard (try? p.run()) != nil else { return -1 }
        p.waitUntilExit()
        return p.terminationStatus
    }
}

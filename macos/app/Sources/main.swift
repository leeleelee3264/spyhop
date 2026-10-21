import AppKit
import WebKit

/// Spyhop.app: 보드를 브라우저 대신 앱 창에, 메뉴바 아이콘은 SwiftBar 대신 앱이 직접.
/// 세션 찾기·요약·화면은 전부 지금의 board.py 가 그대로 한다.
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, NSPopoverDelegate {
    var window: NSWindow?
    var status: NSStatusItem!
    // 패널 틀은 하나를 계속 쓴다. 열 때마다 새로 만들면 macOS 가 닫힌 틀의 배경(유리 효과)을 놓지 않아 한 번에 수 MB 씩 쌓인다(실측)
    lazy var popover: NSPopover = {
        let p = NSPopover()
        p.behavior = .transient
        p.delegate = self
        p.contentSize = NSSize(width: 380, height: 560)
        return p
    }()
    var timer: Timer?
    var popoverClosedAt = Date.distantPast

    func applicationDidFinishLaunching(_ n: Notification) {
        buildMenu()
        guard Board.toolsInstalled() else { return needTools() }
        // 다운로드 폴더나 DMG 에서 바로 열면 macOS 가 앱을 임시 위치로 옮겨 실행한다. 거기서 띄운 서버는 앱을 끄면 코드가 사라진다
        // 마운트한 DMG 안에서 바로 열어도 DMG 를 꺼내면 코드가 사라진다
        let at = Bundle.main.bundlePath
        guard !at.contains("/AppTranslocation/") && !at.hasPrefix("/Volumes/") else { return needMove() }
        removeSwiftBarPlugin()
        Board.ensure()
        setupStatusItem()
        // 로그인 때 뜬 것이면 창은 열지 않고 메뉴바에만 (예전 SwiftBar 처럼 Dock 에도 안 보인다)
        if CommandLine.arguments.contains("--login") { NSApp.setActivationPolicy(.accessory) } else { showWindow() }
        tick()
        // 메뉴바 플러그인과 같은 5초 주기: 숫자 갱신 + 감시가 꺼졌을 때 세션이 생기면 다시 켜기
        timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.tick() }
        timer?.tolerance = 1
    }

    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows v: Bool) -> Bool {
        showWindow()
        return true
    }

    // 창을 닫아도 메뉴바에 남는다 (창은 웹 화면째 내려서 메모리를 돌려준다)
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { false }

    func tick() {
        if !Board.isUp() { Board.ensure(onlyIfAgents: true) }  // 프로세스 목록 확인은 뒤에서
        let s = Board.state()
        // 메뉴바 플러그인과 같은 표시: 내 차례 수, 없으면 ·일하는 수
        let text = s.wait > 0 ? " \(s.wait)" : (s.stale || s.busy == 0 ? "" : " ·\(s.busy)")
        if status.button?.title != text { status.button?.title = text }
        // 앱 창 제목줄·패널을 보드 테마 밝기에 맞춘다(Classic 은 시스템을 따름)
        let look: NSAppearance? = s.appearance == "dark" ? NSAppearance(named: .darkAqua) : s.appearance == "light" ? NSAppearance(named: .aqua) : nil
        if NSApp.appearance?.name != look?.name { NSApp.appearance = look }
        syncLoginItem()
    }

    // MARK: 창

    @objc func showWindow() {
        popover.performClose(nil)
        Board.ensure()  // 세션이 없어 감시가 쉬고 있어도, 사람이 보드를 열면 켠다(예전 spyhop 명령과 같게)
        NSApp.setActivationPolicy(.regular)  // 창이 있을 때만 Dock·Cmd-Tab 에 보인다
        if window == nil {
            let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 800),
                             styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            w.title = "Spyhop"
            w.isReleasedWhenClosed = false
            w.delegate = self
            w.minSize = NSSize(width: 420, height: 320)
            let v = WebHost.shared.makeWebView(frame: w.contentView!.bounds)
            v.autoresizingMask = [.width, .height]
            w.contentView!.addSubview(v)
            let z = UserDefaults.standard.double(forKey: Self.zoomKey)
            if z > 0 { v.pageZoom = z }
            WebHost.shared.openBoard(v)
            w.setFrameAutosaveName("SpyhopBoard")
            if !w.setFrameUsingName("SpyhopBoard") { w.center() }
            window = w
        }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // 창이 다른 앱·다른 데스크톱에 완전히 가려지면 웹 화면을 숨겨 쉬게 한다. 브라우저가 가려진 탭을 멈추는 것과 같게
    // (그대로 두면 WebKit 이 가려진 채로 계속 그린다. 실측 CPU 30%대 → 1% 아래)
    func windowDidChangeOcclusionState(_ n: Notification) {
        guard let w = n.object as? NSWindow, w === window else { return }
        boardView?.isHidden = !w.occlusionState.contains(.visible)
    }

    func windowWillClose(_ n: Notification) {
        guard let w = n.object as? NSWindow, w === window else { return }
        // 닫기가 끝난 뒤에 웹 화면과 창을 놓는다(닫는 도중에 창을 놓으면 빈 창이 화면에 남는다. 실제로 겪음)
        DispatchQueue.main.async { [weak self] in
            w.contentView?.subviews.forEach { if let v = $0 as? WKWebView { WebHost.shared.release(v) } else { $0.removeFromSuperview() } }
            if self?.window === w { self?.window = nil }
            NSApp.setActivationPolicy(.accessory)  // 창이 없으면 메뉴바에만 (예전 SwiftBar 처럼)
        }
    }

    var boardView: WKWebView? { window?.contentView?.subviews.first as? WKWebView }

    @objc func reload() {
        guard let v = boardView else { return }
        WebHost.shared.openBoard(v)
    }

    // 브라우저처럼 Cmd +/- 로 글자 크기
    static let zoomKey = "BoardZoom"
    func setZoom(_ z: Double) {
        let z = min(3, max(0.5, (z * 10).rounded() / 10))
        boardView?.pageZoom = z
        UserDefaults.standard.set(z, forKey: Self.zoomKey)
    }
    @objc func zoomIn() { setZoom((boardView?.pageZoom ?? 1) + 0.1) }
    @objc func zoomOut() { setZoom((boardView?.pageZoom ?? 1) - 0.1) }
    @objc func zoomReset() { setZoom(1) }

    // MARK: 메뉴바

    func setupStatusItem() {
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let b = status.button {
            b.image = Self.menubarIcon()
            b.imagePosition = .imageLeft
            b.target = self
            b.action = #selector(statusClicked(_:))
            b.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
    }

    static func menubarIcon() -> NSImage? {
        guard let p = Bundle.main.path(forResource: "MenuBarIcon", ofType: "png"), let img = NSImage(contentsOfFile: p) else { return nil }
        img.size = NSSize(width: 20, height: 20)
        return img
    }

    @objc func statusClicked(_ sender: NSStatusBarButton) {
        let right = NSApp.currentEvent?.type == .rightMouseUp || NSApp.currentEvent?.modifierFlags.contains(.control) == true
        if right || !Board.isUp() { return showMenu() }
        if popover.isShown { return popover.performClose(nil) }
        // 패널이 떠 있을 때 아이콘을 누르면, 누르는 순간(바깥 클릭) 이미 닫힌다. 그 뒤 손을 뗀 것으로 다시 열지 않는다
        if Date().timeIntervalSince(popoverClosedAt) < 0.35 { return }
        if window?.isVisible != true { NSApp.activate(ignoringOtherApps: true) }  // 보드 창이 떠 있으면 그 창까지 앞으로 끌어오지 않게
        // SwiftBar 때와 같은 380x560 패널. 웹 화면은 열 때 만들고 닫으면 내린다
        let vc = NSViewController()
        let v = WebHost.shared.makeWebView(frame: NSRect(x: 0, y: 0, width: 380, height: 560))
        v.load(URLRequest(url: Board.panelURL))
        vc.view = v
        popover.contentViewController = vc
        popover.show(relativeTo: sender.bounds, of: sender, preferredEdge: .minY)
        vc.view.window?.makeKey()
    }

    func popoverDidClose(_ n: Notification) {
        popoverClosedAt = Date()
        if let v = popover.contentViewController?.view as? WKWebView { WebHost.shared.release(v) }
        popover.contentViewController = nil
    }

    func showMenu() {
        let m = NSMenu()
        if !Board.isUp() {
            let i = NSMenuItem(title: "Watcher off · starts automatically when Claude/Codex runs", action: nil, keyEquivalent: "")
            i.isEnabled = false
            m.addItem(i)
            m.addItem(.separator())
        }
        m.addItem(withTitle: "Open board", action: #selector(showWindow), keyEquivalent: "").target = self
        m.addItem(.separator())
        m.addItem(withTitle: "Quit Spyhop", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        status.menu = m
        status.button?.performClick(nil)
        status.menu = nil
    }

    // MARK: 로그인 때 시작

    /// 설정의 Start at login 은 서버를 띄우는 LaunchAgent(com.spyhop.board)를 만든다. 앱이 깔려 있으면 메뉴바도 같이 뜨도록
    /// 앱을 창 없이 여는 LaunchAgent(com.spyhop.app)를 그 설정에 맞춰 두거나 지운다
    func syncLoginItem() {
        // 개발용 빌드(레포 안)가 로그인 항목에 올라가지 않게, 응용 프로그램 폴더에 깔린 앱만 맞춘다
        let at = Bundle.main.bundlePath
        guard at.hasPrefix("/Applications/") || at.hasPrefix(NSHomeDirectory() + "/Applications/") else { return }
        let dir = NSHomeDirectory() + "/Library/LaunchAgents"
        let want = FileManager.default.fileExists(atPath: dir + "/com.spyhop.board.plist")
        let mine = dir + "/com.spyhop.app.plist"
        let have = FileManager.default.fileExists(atPath: mine)
        let args = ["/usr/bin/open", "-g", "-a", at, "--args", "--login"]
        let current = (NSDictionary(contentsOfFile: mine)?["ProgramArguments"] as? [String]) ?? []
        // 다른 자리에 앱이 따로 남아 있고 그 앱을 가리키고 있으면 서로 덮어쓰지 않게 둔다(옮겨서 옛 자리가 비었으면 이 자리로)
        let other = current.count > 3 && current[3] != at && FileManager.default.fileExists(atPath: current[3])
        if want && current != args && !other {
            let plist: [String: Any] = [
                "Label": "com.spyhop.app",
                "ProgramArguments": args,
                "RunAtLoad": true,
                "AssociatedBundleIdentifiers": [Bundle.main.bundleIdentifier!],
            ]
            if let d = try? PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0) {
                try? d.write(to: URL(fileURLWithPath: mine))
            }
        } else if !want && have {
            try? FileManager.default.removeItem(atPath: mine)
        }
        // 서버 로그인 항목을 이 앱 코드로 맞춘다: brew 설치본을 가리키면(앱이 깔리면 `spyhop` 도 앱을 연다) 또는 옛 자리의 앱 코드인데 그 자리가 비었으면(앱을 옮김).
        // 그대로 두면 다음 로그인 때 brew 쪽 서버가 먼저 떠서 앱이 옛 보드를 보인다. 남아 있는 다른 앱은 그대로 둔다
        let board = dir + "/com.spyhop.board.plist"
        if want, let d = NSMutableDictionary(contentsOfFile: board), var a = d["ProgramArguments"] as? [String], a.count > 1, a[1] != Board.script,
           a[1].contains("/opt/spyhop/") || a[1].contains("/Cellar/spyhop/")
            || (a[1].hasSuffix(".app/Contents/Resources/spyhop/board.py") && !FileManager.default.fileExists(atPath: a[1])) {
            a[0] = "/usr/bin/python3"  // 앱이 서버를 띄울 때와 같은 파이썬
            a[1] = Board.script
            d["ProgramArguments"] = a
            d.write(toFile: board, atomically: true)
        }
    }

    // MARK: 정리

    /// 앱이 메뉴바를 맡으니, `spyhop` 명령이 SwiftBar 에 붙여 둔 플러그인은 뗀다(아이콘이 둘 뜨지 않게). 우리가 만든 링크만 지운다
    func removeSwiftBarPlugin() {
        guard let dir = UserDefaults(suiteName: "com.ameba.SwiftBar")?.string(forKey: "PluginDirectory") else { return }
        let link = (dir as NSString).expandingTildeInPath + "/spyhop.5s.py"
        guard let dest = try? FileManager.default.destinationOfSymbolicLink(atPath: link),
              dest.hasSuffix("/menubar/spyhop.5s.py") else { return }
        try? FileManager.default.removeItem(atPath: link)
    }

    func needMove() {
        let a = NSAlert()
        a.messageText = "Move Spyhop to your Applications folder"
        a.informativeText = "Drag Spyhop from the disk image (or Downloads) into Applications, then open it from there."
        a.addButton(withTitle: "Quit")
        a.runModal()
        NSApp.terminate(nil)
    }

    func needTools() {
        let a = NSAlert()
        a.messageText = "Spyhop needs the Xcode Command Line Tools"
        a.informativeText = "Spyhop runs on the Python that comes with them. Run this in Terminal, then open Spyhop again:\n\nxcode-select --install"
        a.addButton(withTitle: "Quit")
        a.runModal()
        NSApp.terminate(nil)
    }

    func buildMenu() {
        let main = NSMenu()
        let app = NSMenu()
        app.addItem(withTitle: "About Spyhop", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        app.addItem(.separator())
        app.addItem(withTitle: "Hide Spyhop", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        app.addItem(withTitle: "Quit Spyhop", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        let view = NSMenu(title: "View")
        view.addItem(withTitle: "Reload", action: #selector(reload), keyEquivalent: "r").target = self
        view.addItem(.separator())
        view.addItem(withTitle: "Actual Size", action: #selector(zoomReset), keyEquivalent: "0").target = self
        view.addItem(withTitle: "Zoom In", action: #selector(zoomIn), keyEquivalent: "=").target = self
        let plus = NSMenuItem(title: "Zoom In", action: #selector(zoomIn), keyEquivalent: "+")
        plus.target = self
        plus.isHidden = true
        plus.allowsKeyEquivalentWhenHidden = true
        view.addItem(plus)
        view.addItem(withTitle: "Zoom Out", action: #selector(zoomOut), keyEquivalent: "-").target = self
        let win = NSMenu(title: "Window")
        win.addItem(withTitle: "Board", action: #selector(showWindow), keyEquivalent: "1").target = self
        win.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        win.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        for (title, sub) in [("Spyhop", app), ("Edit", edit), ("View", view), ("Window", win)] {
            let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
            item.submenu = sub
            main.addItem(item)
        }
        NSApp.mainMenu = main
        NSApp.windowsMenu = win
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(CommandLine.arguments.contains("--login") ? .accessory : .regular)  // 로그인 때는 Dock 에 잠깐도 안 보이게
app.run()

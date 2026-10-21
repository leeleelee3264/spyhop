import AppKit
import WebKit

/// 보드·패널 화면을 띄우는 웹 화면. 브라우저 탭에서 하던 일 중 앱 창에 따로 필요한 것만 채운다:
/// 새 창 링크는 기본 브라우저로, JS 알림·확인·입력 창, 클립보드 복사.
final class WebHost: NSObject, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    static let shared = WebHost()

    // 보드는 iframe 안에서 navigator.clipboard 를 쓴다. 앱 웹 화면에서는 권한 없이 막힐 수 있어 앱이 대신 복사한다
    private static let clipboardJS = """
    (function(){try{var h=window.webkit&&window.webkit.messageHandlers&&window.webkit.messageHandlers.spyhopCopy;if(!h)return;
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:function(t){h.postMessage(String(t));return Promise.resolve()}}})}catch(e){}})();
    """

    /// board 가 true 면 보드 창용: 제목줄 없이 헤더가 창 맨 위로 올라가므로, 헤더 빈 곳을 끌면 창이 움직이게 한다
    func makeWebView(frame: NSRect, board: Bool = false) -> WKWebView {
        let cfg = WKWebViewConfiguration()
        let ucc = WKUserContentController()
        ucc.addUserScript(WKUserScript(source: Self.clipboardJS, injectionTime: .atDocumentStart, forMainFrameOnly: false))
        ucc.add(WeakHandler(self), name: "spyhopCopy")
        if board { ucc.add(WeakHandler(self), name: "spyhopChrome") }
        cfg.userContentController = ucc
        // 로더(file://)가 보드(http://127.0.0.1)를 iframe 으로 부르고, 꺼지면 다시 붙을 때까지 기다린다
        cfg.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        let v: WKWebView = board ? BoardWebView(frame: frame, configuration: cfg) : WKWebView(frame: frame, configuration: cfg)
        v.uiDelegate = self
        v.navigationDelegate = self
        v.setValue(false, forKey: "drawsBackground")
        return v
    }

    /// 오르카 탭과 같은 로더로 연다(빌드 때 board.py 의 로더를 앱 안에 넣어 둠). 서버가 살아 있으면 보드를 iframe 으로,
    /// 꺼져 있으면 「Starting the board…」를 보이며 다시 붙을 때까지 기다린다. 처음 깔아 서버가 아직 안 떴어도 빈 창이 되지 않는다
    func openBoard(_ v: WKWebView) {
        guard let loader = Bundle.main.url(forResource: "loader", withExtension: "html") else { v.load(URLRequest(url: Board.url)); return }
        v.loadFileURL(loader, allowingReadAccessTo: loader.deletingLastPathComponent())
    }

    // 메뉴바 패널은 서버에서 바로 연다. 서버가 막 꺼지거나 바뀌는 순간이라 연결을 못 했으면 2초 뒤 같은 주소로 다시
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) {
        let code = (e as NSError).code
        guard [NSURLErrorCannotConnectToHost, NSURLErrorNetworkConnectionLost, NSURLErrorTimedOut, NSURLErrorNotConnectedToInternet].contains(code) else { return }
        let failed = (e as NSError).userInfo[NSURLErrorFailingURLErrorKey] as? URL ?? Board.panelURL
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak w] in
            guard let w, w.window != nil else { return }
            w.load(URLRequest(url: failed))
        }
    }

    /// 앱 안에 보여도 되는 곳: 앱에 넣은 로더와 이 보드 서버뿐
    static func trusted(_ u: URL?) -> Bool {
        guard let u else { return false }
        if u.isFileURL { return u.path == Bundle.main.url(forResource: "loader", withExtension: "html")?.path }
        return u.scheme == "http" && u.host == "127.0.0.1" && u.port == Int(Board.port) || u.absoluteString == "about:blank"
    }

    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        let o = m.frameInfo.securityOrigin
        guard o.protocol == "file" || (o.host == "127.0.0.1" && o.port == Int(Board.port)) else { return }
        if m.name == "spyhopChrome", let v = m.webView as? BoardWebView, let d = m.body as? [String: Any] {
            v.headerBottom = (d["bottom"] as? NSNumber)?.doubleValue ?? 0
            v.hits = ((d["hit"] as? [[NSNumber]]) ?? []).compactMap { r in
                r.count == 4 ? CGRect(x: r[0].doubleValue, y: r[1].doubleValue, width: r[2].doubleValue, height: r[3].doubleValue) : nil }
            return
        }
        guard m.name == "spyhopCopy", let t = m.body as? String else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(t, forType: .string)
    }

    // target="_blank" (릴리즈 노트 링크 등) 은 앱 안이 아니라 기본 브라우저로
    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction, windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url, let s = u.scheme, ["http", "https", "mailto"].contains(s) { NSWorkspace.shared.open(u) }
        return nil
    }

    // 보드 밖 주소로는 앱 창이 넘어가지 않는다. 사람이 누른 http(s)·메일 링크만 기본 앱으로 열고 나머지는 막는다
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let u = a.request.url, !Self.trusted(u) else { return decisionHandler(.allow) }
        if a.navigationType == .linkActivated, let s = u.scheme, ["http", "https", "mailto"].contains(s) { NSWorkspace.shared.open(u) }
        decisionHandler(.cancel)
    }

    /// 창에 붙은 시트로 띄운다(창이 없으면 따로 띄움)
    private func present(_ a: NSAlert, in w: WKWebView, _ done: @escaping (NSApplication.ModalResponse) -> Void) {
        if let win = w.window, win.isVisible, !(win is NSPanel) {
            a.beginSheetModal(for: win, completionHandler: done)
        } else {
            done(a.runModal())
        }
    }

    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert()
        a.messageText = m
        present(a, in: w) { _ in completionHandler() }
    }

    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert()
        a.messageText = m
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: "Cancel")
        present(a, in: w) { completionHandler($0 == .alertFirstButtonReturn) }
    }

    func webView(_ w: WKWebView, runJavaScriptTextInputPanelWithPrompt p: String, defaultText d: String?, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert()
        a.messageText = p
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24))
        field.stringValue = d ?? ""
        a.accessoryView = field
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: "Cancel")
        present(a, in: w) { completionHandler($0 == .alertFirstButtonReturn ? field.stringValue : nil) }
    }

    /// 창·패널을 닫을 때 웹 화면을 다 쓰고 놓는다. 그냥 떼어 내면 WebKit 이 웹 화면 프로세스를 다음에 쓰려고 그대로 들고 있다
    /// (창을 닫고 30분 넘게 94MB 가 남는 것을 실측). 브라우저 탭을 닫으면 그 탭 프로세스가 내려가는 것과 같게 한다
    func release(_ v: WKWebView) {
        v.navigationDelegate = nil  // 내리는 것을 「뜻밖에 죽음」으로 보고 다시 불러오지 않게
        v.uiDelegate = nil
        v.stopLoading()
        v.configuration.userContentController.removeAllScriptMessageHandlers()
        let close = NSSelectorFromString("_close")
        if v.responds(to: close) { v.perform(close) }
        v.removeFromSuperview()
    }

    // 웹 화면 프로세스가 죽으면(메모리 압박 등) 다시 불러온다
    func webViewWebContentProcessDidTerminate(_ w: WKWebView) {
        w.reload()
    }
}

/// WKUserContentController 가 처리기를 강하게 잡아 생기는 순환 참조를 끊는다
final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ t: WKScriptMessageHandler) { target = t }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        target?.userContentController(c, didReceive: m)
    }
}

/// 보드 창의 웹 화면. 헤더에서 버튼·탭이 아닌 빈 곳을 누르면 웹 대신 창이 받아 끌기·두 번 눌러 확대를 한다(맥 제목줄처럼)
final class BoardWebView: WKWebView {
    var headerBottom = 0.0   // 헤더 아래 끝(CSS 픽셀, 위에서부터)
    var hits: [CGRect] = []  // 헤더 안 누를 수 있는 것들의 자리(CSS 픽셀)

    /// 헤더의 빈 곳(창을 끄는 자리)인가
    private func inDragArea(_ e: NSEvent) -> Bool {
        let p = convert(e.locationInWindow, from: nil)
        let z = pageZoom > 0 ? pageZoom : 1
        let pt = CGPoint(x: p.x / z, y: (isFlipped ? p.y : bounds.height - p.y) / z)
        return pt.y < headerBottom && !hits.contains(where: { $0.insetBy(dx: -2, dy: -2).contains(pt) })
    }

    // 다른 앱이 앞에 있어도 제목줄처럼 첫 클릭으로 바로 끌 수 있게
    override func acceptsFirstMouse(for e: NSEvent?) -> Bool {
        if let e, inDragArea(e) { return true }
        return super.acceptsFirstMouse(for: e)
    }

    override func mouseDown(with e: NSEvent) {
        guard let w = window, inDragArea(e) else { return super.mouseDown(with: e) }
        if e.clickCount == 2 {
            switch UserDefaults.standard.string(forKey: "AppleActionOnDoubleClick") {
            case "Minimize": w.performMiniaturize(nil)
            case "None": break
            default: w.performZoom(nil)
            }
        } else {
            w.performDrag(with: e)
        }
    }
}


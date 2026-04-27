import sys
import os
import socket
import threading
import json
import urllib.request
from urllib.parse import urlparse

# Configurar flags de Chromium ANTES de importar PyQt
# (deben estar en el entorno antes de que Chromium arranque)
stealth_flags = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=ChromeWhatsNewUI",
    "--disable-web-security",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--renderer-process-limit=2",
    "--js-flags=--max-old-space-size=128",
    "--enable-webgl",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--disable-reading-from-canvas=false",
    "--force-color-profile=srgb",
]
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(stealth_flags)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineSettings, QWebEngineScript
)
from PyQt6.QtCore import QUrl, QTimer, Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QFont, QColor
from PyQt6.QtNetwork import QNetworkProxy

from Correos import CORREOS_URL
from correos_gmail import GMAIL_URL
from MercadoSalud import MERCADOSALUD_URL
from browser_identity import generate_browser_identity, generate_spoof_js

ARCHIVO_PROXIES = "proxies_buenos.txt"

# ⚠️ DEPRECADO: CHROME_USER_AGENT y CHROME_SPOOF_JS (debajo) ya NO se usan.
# Ahora cada pestaña genera su propia identidad de navegador única
# mediante browser_identity.generate_browser_identity()
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# JavaScript que se inyecta ANTES de que cargue cualquier página
# para enmascarar QWebEngineView como un Chrome real
CHROME_SPOOF_JS = """
(function() {
    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 1: Identidad del navegador (UserAgentData + webdriver)
    // ═══════════════════════════════════════════════════════════
    Object.defineProperty(navigator, 'userAgentData', {
        get: function() {
            return {
                brands: [
                    { brand: "Google Chrome", version: "131" },
                    { brand: "Chromium", version: "131" },
                    { brand: "Not_A Brand", version: "24" }
                ],
                mobile: false,
                platform: "Windows",
                getHighEntropyValues: function(hints) {
                    return Promise.resolve({
                        brands: [
                            { brand: "Google Chrome", version: "131" },
                            { brand: "Chromium", version: "131" },
                            { brand: "Not_A Brand", version: "24" }
                        ],
                        mobile: false,
                        platform: "Windows",
                        platformVersion: "10.0.0",
                        architecture: "x86",
                        bitness: "64",
                        model: "",
                        uaFullVersion: "131.0.0.0",
                        fullVersionList: [
                            { brand: "Google Chrome", version: "131.0.6778.86" },
                            { brand: "Chromium", version: "131.0.6778.86" },
                            { brand: "Not_A Brand", version: "24.0.0.0" }
                        ]
                    });
                },
                toJSON: function() {
                    return {
                        brands: this.brands,
                        mobile: this.mobile,
                        platform: this.platform
                    };
                }
            };
        },
        configurable: true
    });

    Object.defineProperty(navigator, 'webdriver', {
        get: function() { return undefined; },
        configurable: true
    });

    Object.defineProperty(navigator, 'languages', {
        get: function() { return ['en-US', 'en']; },
        configurable: true
    });

    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: function() { return 8; },
        configurable: true
    });

    Object.defineProperty(navigator, 'deviceMemory', {
        get: function() { return 8; },
        configurable: true
    });

    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: function() { return 0; },
        configurable: true
    });

    Object.defineProperty(navigator, 'plugins', {
        get: function() {
            var p = [
                { name: "PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format", length: 1 },
                { name: "Chrome PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 },
                { name: "Chromium PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 },
                { name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 },
                { name: "WebKit built-in PDF", filename: "internal-pdf-viewer", description: "", length: 1 }
            ];
            p.length = 5;
            return p;
        },
        configurable: true
    });

    Object.defineProperty(navigator, 'mimeTypes', {
        get: function() {
            var m = [
                { type: "application/pdf", suffixes: "pdf", description: "Portable Document Format" },
                { type: "text/pdf", suffixes: "pdf", description: "Portable Document Format" }
            ];
            m.length = 2;
            return m;
        },
        configurable: true
    });

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 2: Eliminar rastros de Qt / WebEngine
    // ═══════════════════════════════════════════════════════════
    try { delete window.qt; } catch(e) {}
    try { delete window.__qtWebEngine; } catch(e) {}
    try { delete window.QWebChannel; } catch(e) {}
    try { Object.defineProperty(window, 'qt', { get: function() { return undefined; }, configurable: true }); } catch(e) {}
    try { Object.defineProperty(window, '__qtWebEngine', { get: function() { return undefined; }, configurable: true }); } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 3: WebGL Spoofing (v1 + v2)
    // ═══════════════════════════════════════════════════════════
    try {
        var cards = [
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (AMD, AMD Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"
        ];
        // Elegir UNA sola tarjeta por sesion para mantener consistencia interna
        var chosenCard = cards[Math.floor(Math.random() * cards.length)];

        function patchGetParameter(proto) {
            var original = proto.getParameter;
            proto.getParameter = function(param) {
                if (param === 37445) return "Google Inc. (NVIDIA)";
                if (param === 37446) return chosenCard;
                return original.apply(this, arguments);
            };
        }
        patchGetParameter(WebGLRenderingContext.prototype);
        if (typeof WebGL2RenderingContext !== 'undefined') {
            patchGetParameter(WebGL2RenderingContext.prototype);
        }
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 4: Canvas Fingerprint Noise
    // ═══════════════════════════════════════════════════════════
    try {
        var origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        var origToBlob = HTMLCanvasElement.prototype.toBlob;
        var origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        var noiseSeed = Math.random();

        HTMLCanvasElement.prototype.toDataURL = function() {
            try {
                var ctx = this.getContext('2d');
                if (ctx) {
                    var r = Math.floor(noiseSeed * 10) % 256;
                    var g = Math.floor(noiseSeed * 100) % 256;
                    ctx.fillStyle = 'rgba(' + r + ',' + g + ',0,0.01)';
                    ctx.fillRect(0, 0, 1, 1);
                }
                return origToDataURL.apply(this, arguments);
            } catch(e) {
                // Canvas tainted por contenido cross-origin: devolver un data URL falso unico
                return 'data:image/png;base64,iVBOR' + Math.random().toString(36).substring(2);
            }
        };

        HTMLCanvasElement.prototype.toBlob = function() {
            try {
                var ctx = this.getContext('2d');
                if (ctx) {
                    var r = Math.floor(noiseSeed * 10) % 256;
                    var g = Math.floor(noiseSeed * 100) % 256;
                    ctx.fillStyle = 'rgba(' + r + ',' + g + ',0,0.01)';
                    ctx.fillRect(0, 0, 1, 1);
                }
                return origToBlob.apply(this, arguments);
            } catch(e) {
                // Tainted canvas: invocar callback con un blob vacio
                var cb = arguments[0];
                if (typeof cb === 'function') cb(new Blob([], {type: 'image/png'}));
            }
        };

        CanvasRenderingContext2D.prototype.getImageData = function() {
            try {
                var imageData = origGetImageData.apply(this, arguments);
                for (var i = 0; i < Math.min(imageData.data.length, 40); i += 4) {
                    imageData.data[i] = imageData.data[i] ^ (Math.floor(noiseSeed * (i+1)) & 1);
                }
                return imageData;
            } catch(e) {
                // Tainted: devolver ImageData vacio del tamano solicitado
                var w = arguments[2] || 1, h = arguments[3] || 1;
                return new ImageData(w, h);
            }
        };
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 5: AudioContext Fingerprint Noise
    // ═══════════════════════════════════════════════════════════
    try {
        var origGetFloatFreqData = AnalyserNode.prototype.getFloatFrequencyData;
        AnalyserNode.prototype.getFloatFrequencyData = function(array) {
            origGetFloatFreqData.apply(this, arguments);
            for (var i = 0; i < array.length; i++) {
                array[i] = array[i] + (Math.random() * 0.0001 - 0.00005);
            }
        };
        var origCreateOsc = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {
            var osc = origCreateOsc.apply(this, arguments);
            osc.__noise = Math.random() * 0.00001;
            return osc;
        };
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 6: ClientRects / Element Size Jitter
    // ═══════════════════════════════════════════════════════════
    try {
        var origGetClientRects = Element.prototype.getClientRects;
        var origGetBCR = Element.prototype.getBoundingClientRect;
        var rectNoise = (Math.random() - 0.5) * 0.25;

        Element.prototype.getClientRects = function() {
            var rects = origGetClientRects.apply(this, arguments);
            var result = [];
            for (var i = 0; i < rects.length; i++) {
                result.push(new DOMRect(
                    rects[i].x + rectNoise,
                    rects[i].y + rectNoise,
                    rects[i].width + rectNoise,
                    rects[i].height + rectNoise
                ));
            }
            return result;
        };

        Element.prototype.getBoundingClientRect = function() {
            var rect = origGetBCR.apply(this, arguments);
            return new DOMRect(
                rect.x + rectNoise,
                rect.y + rectNoise,
                rect.width + rectNoise,
                rect.height + rectNoise
            );
        };
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 7: Screen Resolution Spoofing (Consistente con una PC comun)
    // ═══════════════════════════════════════════════════════════
    try {
        var screens = [
            {w: 1920, h: 1080, aw: 1920, ah: 1040},
            {w: 1366, h: 768, aw: 1366, ah: 728},
            {w: 1536, h: 864, aw: 1536, ah: 824},
            {w: 1440, h: 900, aw: 1440, ah: 860}
        ];
        var chosen = screens[Math.floor(Math.random() * screens.length)];
        Object.defineProperty(screen, 'width', { get: function() { return chosen.w; } });
        Object.defineProperty(screen, 'height', { get: function() { return chosen.h; } });
        Object.defineProperty(screen, 'availWidth', { get: function() { return chosen.aw; } });
        Object.defineProperty(screen, 'availHeight', { get: function() { return chosen.ah; } });
        Object.defineProperty(screen, 'colorDepth', { get: function() { return 24; } });
        Object.defineProperty(screen, 'pixelDepth', { get: function() { return 24; } });
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 8: Timezone Normalizar a US/Eastern (MercadoSalud es de USA)
    // ═══════════════════════════════════════════════════════════
    try {
        var origDTF = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function() {
            var args = Array.from(arguments);
            if (!args[1]) args[1] = {};
            if (!args[1].timeZone) args[1].timeZone = 'America/New_York';
            return new origDTF(args[0], args[1]);
        };
        Intl.DateTimeFormat.prototype = origDTF.prototype;
        Intl.DateTimeFormat.supportedLocalesOf = origDTF.supportedLocalesOf;

        var origResolvedOptions = origDTF.prototype.resolvedOptions;
        origDTF.prototype.resolvedOptions = function() {
            var opts = origResolvedOptions.apply(this, arguments);
            opts.timeZone = 'America/New_York';
            return opts;
        };

        var origGetTZO = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {
            return 300; // UTC-5 = Eastern Standard Time
        };
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 9: WebRTC IP Leak Prevention
    // ═══════════════════════════════════════════════════════════
    try {
        var origRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {
            if (config && config.iceServers) {
                config.iceServers = [];
            }
            return new origRTC(config);
        };
        window.RTCPeerConnection.prototype = origRTC.prototype;
        // Tambien parchar webkitRTCPeerConnection
        if (window.webkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = window.RTCPeerConnection;
        }
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 10: Ocultar APIs exoticas que revelan automatizacion
    // ═══════════════════════════════════════════════════════════
    try {
        // Permissions API: siempre devolver 'prompt' (como un Chrome real)
        var origQuery = navigator.permissions.query;
        navigator.permissions.query = function(desc) {
            if (desc.name === 'notifications') {
                return Promise.resolve({ state: 'prompt', onchange: null });
            }
            return origQuery.apply(this, arguments);
        };
    } catch(e) {}

    try {
        // Battery API: devolver bateria cargada simulada
        if (navigator.getBattery) {
            navigator.getBattery = function() {
                return Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1.0,
                    addEventListener: function() {},
                    removeEventListener: function() {}
                });
            };
        }
    } catch(e) {}

    try {
        // Bluetooth: no disponible en Chrome desktop real
        if (navigator.bluetooth) {
            Object.defineProperty(navigator, 'bluetooth', {
                get: function() { return undefined; },
                configurable: true
            });
        }
    } catch(e) {}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 11: Prevenir deteccion via window.chrome
    // ═══════════════════════════════════════════════════════════
    try {
        if (!window.chrome) {
            window.chrome = {
                runtime: {
                    onMessage: { addListener: function() {}, removeListener: function() {} },
                    sendMessage: function() {},
                    connect: function() { return { onMessage: { addListener: function() {} } }; }
                },
                loadTimes: function() {
                    return {
                        requestTime: Date.now() / 1000,
                        startLoadTime: Date.now() / 1000,
                        commitLoadTime: Date.now() / 1000 + 0.3,
                        finishDocumentLoadTime: Date.now() / 1000 + 0.5,
                        finishLoadTime: Date.now() / 1000 + 0.7,
                        firstPaintTime: Date.now() / 1000 + 0.1,
                        firstPaintAfterLoadTime: 0,
                        navigationType: "Other",
                        wasFetchedViaSpdy: true,
                        wasNpnNegotiated: true,
                        npnNegotiatedProtocol: "h2",
                        wasAlternateProtocolAvailable: false,
                        connectionInfo: "h2"
                    };
                },
                csi: function() { return { pageT: Date.now() }; },
                app: { isInstalled: false, getDetails: function() { return null; }, getIsInstalled: function() { return false; }, runningState: function() { return 'cannot_run'; } }
            };
        }
    } catch(e) {}

})();
"""


# ══════════════════════════════════════════════════════════════
#   Señal auxiliar para comunicar el hilo de búsqueda → GUI
# ══════════════════════════════════════════════════════════════

class _ProxyFoundSignal(QObject):
    found = pyqtSignal(str)   # emite la URL del proxy válido
    status = pyqtSignal(str)  # emite mensajes de progreso


# ══════════════════════════════════════════════════════════════
#   PANTALLA DE CARGA – busca un proxy vivo antes de abrir app
# ══════════════════════════════════════════════════════════════

class LoadingScreen(QWidget):
    """Pantalla de carga que prueba proxies hasta encontrar uno activo.
    Una vez encontrado, emite `proxy_ready` con la URL del proxy."""

    proxy_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Centralizador – Conectando…")
        self.setFixedSize(520, 340)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e
                );
            }
        """)
        # Centrar en pantalla
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        # Título
        title = QLabel("🛡️  Programa Centralizador")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # Ícono animado de puntos
        self._dots = 0
        self.lbl_status = QLabel("🔍 Buscando una IP de proxy válida")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #a29bfe; font-size: 15px;")
        layout.addWidget(self.lbl_status)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detail.setStyleSheet("color: #636e72; font-size: 12px;")
        layout.addWidget(self.lbl_detail)

        layout.addStretch()

        # Firma
        footer = QLabel("Made by Alfred Varela for Empire")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #636e72; font-size: 10px;")
        layout.addWidget(footer)

        # Señales del hilo
        self._signal = _ProxyFoundSignal()
        self._signal.found.connect(self._on_proxy_found)
        self._signal.status.connect(self._on_status_update)

        # Animación de puntos
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start(500)

        # Lanzar búsqueda en hilo background
        threading.Thread(target=self._search_proxy, daemon=True).start()

    # ── Animación de puntos ──
    def _animate_dots(self):
        self._dots = (self._dots + 1) % 4
        dots = "." * self._dots
        base = self.lbl_status.text().rstrip(".")
        # Mantener el texto base sin puntos extra
        if "Buscando" in base or "Probando" in base:
            clean = base.split("…")[0].split("...")[0].rstrip(". ")
            self.lbl_status.setText(f"{clean}{'.' * self._dots}")

    # ── Hilo de búsqueda ──
    def _search_proxy(self):
        """Prueba proxies del servidor Flask iterativamente hasta encontrar uno vivo."""
        import time

        idx = 0
        while True:
            # Pedimos la lista al servidor en todo momento para asegurar que esté fresca
            proxy_list = _cargar_lista_proxies()
            
            if not proxy_list:
                self._signal.status.emit("⚠️ Esperando que el servidor entregue proxies...")
                time.sleep(2)
                continue

            # Ajustamos el índice si la lista cambió de tamaño
            if idx >= len(proxy_list):
                idx = 0

            proxy = proxy_list[idx]
            
            parsed = urlparse(proxy)
            host = parsed.hostname
            port = parsed.port or 80
            
            display_ip = f"{host}:{port}"
            self._signal.status.emit(f"🔍 Probando {display_ip}")
            
            try:
                sock = socket.create_connection((host, port), timeout=3)
                sock.close()
                print(f"[LoadingScreen] Proxy encontrado: {display_ip}")
                self._signal.found.emit(proxy)
                return
            except Exception as e:
                print(f"[LoadingScreen] Falló {display_ip}: {e}")

            # Si falla, pasamos a la siguiente IP
            idx = (idx + 1) % len(proxy_list)
            time.sleep(0.5)

    # ── Slots ──
    def _on_status_update(self, msg):
        self.lbl_detail.setText(msg)

    def _on_proxy_found(self, proxy_url):
        self._dot_timer.stop()
        self.lbl_status.setText("✅ ¡Proxy encontrado!")
        self.lbl_status.setStyleSheet("color: #00b894; font-size: 15px; font-weight: bold;")
        
        parsed = urlparse(proxy_url)
        display_ip = f"{parsed.hostname}:{parsed.port}" if parsed.hostname else proxy_url
        self.lbl_detail.setText(display_ip)
        
        # Pequeña pausa visual y luego emitir señal
        QTimer.singleShot(800, lambda: self.proxy_ready.emit(proxy_url))


class VerticalLabel(QLabel):
    """Etiqueta que dibuja su texto rotado 90 grados hacia arriba,
    ideal para ocupar el espacio vertical de la barra de pestañas."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Asignamos la fuente pequeña desde el inicio para que sizeHint funcione bien
        font = self.font()
        font.setPointSize(8) # Tamaño pequeño para que no ensanche la barra
        self.setFont(font)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        text_height = fm.height() 
        
        # Centrar matemáticamente el texto rotado -90 grados
        # X: Centro del widget + la mitad de la altura de la fuente (compensando la línea base)
        # Y: Centro del widget + la mitad del largo del texto
        x = (self.width() + text_height) / 2 - fm.descent()
        y = (self.height() + text_width) / 2
        
        painter.translate(x, y)
        painter.rotate(-90)
        
        painter.drawText(0, 0, self.text())
        painter.end()
        
    def sizeHint(self):
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        text_height = fm.height()
        # El ancho del widget será exactamente la altura de la fuente, minimizando su grosor
        return QSize(text_height, text_width)


def format_display_proxy(proxy_url):
    """Devuelve solo host:port para visualización (ocultando usuario/clave)."""
    try:
        if not proxy_url: return ""
        parsed = urlparse(proxy_url)
        return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    except:
        return proxy_url


def apply_proxy(proxy_url):
    """Aplica un proxy HTTP a nivel de toda la aplicación Qt, soportando credenciales."""
    parsed = urlparse(proxy_url)
    
    proxy = QNetworkProxy()
    proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
    proxy.setHostName(parsed.hostname)
    # Evitar None en el puerto
    proxy.setPort(parsed.port or 80)
    
    # Inyectar usuario y contraseña si el proxy los requiere
    if parsed.username and parsed.password:
        proxy.setUser(parsed.username)
        proxy.setPassword(parsed.password)
        
    QNetworkProxy.setApplicationProxy(proxy)


def create_spoof_script(js_code):
    """Crea un QWebEngineScript que inyecta el JS de spoofing
    antes de que cualquier script de la página se ejecute."""
    script = QWebEngineScript()
    script.setName("chrome_spoof")
    script.setSourceCode(js_code)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(True)
    return script


def configure_profile(profile, identity):
    """Configura un perfil con la identidad de navegador única proporcionada.
    Cada perfil obtiene un User-Agent y JS de spoofing diferente."""
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
    profile.setHttpUserAgent(identity["user_agent"])
    js_code = generate_spoof_js(identity)
    profile.scripts().insert(create_spoof_script(js_code))


def create_webview(profile):
    """Crea un QWebEngineView con configuración optimizada."""
    
    class SilentWebEnginePage(QWebEnginePage):
        def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
            pass # Silencia las advertencias JS de las webs (como preloads de fuentes, etc)
            
    view = QWebEngineView()
    page = SilentWebEnginePage(profile, view)
    view.setPage(page)

    settings = view.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
    # Optimizaciones de memoria
    settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

    return view


class LazyTab(QWidget):
    """Widget de pestaña que carga la página web solo cuando se hace visible.
    Esto ahorra ~200-400MB de RAM por cada pestaña no utilizada."""

    def __init__(self, profile, url, identity, parent=None):
        super().__init__(parent)
        self._profile = profile
        self._url = url
        self._identity = identity
        self._loaded = False
        self._view = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder mientras no se carga
        self._placeholder = QLabel("Haz clic en esta pestaña para cargar...")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("font-size: 16px; color: #888;")
        self._layout.addWidget(self._placeholder)

    def load_if_needed(self):
        """Carga la página solo si no ha sido cargada antes."""
        if self._loaded:
            return
        self._loaded = True
        self._placeholder.hide()

        self._view = create_webview(self._profile)
        self._view.setUrl(QUrl(self._url))
        self._layout.addWidget(self._view)

    def unload(self):
        """Descarga la página para liberar memoria (opcional, para uso futuro)."""
        if not self._loaded or self._view is None:
            return
        self._view.setUrl(QUrl("about:blank"))
        self._view.deleteLater()
        self._view = None
        self._loaded = False
        self._placeholder.show()

    def reset_profile_completely(self, parent_window):
        """Para lograr 100% de aislamiento (cero rastreadores IndexedDB o Caché oculto),
        destruye físicamente la vista y su perfil en memoria y los reconstruye vírgenes.
        Genera una NUEVA identidad de navegador para simular un navegador completamente nuevo."""
        self.unload()
        if self._profile:
            self._profile.deleteLater()

        # Generar nueva identidad aleatoria (nuevo "navegador")
        self._identity = generate_browser_identity()

        self._profile = QWebEngineProfile(parent_window)
        configure_profile(self._profile, self._identity)


def _cargar_lista_proxies():
    """Obtiene la lista de proxies de los servidores locales Flask en tiempo real."""
    urls = [
        "http://10.161.146.235:5000/proxies",
        "http://10.0.0.217:5000/proxies",
        "http://10.0.0.4:5000/proxies"
    ]
    proxies = []
    for url in urls:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                proxies.extend(data.get("proxies", []))
        except Exception as e:
            print(f"Error al obtener proxies del servidor {url}: {e}")
            
    # Retornar eliminando posibles duplicados y manteniendo el orden original
    return list(dict.fromkeys(proxies))


class CentralWindow(QMainWindow):
    def __init__(self, initial_proxy):
        super().__init__()
        self.setWindowTitle("Programa Centralizador - Web Integrado")
        self.resize(1200, 700)

        # Lista de proxies buenos y índice de rotación
        self._proxy_list = _cargar_lista_proxies()
        self._proxy_index = 0
        # Avanzar el índice más allá del proxy inicial para no repetirlo
        if initial_proxy in self._proxy_list:
            self._proxy_index = (self._proxy_list.index(initial_proxy) + 1) % len(self._proxy_list)

        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Barra superior con botón de forzar rotación
        top_bar = QHBoxLayout()
        
        display_initial = format_display_proxy(initial_proxy)
        self.lbl_ip_activa = QLabel(f"🌐 IP Activa: {display_initial}")
        self.lbl_ip_activa.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        top_bar.addWidget(self.lbl_ip_activa)
        
        top_bar.addStretch()
        
        self.btn_rotar_proxy = QPushButton("🔄 Rotar Proxy y Refrescar Pestaña")
        self.btn_rotar_proxy.setStyleSheet("""
            QPushButton {
                background-color: #e67e22; 
                color: white; 
                font-size: 14px;
                font-weight: bold; 
                padding: 10px 20px; 
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        self.btn_rotar_proxy.clicked.connect(self._rotar_proxy_manual)
        
        top_bar.addStretch()
        top_bar.addWidget(self.btn_rotar_proxy)
        layout.addLayout(top_bar)

        # Tab Widget nativo
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        layout.addWidget(self.tab_widget)

        # Etiqueta sobrepuesta que no afecta el diseño de los tabs
        self.label_autor = VerticalLabel("Made by Alfred Varela for Empire", self.tab_widget)
        self.label_autor.setStyleSheet("color: black; background: transparent;")

        # Configurar proxy inicial (ya validado por la pantalla de carga)
        apply_proxy(initial_proxy)
        self._current_applied_proxy = initial_proxy

        # ── Identidades únicas por pestaña (cada una simula un navegador diferente) ──
        self.identity_correos = generate_browser_identity()
        self.identity_gmail = generate_browser_identity()
        self.identity_mercadosalud = generate_browser_identity()

        print(f"[Identidad Correos]  Chrome/{self.identity_correos['chrome_major']}  "
              f"GPU: {self.identity_correos['gpu_renderer'][:40]}...  "
              f"Screen: {self.identity_correos['screen_w']}x{self.identity_correos['screen_h']}")
        print(f"[Identidad Gmail]    Chrome/{self.identity_gmail['chrome_major']}  "
              f"GPU: {self.identity_gmail['gpu_renderer'][:40]}...  "
              f"Screen: {self.identity_gmail['screen_w']}x{self.identity_gmail['screen_h']}")
        print(f"[Identidad MdSalud]  Chrome/{self.identity_mercadosalud['chrome_major']}  "
              f"GPU: {self.identity_mercadosalud['gpu_renderer'][:40]}...  "
              f"Screen: {self.identity_mercadosalud['screen_w']}x{self.identity_mercadosalud['screen_h']}")

        # ── Crear perfiles incógnito con identidades diferentes ──
        self.profile_correos = QWebEngineProfile(self)
        configure_profile(self.profile_correos, self.identity_correos)

        self.profile_gmail = QWebEngineProfile(self)
        configure_profile(self.profile_gmail, self.identity_gmail)

        self.profile_mercadosalud = QWebEngineProfile(self)
        configure_profile(self.profile_mercadosalud, self.identity_mercadosalud)

        # ── Pestañas con carga perezosa y su identidad asociada ──
        self.tab_correos = LazyTab(self.profile_correos, CORREOS_URL, self.identity_correos)
        self.tab_gmail = LazyTab(self.profile_gmail, GMAIL_URL, self.identity_gmail)
        self.tab_mercadosalud = LazyTab(self.profile_mercadosalud, MERCADOSALUD_URL, self.identity_mercadosalud)

        self.tab_widget.addTab(self.tab_correos, "Correos Outlook")
        self.tab_widget.addTab(self.tab_gmail, "Correos Gmail")
        self.tab_widget.addTab(self.tab_mercadosalud, "MercadoSalud")

        # Cargar la primera pestaña inmediatamente
        self.tab_correos.load_if_needed()

        # Conectar cambio de pestaña
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        """Carga la pestaña solo cuando el usuario la selecciona."""
        tab = self.tab_widget.widget(index)
        if isinstance(tab, LazyTab):
            tab.load_if_needed()
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Posición absoluta: exactamente en el "bottom" (sin restarle píxeles)
        x_pos = 2
        y_pos = self.tab_widget.height() - self.label_autor.height()
        self.label_autor.move(x_pos, y_pos)

    def _rotar_proxy_manual(self):
        """Toma el siguiente proxy consultando al servidor Flask y lo aplica."""
        # Recargar la lista en tiempo real
        self._proxy_list = _cargar_lista_proxies()

        if not self._proxy_list:
            self.lbl_ip_activa.setText("⚠️ No hay proxies disponibles en el servidor")
            return
            
        self.btn_rotar_proxy.setEnabled(False)
        
        # Ajustar el índice si la lista se redujo
        if self._proxy_index >= len(self._proxy_list):
            self._proxy_index = 0

        new_proxy = self._proxy_list[self._proxy_index]
        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_list)
        
        self._apply_global_rotation(new_proxy)
        
        display_new = format_display_proxy(new_proxy)
        self.lbl_ip_activa.setText(f"🌐 IP Activa: {display_new}")
        self.btn_rotar_proxy.setText(f"✅ ¡Rotado! ({self._proxy_index}/{len(self._proxy_list)})")
        
        def restaurar_boton():
            self.btn_rotar_proxy.setText("🔄 Rotar Proxy y Refrescar Pestaña")
            self.btn_rotar_proxy.setEnabled(True)
            
        QTimer.singleShot(2500, restaurar_boton)

    def _apply_global_rotation(self, new_proxy):
        """Aplica proxy matando conexiones viejas antes de recargar.
        
        Flujo: about:blank → purgar → nuevo proxy → esperar → recargar URLs reales.
        Esto evita que WebEngine intente reusar conexiones TCP del proxy anterior."""
        if not new_proxy:
            return
        
        tabs = [self.tab_correos, self.tab_gmail, self.tab_mercadosalud]
        previously_loaded = [tab for tab in tabs if getattr(tab, "_loaded", False)]

        # PASO 1: Destrucción nuclear del Sandbox de esta sesión.
        # Esto nos asegura borrar Cookies, LocalStorage, IndexedDB y tokens ocultos.
        for tab in tabs:
            tab.reset_profile_completely(self)
        
        # PASO 2: Aplicar el nuevo proxy a nivel sistema
        apply_proxy(new_proxy)
        self._current_applied_proxy = new_proxy
        
        # PASO 3: Esperar 700ms para asegurar la destrucción en memoria C++
        #         y luego recargar las pestañas que estaban activas.
        def _recargar_urls():
            for tab in previously_loaded:
                tab.load_if_needed()
        
        QTimer.singleShot(700, _recargar_urls)

    def closeEvent(self, event):
        event.accept()


if __name__ == "__main__":


    app = QApplication(sys.argv)

    # ── PASO 1: Mostrar pantalla de carga y buscar proxy ──
    loading = LoadingScreen()
    loading.show()

    def on_proxy_ready(proxy_url):
        """Callback: proxy encontrado → cerrar loading y abrir ventana principal."""
        loading.close()
        # ── PASO 2: Abrir ventana principal con el proxy ya validado ──
        window = CentralWindow(proxy_url)
        window.show()
        # Guardar referencia para que no se destruya por garbage collector
        app._main_window = window

    loading.proxy_ready.connect(on_proxy_ready)

    sys.exit(app.exec())

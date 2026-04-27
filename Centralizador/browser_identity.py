"""browser_identity.py – Genera identidades de navegador únicas por pestaña.

Cada llamada a generate_browser_identity() devuelve un diccionario con valores
aleatorios pero internamente consistentes (misma versión de Chrome en UA y
userAgentData, misma GPU en WebGL v1 y v2, etc.).

generate_spoof_js(identity) convierte esa identidad en un bloque de JavaScript
listo para inyectar con QWebEngineScript.
"""

import random
import hashlib


# ══════════════════════════════════════════════════════════════
#   Pools de datos realistas para aleatorizar
# ══════════════════════════════════════════════════════════════

_CHROME_VERSIONS = [
    {"major": "120", "full": "120.0.6099.130"},
    {"major": "121", "full": "121.0.6167.85"},
    {"major": "122", "full": "122.0.6261.112"},
    {"major": "123", "full": "123.0.6312.86"},
    {"major": "124", "full": "124.0.6367.91"},
    {"major": "125", "full": "125.0.6422.76"},
    {"major": "126", "full": "126.0.6478.114"},
    {"major": "127", "full": "127.0.6533.72"},
    {"major": "128", "full": "128.0.6613.85"},
    {"major": "129", "full": "129.0.6668.59"},
    {"major": "130", "full": "130.0.6723.70"},
    {"major": "131", "full": "131.0.6778.86"},
]

_GPU_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
]

_GPU_VENDORS = {
    "NVIDIA": "Google Inc. (NVIDIA)",
    "Intel": "Google Inc. (Intel)",
    "AMD": "Google Inc. (AMD)",
}

_SCREENS = [
    {"w": 1920, "h": 1080, "aw": 1920, "ah": 1040},
    {"w": 1366, "h": 768, "aw": 1366, "ah": 728},
    {"w": 1536, "h": 864, "aw": 1536, "ah": 824},
    {"w": 1440, "h": 900, "aw": 1440, "ah": 860},
    {"w": 2560, "h": 1440, "aw": 2560, "ah": 1400},
    {"w": 1600, "h": 900, "aw": 1600, "ah": 860},
    {"w": 1680, "h": 1050, "aw": 1680, "ah": 1010},
]

_HW_CONCURRENCY = [4, 6, 8, 12, 16]
_DEVICE_MEMORY = [4, 8, 16, 32]
_PLATFORM_VERSIONS = ["10.0.0", "15.0.0", "14.0.0"]


def _extract_gpu_vendor(renderer: str) -> str:
    """Extrae la marca de GPU del string del renderer para derivar el vendor."""
    for brand in ("NVIDIA", "AMD", "Intel"):
        if brand in renderer:
            return _GPU_VENDORS[brand]
    return "Google Inc. (NVIDIA)"


def generate_browser_identity() -> dict:
    """Genera una identidad de navegador completamente aleatoria pero internamente
    consistente. Devuelve un diccionario con todos los parámetros necesarios."""

    chrome = random.choice(_CHROME_VERSIONS)
    gpu = random.choice(_GPU_RENDERERS)
    screen = random.choice(_SCREENS)

    identity = {
        # Chrome version
        "chrome_major": chrome["major"],
        "chrome_full": chrome["full"],
        # User-Agent string
        "user_agent": (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome['full']} Safari/537.36"
        ),
        # GPU / WebGL
        "gpu_vendor": _extract_gpu_vendor(gpu),
        "gpu_renderer": gpu,
        # Screen
        "screen_w": screen["w"],
        "screen_h": screen["h"],
        "screen_aw": screen["aw"],
        "screen_ah": screen["ah"],
        # Hardware
        "hardware_concurrency": random.choice(_HW_CONCURRENCY),
        "device_memory": random.choice(_DEVICE_MEMORY),
        # Platform
        "platform_version": random.choice(_PLATFORM_VERSIONS),
        # Noise seeds (deterministas por identidad)
        "canvas_noise_seed": random.random(),
        "rect_noise": (random.random() - 0.5) * 0.25,
    }

    return identity


def generate_spoof_js(identity: dict) -> str:
    """Genera el JavaScript de spoofing parametrizado con los valores de la identidad.
    Este JS se inyecta ANTES de que cargue cualquier página."""

    chrome_major = identity["chrome_major"]
    chrome_full = identity["chrome_full"]
    gpu_vendor = identity["gpu_vendor"]
    gpu_renderer = identity["gpu_renderer"]
    screen_w = identity["screen_w"]
    screen_h = identity["screen_h"]
    screen_aw = identity["screen_aw"]
    screen_ah = identity["screen_ah"]
    hw_concurrency = identity["hardware_concurrency"]
    device_memory = identity["device_memory"]
    platform_version = identity["platform_version"]
    canvas_seed = identity["canvas_noise_seed"]
    rect_noise = identity["rect_noise"]

    return f"""(function() {{
    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 1: Identidad del navegador (UserAgentData + webdriver)
    // ═══════════════════════════════════════════════════════════
    Object.defineProperty(navigator, 'userAgentData', {{
        get: function() {{
            return {{
                brands: [
                    {{ brand: "Google Chrome", version: "{chrome_major}" }},
                    {{ brand: "Chromium", version: "{chrome_major}" }},
                    {{ brand: "Not_A Brand", version: "24" }}
                ],
                mobile: false,
                platform: "Windows",
                getHighEntropyValues: function(hints) {{
                    return Promise.resolve({{
                        brands: [
                            {{ brand: "Google Chrome", version: "{chrome_major}" }},
                            {{ brand: "Chromium", version: "{chrome_major}" }},
                            {{ brand: "Not_A Brand", version: "24" }}
                        ],
                        mobile: false,
                        platform: "Windows",
                        platformVersion: "{platform_version}",
                        architecture: "x86",
                        bitness: "64",
                        model: "",
                        uaFullVersion: "{chrome_full}",
                        fullVersionList: [
                            {{ brand: "Google Chrome", version: "{chrome_full}" }},
                            {{ brand: "Chromium", version: "{chrome_full}" }},
                            {{ brand: "Not_A Brand", version: "24.0.0.0" }}
                        ]
                    }});
                }},
                toJSON: function() {{
                    return {{
                        brands: this.brands,
                        mobile: this.mobile,
                        platform: this.platform
                    }};
                }}
            }};
        }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'webdriver', {{
        get: function() {{ return undefined; }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'languages', {{
        get: function() {{ return ['en-US', 'en']; }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: function() {{ return {hw_concurrency}; }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'deviceMemory', {{
        get: function() {{ return {device_memory}; }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: function() {{ return 0; }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'plugins', {{
        get: function() {{
            var p = [
                {{ name: "PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format", length: 1 }},
                {{ name: "Chrome PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 }},
                {{ name: "Chromium PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 }},
                {{ name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer", description: "", length: 1 }},
                {{ name: "WebKit built-in PDF", filename: "internal-pdf-viewer", description: "", length: 1 }}
            ];
            p.length = 5;
            return p;
        }},
        configurable: true
    }});

    Object.defineProperty(navigator, 'mimeTypes', {{
        get: function() {{
            var m = [
                {{ type: "application/pdf", suffixes: "pdf", description: "Portable Document Format" }},
                {{ type: "text/pdf", suffixes: "pdf", description: "Portable Document Format" }}
            ];
            m.length = 2;
            return m;
        }},
        configurable: true
    }});

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 2: Eliminar rastros de Qt / WebEngine
    // ═══════════════════════════════════════════════════════════
    try {{ delete window.qt; }} catch(e) {{}}
    try {{ delete window.__qtWebEngine; }} catch(e) {{}}
    try {{ delete window.QWebChannel; }} catch(e) {{}}
    try {{ Object.defineProperty(window, 'qt', {{ get: function() {{ return undefined; }}, configurable: true }}); }} catch(e) {{}}
    try {{ Object.defineProperty(window, '__qtWebEngine', {{ get: function() {{ return undefined; }}, configurable: true }}); }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 3: WebGL Spoofing (v1 + v2)
    // ═══════════════════════════════════════════════════════════
    try {{
        var gpuVendor = "{gpu_vendor}";
        var gpuRenderer = "{gpu_renderer}";

        function patchGetParameter(proto) {{
            var original = proto.getParameter;
            proto.getParameter = function(param) {{
                if (param === 37445) return gpuVendor;
                if (param === 37446) return gpuRenderer;
                return original.apply(this, arguments);
            }};
        }}
        patchGetParameter(WebGLRenderingContext.prototype);
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            patchGetParameter(WebGL2RenderingContext.prototype);
        }}
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 4: Canvas Fingerprint Noise
    // ═══════════════════════════════════════════════════════════
    try {{
        var origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        var origToBlob = HTMLCanvasElement.prototype.toBlob;
        var origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        var noiseSeed = {canvas_seed};

        HTMLCanvasElement.prototype.toDataURL = function() {{
            try {{
                var ctx = this.getContext('2d');
                if (ctx) {{
                    var r = Math.floor(noiseSeed * 10) % 256;
                    var g = Math.floor(noiseSeed * 100) % 256;
                    ctx.fillStyle = 'rgba(' + r + ',' + g + ',0,0.01)';
                    ctx.fillRect(0, 0, 1, 1);
                }}
                return origToDataURL.apply(this, arguments);
            }} catch(e) {{
                return 'data:image/png;base64,iVBOR' + Math.random().toString(36).substring(2);
            }}
        }};

        HTMLCanvasElement.prototype.toBlob = function() {{
            try {{
                var ctx = this.getContext('2d');
                if (ctx) {{
                    var r = Math.floor(noiseSeed * 10) % 256;
                    var g = Math.floor(noiseSeed * 100) % 256;
                    ctx.fillStyle = 'rgba(' + r + ',' + g + ',0,0.01)';
                    ctx.fillRect(0, 0, 1, 1);
                }}
                return origToBlob.apply(this, arguments);
            }} catch(e) {{
                var cb = arguments[0];
                if (typeof cb === 'function') cb(new Blob([], {{type: 'image/png'}}));
            }}
        }};

        CanvasRenderingContext2D.prototype.getImageData = function() {{
            try {{
                var imageData = origGetImageData.apply(this, arguments);
                for (var i = 0; i < Math.min(imageData.data.length, 40); i += 4) {{
                    imageData.data[i] = imageData.data[i] ^ (Math.floor(noiseSeed * (i+1)) & 1);
                }}
                return imageData;
            }} catch(e) {{
                var w = arguments[2] || 1, h = arguments[3] || 1;
                return new ImageData(w, h);
            }}
        }};
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 5: AudioContext Fingerprint Noise
    // ═══════════════════════════════════════════════════════════
    try {{
        var origGetFloatFreqData = AnalyserNode.prototype.getFloatFrequencyData;
        AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
            origGetFloatFreqData.apply(this, arguments);
            for (var i = 0; i < array.length; i++) {{
                array[i] = array[i] + (Math.random() * 0.0001 - 0.00005);
            }}
        }};
        var origCreateOsc = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {{
            var osc = origCreateOsc.apply(this, arguments);
            osc.__noise = Math.random() * 0.00001;
            return osc;
        }};
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 6: ClientRects / Element Size Jitter
    // ═══════════════════════════════════════════════════════════
    try {{
        var origGetClientRects = Element.prototype.getClientRects;
        var origGetBCR = Element.prototype.getBoundingClientRect;
        var rectNoise = {rect_noise};

        Element.prototype.getClientRects = function() {{
            var rects = origGetClientRects.apply(this, arguments);
            var result = [];
            for (var i = 0; i < rects.length; i++) {{
                result.push(new DOMRect(
                    rects[i].x + rectNoise,
                    rects[i].y + rectNoise,
                    rects[i].width + rectNoise,
                    rects[i].height + rectNoise
                ));
            }}
            return result;
        }};

        Element.prototype.getBoundingClientRect = function() {{
            var rect = origGetBCR.apply(this, arguments);
            return new DOMRect(
                rect.x + rectNoise,
                rect.y + rectNoise,
                rect.width + rectNoise,
                rect.height + rectNoise
            );
        }};
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 7: Screen Resolution Spoofing
    // ═══════════════════════════════════════════════════════════
    try {{
        Object.defineProperty(screen, 'width', {{ get: function() {{ return {screen_w}; }} }});
        Object.defineProperty(screen, 'height', {{ get: function() {{ return {screen_h}; }} }});
        Object.defineProperty(screen, 'availWidth', {{ get: function() {{ return {screen_aw}; }} }});
        Object.defineProperty(screen, 'availHeight', {{ get: function() {{ return {screen_ah}; }} }});
        Object.defineProperty(screen, 'colorDepth', {{ get: function() {{ return 24; }} }});
        Object.defineProperty(screen, 'pixelDepth', {{ get: function() {{ return 24; }} }});
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 8: Timezone Normalizar a US/Eastern
    // ═══════════════════════════════════════════════════════════
    try {{
        var origDTF = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function() {{
            var args = Array.from(arguments);
            if (!args[1]) args[1] = {{}};
            if (!args[1].timeZone) args[1].timeZone = 'America/New_York';
            return new origDTF(args[0], args[1]);
        }};
        Intl.DateTimeFormat.prototype = origDTF.prototype;
        Intl.DateTimeFormat.supportedLocalesOf = origDTF.supportedLocalesOf;

        var origResolvedOptions = origDTF.prototype.resolvedOptions;
        origDTF.prototype.resolvedOptions = function() {{
            var opts = origResolvedOptions.apply(this, arguments);
            opts.timeZone = 'America/New_York';
            return opts;
        }};

        var origGetTZO = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {{
            return 300;
        }};
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 9: WebRTC IP Leak Prevention
    // ═══════════════════════════════════════════════════════════
    try {{
        var origRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {{
            if (config && config.iceServers) {{
                config.iceServers = [];
            }}
            return new origRTC(config);
        }};
        window.RTCPeerConnection.prototype = origRTC.prototype;
        if (window.webkitRTCPeerConnection) {{
            window.webkitRTCPeerConnection = window.RTCPeerConnection;
        }}
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 10: Ocultar APIs exóticas que revelan automatización
    // ═══════════════════════════════════════════════════════════
    try {{
        var origQuery = navigator.permissions.query;
        navigator.permissions.query = function(desc) {{
            if (desc.name === 'notifications') {{
                return Promise.resolve({{ state: 'prompt', onchange: null }});
            }}
            return origQuery.apply(this, arguments);
        }};
    }} catch(e) {{}}

    try {{
        if (navigator.getBattery) {{
            navigator.getBattery = function() {{
                return Promise.resolve({{
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1.0,
                    addEventListener: function() {{}},
                    removeEventListener: function() {{}}
                }});
            }};
        }}
    }} catch(e) {{}}

    try {{
        if (navigator.bluetooth) {{
            Object.defineProperty(navigator, 'bluetooth', {{
                get: function() {{ return undefined; }},
                configurable: true
            }});
        }}
    }} catch(e) {{}}

    // ═══════════════════════════════════════════════════════════
    //  BLOQUE 11: Prevenir detección via window.chrome
    // ═══════════════════════════════════════════════════════════
    try {{
        if (!window.chrome) {{
            window.chrome = {{
                runtime: {{
                    onMessage: {{ addListener: function() {{}}, removeListener: function() {{}} }},
                    sendMessage: function() {{}},
                    connect: function() {{ return {{ onMessage: {{ addListener: function() {{}} }} }}; }}
                }},
                loadTimes: function() {{
                    return {{
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
                    }};
                }},
                csi: function() {{ return {{ pageT: Date.now() }}; }},
                app: {{ isInstalled: false, getDetails: function() {{ return null; }}, getIsInstalled: function() {{ return false; }}, runningState: function() {{ return 'cannot_run'; }} }}
            }};
        }}
    }} catch(e) {{}}

}})();"""

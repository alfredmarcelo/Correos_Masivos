import subprocess

brave_args = [
    "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe", 
    "--app=https://uhc.healthsherpa.com/sessions/new", 
    "--proxy-server=http://69.30.75.181:6238",
    
    # --- Funciones Anti-Fingerprinting y Anti-Detección ---
    "--disable-blink-features=AutomationControlled", # Evita que las páginas detecten la automatización
    "--disable-features=IsolateOrigins,site-per-process",
    "--test-type",                                   # Oculta la advertencia de "parámetros no admitidos"
    "--no-first-run",
    "--no-default-browser-check",
    "--ignore-certificate-errors",
    "--disable-background-networking"
]

subprocess.run(brave_args)
# Programa Centralizador - Creación Masiva de Correos

**Programa Centralizador** es una herramienta de escritorio desarrollada en Python (PyQt6) enfocada en la **creación masiva y automatizada de cuentas de correo electrónico** (como Outlook/Hotmail y Gmail). 

Este cliente web modificado está construido con una arquitectura avanzada para evadir los sistemas anti-bots y evitar el "browser fingerprinting", garantizando el aislamiento absoluto de cada sesión de registro para evitar que las cuentas sean marcadas como automatizadas.

## 🚀 Características Principales

### 1. Aislamiento Total de Pestañas (Anti-Fingerprinting)
Cada pestaña del navegador funciona como un entorno completamente aislado. El programa inyecta scripts de evasión en tiempo real para generar identidades únicas por cada pestaña, saltando las defensas de Microsoft y Google:
- **WebGL Spoofing:** Simulación de diferentes tarjetas gráficas (NVIDIA, AMD, Intel).
- **Canvas Noise:** Inyección de ruido en la renderización de canvas para evitar rastreo por píxeles.
- **AudioContext Jitter:** Alteración microscópica en frecuencias de audio.
- **Screen Spoofing:** Rotación de resoluciones de pantalla simuladas en el navegador.
- **Timezone Normalization:** Enmascaramiento de zonas horarias para coincidir con la ubicación del proxy en uso.

### 2. Soporte de Proxies (Rotación)
La aplicación está preparada para rotar IP conectándose a listas de proxies externas, asegurando que cada bloque de registros salga desde IPs residenciales o de centros de datos distintos. Permite manejar proxies autenticados (usuario:contraseña) con integración nativa a través de PyQt Network y peticiones asíncronas para buscar el mejor proxy disponible antes de arrancar.

### 3. Flujos Optimizados y Simulación Humana
- Pestañas independientes con memoria y caché virtualizadas.
- Ocultación profunda de motores automatizados (eliminación de los rastros típicos de QtWebEngine y Webdriver).

---

## 📂 Archivos Principales del Centralizador

El sistema incluye los siguientes componentes esenciales para funcionar:

- **`Centralizador.py`**: Interfaz principal PyQt6 con navegación por pestañas y motor web optimizado.
- **`browser_identity.py`**: Motor generador de identidades (crea User-Agents, tarjetas de video falsas, y huellas digitales aleatorias pero consistentes por pestaña).
- **Scripts de Plataformas (`Correos.py`, `correos_gmail.py`, `MercadoSalud.py`)**: Configuraciones específicas para cada entorno de destino.
- **`updater.py`**: Utilidad para gestionar la actualización remota de la herramienta.

---

## 🛠️ Instalación Rápida

### Dependencias
- Python 3.10+
- `PyQt6` y `PyQt6-WebEngine`

### Configuración
1. Clona este repositorio:
   ```bash
   git clone https://github.com/alfredmarcelo/Correos_Masivos.git
   ```
2. Instala las dependencias necesarias:
   ```bash
   pip install PyQt6 PyQt6-WebEngine
   ```
3. Inicia la aplicación:
   ```bash
   python Centralizador/Centralizador.py
   ```

*(Nota: Para utilizar la funcionalidad completa, el programa necesita consumir una lista de IPs / proxies a través de sus endpoints HTTP configurados localmente).*

---

## ⚠️ Aviso de Responsabilidad
Este proyecto fue creado con fines de automatización, pruebas de carga e investigación en seguridad y evasión de huellas digitales (Browser Fingerprinting). El uso intensivo de estos scripts para la creación masiva de cuentas en plataformas de terceros debe hacerse bajo la propia responsabilidad del usuario, respetando los Términos de Servicio (ToS) de las respectivas plataformas.

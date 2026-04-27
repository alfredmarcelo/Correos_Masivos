# Programa Centralizador - Automatización y Creación Masiva de Correos

![Centralizador](Centralizador/Icono.ico)

**Programa Centralizador** es una potente herramienta de escritorio desarrollada en Python (PyQt6) diseñada específicamente para la **creación masiva y automatizada de cuentas de correo electrónico** (principalmente Outlook/Hotmail y Gmail). 

El sistema está construido con una arquitectura avanzada orientada a evadir los sistemas anti-bots y evitar el "browser fingerprinting" (rastreo de huella digital), garantizando el aislamiento absoluto de cada sesión de registro.

## 🚀 Características Principales

### 1. Aislamiento Total de Pestañas (Anti-Fingerprinting)
Cada pestaña del navegador dentro de la aplicación funciona como un entorno 100% aislado. El programa inyecta scripts de evasión (Spoofing JS) en tiempo real para generar identidades únicas por pestaña, evadiendo la detección de Microsoft y Google:
- **WebGL Spoofing:** Simulación de diferentes tarjetas gráficas (NVIDIA, AMD, Intel).
- **Canvas Noise:** Inyección de ruido en la renderización de canvas para evitar rastreo por píxeles.
- **AudioContext Jitter:** Alteración microscópica en frecuencias de audio.
- **Screen & Hardware Spoofing:** Rotación de resoluciones de pantalla, memoria RAM y núcleos de CPU simulados.
- **Timezone Normalization:** Enmascaramiento de zonas horarias para coincidir con la ubicación del proxy.

### 2. Gestión Dinámica y Rotación de Proxies
El éxito en la creación masiva de correos radica en la calidad de la conexión:
- **Rotación en Tiempo Real:** Interfaz capaz de rotar y cambiar de proxy si se detectan bloqueos o caídas.
- **Servidores Proxy Locales:** Uso de microservicios Flask (en la carpeta `Proxies/`) que despachan listas frescas de proxies validados.
- **Validación SOCKS5 y HTTP:** Sistemas de chequeo continuo de la salud de los proxies mediante sockets directos.

### 3. Flujos de Registro Optimizados
- Flujos integrados para Outlook/Hotmail y Gmail.
- Las ventanas simulan comportamientos humanos (retrasos naturales, scroll, inyección de clicks) requeridos para saltar los retos ocultos de Microsoft.

---

## 📂 Estructura del Proyecto

El ecosistema de la aplicación se divide en 3 módulos principales:

* **`Centralizador/`**: Es el núcleo (Core) de la aplicación gráfica.
  * `Centralizador.py`: Interfaz principal PyQt6 con navegación por pestañas y motor Chromium modificado.
  * `browser_identity.py`: Motor generador de identidades (User-Agents, tarjetas de video, resoluciones aleatorias).
  * Scripts por módulo: `Correos.py`, `correos_gmail.py`, `MercadoSalud.py`.
* **`Proxies/`**: Herramientas para validación y despliegue de redes.
  * `proxy_server.py`: Servidor Flask que sirve listas de IP validadas.
  * `probar_proxies.py`: Script avanzado para filtrar, deducir y probar proxies (soporte SOCKS5).
* **`Asientos/`**: Herramienta auxiliar de monitoreo local.
  * `Asientos.py`: Dashboard de estado de las PCs o máquinas virtuales usadas en la granja, con integración de Nmap y TightVNC.

---

## 🛠️ Requisitos e Instalación

### Dependencias Generales
- Python 3.10+
- PyQt6 y PyQt6-WebEngine
- Flask (Para los servidores de proxy)
- Python-Nmap (Para el módulo de asientos)

### Instalación Rápida
1. Clona este repositorio:
   ```bash
   git clone https://github.com/alfredmarcelo/Correos_Masivos.git
   ```
2. Instala las dependencias:
   ```bash
   pip install PyQt6 PyQt6-WebEngine Flask python-nmap
   ```
3. Inicia la interfaz principal:
   ```bash
   python Centralizador/Centralizador.py
   ```

*(Nota: Para el módulo de proxies, asegúrate de tener una lista en `Proxies/proxies_buenos.txt` y levantar los servidores locales si el centralizador los requiere para la pantalla de carga inicial).*

---

## ⚠️ Aviso de Responsabilidad
Este proyecto fue creado con fines de automatización, pruebas de carga e investigación en seguridad y evasión de huellas digitales (Browser Fingerprinting). El uso intensivo de estos scripts para la creación masiva de cuentas en plataformas de terceros debe hacerse bajo la propia responsabilidad del usuario, respetando los Términos de Servicio (ToS) de las plataformas correspondientes (Microsoft, Google, etc).

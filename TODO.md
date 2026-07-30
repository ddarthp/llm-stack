# Portar a Windows y macOS

Las bases estan puestas: **no queda nada especifico de Linux fuera de dos ficheros**
(`llmstack/paths.py` y `llmstack/sysinfo.py`), el resto es igual en los tres sistemas.

Lo que sigue es lo que hay que **verificar y rematar en cada maquina**. Aviso importante
sobre el estado: todo el codigo comun esta probado en Linux; los caminos de Windows y
macOS estan **escritos pero sin ejecutar nunca**, porque no habia esas maquinas a mano.
Espera que algo falle a la primera; la idea es que falle en sitios concretos y localizados.

---

## Empezar en una maquina nueva

```bash
git clone https://github.com/ddarthp/llm-stack.git
cd llm-stack
python3 install.py            # dice que detecta y que falta
python3 install.py qwen-a1    # baja runtime + pesos de un modelo (4.5 GB)
python3 -m llmstack           # selector
```

Requisitos: **Python 3.11 o superior** (por `tomllib`). `psutil` es opcional pero
recomendado: sin el, en macOS y Windows no habra datos de CPU ni RAM.

```bash
pip install psutil
```

---

## macOS (Apple Silicon)

### 1. Runtime — probablemente funcione tal cual
`install.py` pide el asset `bin-macos-arm64.zip` de las releases de llama.cpp y detecta
backend `metal`. **Verificar** que el nombre del asset sigue siendo ese: si cambia, es una
linea en el diccionario `ASSETS` de `install.py`.

- [ ] `python3 install.py --runtime` termina sin error
- [ ] `llama-server --version` corre (Gatekeeper puede bloquearlo: `xattr -dr com.apple.quarantine <runtime>`)

### 2. Estadisticas — falta la GPU
`sysinfo._gpu_macos` deja el uso de GPU sin dato a proposito: en Apple Silicon la memoria
es unificada (no hay VRAM separada que reportar) y el uso de GPU solo lo da `powermetrics`,
que **exige root**. Pedir sudo para pintar una barra no compensa.

- [ ] CPU, RAM y temperatura salen bien con `psutil` instalado
- [ ] Decidir si quieres uso de GPU a cambio de sudo; si si, `powermetrics --samplers gpu_power -n1`
- [ ] La fila VRAM muestra "compartida", que es lo correcto ahi

### 3. Terminal a pantalla completa
`bin/llm-steam` usa AppleScript para abrir Terminal.app. **Sin probar.** Dos problemas
esperables:

- Terminal.app no acepta pantalla completa por argumento; hay que mandarle
  `tell application "System Events" to keystroke "f" using {command down, control down}`
- El `wait "$CHILD"` no espera realmente al script de AppleScript, asi que Steam creera
  que el juego se cerro al instante. **Esto casi seguro hay que rehacerlo**: lo suyo es
  lanzar el proceso Python en primer plano y que la terminal sea la que lo hospeda,
  o usar iTerm2, que si tiene API decente.

- [ ] Abrir el selector a pantalla completa
- [ ] Que Steam mantenga el juego "en ejecucion" mientras corre
- [ ] Que "Salir del juego" (SIGTERM) apague el modelo: `runner.py` ya lo maneja

### 4. Steam
`tools/steam-add` ya busca `~/Library/Application Support/Steam/userdata`.

- [ ] Anadir el atajo con Steam **cerrado** y comprobar que aparece
- [ ] Verificar que el icono y las caratulas se ven

---

## Windows

### 1. Runtime
`install.py` pide `bin-win-vulkan-x64.zip` (o CUDA si detecta `nvidia-smi`).

- [ ] `python install.py --runtime` descomprime bien el zip
- [ ] Comprobar que las DLL quedan **junto** a `llama-server.exe`: el aplanado de
      carpetas en `install_runtime` esta escrito para el layout de las releases actuales
      y es lo primero que se rompe si cambian
- [ ] En Windows la variable de bibliotecas es `PATH`, ya contemplado en `paths.py`

### 2. Estadisticas — la GPU esta sin hacer
`sysinfo._gpu_windows` **devuelve False siempre**: es un hueco a proposito, no un olvido.
Con NVIDIA funciona porque `_gpu_nvidia` usa `nvidia-smi`, que tambien existe en Windows.
Para AMD e Intel hay que elegir camino:

- Contadores de rendimiento (`GPU Engine\% Utilization`) via `pdh` o `typeperf`
- WMI / CIM: `Get-CimInstance Win32_VideoController` da memoria pero no uso
- La libreria `pynvml` solo cubre NVIDIA

- [ ] CPU y RAM con `psutil`
- [ ] Elegir e implementar backend de GPU, o dejarlo en "n/d" (el panel ya lo pinta asi)

### 3. Terminal
`bin/llm-steam.cmd` usa Windows Terminal (`wt --fullscreen`) y cae a `cmd` si no esta.

- [ ] Que `wt --fullscreen` abra a pantalla completa de verdad
- [ ] Que los colores ANSI se vean (Windows Terminal si; `cmd` clasico puede necesitar
      `VirtualTerminalLevel` en el registro)
- [ ] Que los caracteres de caja (`━ ─ ▸`) se rendericen: hace falta una fuente que los
      tenga y **UTF-8**. Puede requerir `chcp 65001`
- [ ] Que Ctrl+C pare el modelo y vuelva al menu

### 4. Senales
Windows no tiene `SIGHUP` y su `SIGTERM` se comporta distinto. `runner.py` ya comprueba
`hasattr(signal, "SIGHUP")`, pero **el apagado limpio al cerrar la ventana no esta
probado**. Si el modelo se queda cargado ocupando memoria, mirar ahi.

- [ ] Cerrar la ventana libera la memoria del modelo
- [ ] "Salir del juego" desde Steam tambien

### 5. Mando en el menu
`selector.Pads` lee `/dev/input/js*`, que **no existe** fuera de Linux. En Windows y macOS
el menu funciona con teclado y con la cuenta atras, que era justo la red de seguridad
pensada para esto. Si quieres mando:

- [ ] Windows: XInput via `ctypes`, o la libreria `inputs`
- [ ] macOS: framework GameController, o `pygame`

---

## Comun a los tres

- [ ] **Bonsai necesita el fork de PrismML**, que `install.py` no descarga: avisa y remite
      al README del modelo. Automatizarlo si merece la pena (sus releases estan en GitHub)
- [ ] Los `bench` de cada `model.toml` son de la Legion Go S. Al medir en otra maquina,
      esos numeros dejan de aplicar: o se guardan por maquina o se marcan como referencia
- [ ] `tools/bonsai-power` es **solo** para la Legion Go S (WMI de Lenovo). En otro equipo
      no aplica; no intentes portarlo, borra el archivo si estorba

---

## Como esta repartido el codigo

| Fichero | Especifico del sistema |
|---|---|
| `llmstack/paths.py` | **Si** — carpetas de datos y variable de bibliotecas por sistema |
| `llmstack/sysinfo.py` | **Si** — un backend de estadisticas por plataforma |
| `llmstack/runner.py` | No |
| `llmstack/panel.py` | No |
| `llmstack/config.py` | No |
| `llmstack/selector.py` | Parcial — solo el mando (`Pads`) |
| `install.py` | Parcial — solo el diccionario `ASSETS` |
| `bin/llm-steam*` | **Si** — una version por sistema |
| `tools/steam-add` | Parcial — solo donde buscar `userdata` |

Si añades soporte para algo nuevo, que sea en `paths.py` o en `sysinfo.py`. Si te ves
tocando `runner.py` o `panel.py` para un sistema concreto, probablemente la abstraccion
esta en el sitio equivocado.

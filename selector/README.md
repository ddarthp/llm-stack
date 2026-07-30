# Modelos locales — selector

Un solo icono, un solo puerto. Elige que modelo cargar y lo arranca; al pararlo vuelve
al menu para cambiar de modelo sin salir de la aplicacion.

```bash
llm               # menu + panel en vivo
```

## Por que un solo puerto

Antes cada modelo tenia el suyo (Bonsai 8090, Qwen 8091), asi que los clientes —opencode,
el movil, lo que sea— habia que reconfigurarlos segun cual estuviera cargado. Ahora **todos
usan el 8090**: cambias de modelo y el cliente ni se entera.

El puerto se cambia con `LLM_PORT=8095 llm`, y se propaga al modelo que elijas.

## Clave de acceso

Una sola para todos los modelos: **`PON-AQUI-TU-CLAVE`**, en `/home/deck/llm/apikey`.

```bash
curl http://TU-IP-LOCAL:8090/v1/chat/completions \
  -H "Authorization: Bearer PON-AQUI-TU-CLAVE" \
  -H 'Content-Type: application/json' \
  -d '{"model":"local","messages":[{"role":"user","content":"hola"}]}'
```

`llama-server` obliga a poner una, pero esto es un servidor de red local de uso ocasional,
asi que la clave es un formalismo y se prioriza que sea comoda de escribir. Sin ella
responde `401`. Ten en cuenta que **cualquiera en tu red local puede usar el servidor**
sabiendo esa palabra; si algun dia lo expones fuera de casa, cambia el contenido de
`apikey` por algo largo.

Plantilla de opencode lista en `/home/deck/llm/opencode.json`:

```bash
mkdir -p ~/.config/opencode && cp /home/deck/llm/opencode.json ~/.config/opencode/opencode.json
```

## Manejo

Pensado para funcionar en Modo Juego, donde no hay teclado:

| | |
|---|---|
| Mando | cruceta o stick para moverse · **A** elegir · **B** salir |
| Teclado | flechas o W/S · numeros · Enter · Q |
| Sin nada | cuenta atras de 15 s y arranca el ultimo modelo usado |

Esa cuenta atras es la red de seguridad: aunque el mando no responda por como Steam haya
mapeado el mando, la aplicacion arranca sola con lo ultimo que usaste. Cualquier pulsacion
la cancela. Se ajusta con `LLM_AUTOSTART=0` (sin cuenta atras) o el numero de segundos.

El mando se lee directamente de `/dev/input/js*`, probando todos los que se puedan abrir:
el mando fisico suele estar bajo ACL de sesion, pero Steam expone uno virtual legible.

## Modelos disponibles

| | Generacion | Prefill | VRAM | Para que |
|---|---|---|---|---|
| **Qwen A1 4B** | 16.6 tok/s | 250 tok/s | 9.6 GB | Agentes, opencode, herramientas |
| **Bonsai 27B** | 4.5 tok/s | 44 tok/s | 10.7 GB | Respuestas mas ricas, acepta imagenes |

Medido con `llama-bench -p 512 -n 32`. Detalles de cada uno en
`/home/deck/qwen-a1/README.md` y `/home/deck/bonsai/README.md`.

Para anadir otro modelo, edita la lista `MODELS` al principio de `llm`: cada entrada
apunta a su lanzador y le pasa el puerto unificado por variable de entorno.

## Desde Steam

Anadido como **"Modelos locales"**. Al salir desde el menu de Steam se apaga el modelo y
se libera la VRAM (verificado: de 9362 MiB a 740).

## Ficheros

```
/home/deck/llm/
├── llm           selector (enlazado en ~/.local/bin/llm)
├── llm-steam     version a pantalla completa para Modo Juego
├── last          ultimo modelo elegido
├── llm.png, art/ icono y caratulas
```

Los modelos siguen viviendo en `/home/deck/bonsai` y `/home/deck/qwen-a1`; esto solo los
orquesta. Sus lanzadores (`bonsai`, `qwen`) siguen funcionando sueltos si los llamas
directamente, cada uno con su puerto por defecto.

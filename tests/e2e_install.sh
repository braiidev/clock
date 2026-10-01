#!/usr/bin/env bash
# E2E del instalador. Reproduce el escenario real: una instalación vieja, con el
# venv creado a la antigua (`python3 -m venv`, que deja el alias flotante) y
# ~/.local/bin/clock como symlink al venv. Verifica que install.sh y
# `clock --update` lo reparen.
#
# No lo corre pytest a propósito: clona y crea venvs de verdad (~30s) y depende
# de /usr/bin/python3.X. Se corre a mano cuando se toca install.sh o update.py:
#     bash tests/e2e_install.sh
set -uo pipefail

# Raíz del repo: este script vive en tests/, así que el repo es su carpeta padre.
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T=$(mktemp -d /tmp/clock-e2e-XXXXXX)
export HOME="$T/home"
mkdir -p "$HOME"
CLONE="$HOME/.local/share/clock-tui"
BIN="$HOME/.local/bin/clock"
RC="$HOME/.bashrc"
: >"$RC"

export CLOCK_TUI_BIN="$BIN" CLOCK_TUI_RC="$RC"
export GIT_CONFIG_GLOBAL="$T/gitconfig"
git config --global user.email t@t.local >/dev/null
git config --global user.name T >/dev/null
git config --global init.defaultBranch main >/dev/null

fail=0
chk() { # chk <descripción> <esperado> <real>
  if [ "$2" = "$3" ]; then printf '  ✓ %s\n' "$1"
  else printf '  ✗ %s\n      esperado: %s\n      real:     %s\n' "$1" "$2" "$3"; fail=1; fi
}

echo "▶ clonando $SRC"
git clone -q "$SRC" "$CLONE"
# el fix todavía no está commiteado: lo copio al clon
cp "$SRC/install.sh" "$CLONE/install.sh"
cp -r "$SRC/src/." "$CLONE/src/"

echo "▶ creando el venv A LA VIEJA (python3 -m venv → flotante)"
/usr/bin/python3 -m venv "$CLONE/.venv"
"$CLONE/.venv/bin/pip" install -q -e "$CLONE" 2>/dev/null
echo "  estructura inicial:"
for p in python python3 python3.12; do printf '    .venv/bin/%-12s -> %s\n' "$p" "$(readlink "$CLONE/.venv/bin/$p" 2>/dev/null || echo '(archivo real)')"; done

echo
echo "── symlink viejo de la instalación anterior (así estaba antes del fix) ──"
mkdir -p "$(dirname "$BIN")"
ln -sf "$CLONE/.venv/bin/clock" "$BIN"
printf '  ~/.local/bin/clock -> %s   (symlink, como la instalación vieja)\n' "$(readlink "$BIN")"

echo
echo "── install.sh sobre el venv flotante + symlink viejo ──"
out=$(bash "$CLONE/install.sh" 2>&1); rc=$?
echo "$out" | grep -E "venv|Intérprete" | sed 's/^/  /'
chk "exit code" 0 "$rc"
chk "detecta el flotante" "sí" "$(echo "$out" | grep -q 'alias flotante' && echo sí || echo no)"
chk "bin/python3 ya no cuelga del alias" "python3.12" "$(readlink "$CLONE/.venv/bin/python3")"
chk "venv responde" "sí" "$("$CLONE/.venv/bin/python" -c 'import clock_tui' 2>/dev/null && echo sí || echo no)"
# Ojo: grep sigue symlinks, así que "tiene el marcador" NO alcanza — hay que
# comprobar que $BIN es un archivo regular y no un symlink al venv.
chk "~/.local/bin/clock es wrapper" "sí" "$(grep -q 'managed wrapper' "$BIN" 2>/dev/null && echo sí || echo no)"
chk "~/.local/bin/clock NO es symlink" "no" "$([ -L "$BIN" ] && echo sí || echo no)"
chk "console script de pip intacto" "sí" "$(grep -q '__main__\|clock_tui' "$CLONE/.venv/bin/clock" 2>/dev/null && ! grep -q 'managed wrapper' "$CLONE/.venv/bin/clock" 2>/dev/null && echo sí || echo no)"

echo
echo "── clock --version (smoke por el wrapper) ──"
v=$("$BIN" --version 2>&1); chk "wrapper arranca" 0 "$?"
echo "  $v"

echo
echo "── ROMPO el venv a mano otra vez (como el SO tras un upgrade) ──"
rm -f "$CLONE/.venv/bin/python" "$CLONE/.venv/bin/python3" "$CLONE/.venv/bin/python3.12"
/usr/bin/python3 -m venv "$CLONE/.venv" >/dev/null 2>&1
"$CLONE/.venv/bin/pip" install -q -e "$CLONE" 2>/dev/null
printf '%s\n' "$(readlink "$CLONE/.venv/bin/python3")" >"$CLONE/.pinned-python"
echo "  .venv/bin/python3 -> $(readlink "$CLONE/.venv/bin/python3")   (flotante de nuevo)"
flot=$(PYTHONPATH="$CLONE/src" /usr/bin/python3 -c "
import sys; sys.path.insert(0,'$CLONE/src')
from clock_tui import update
print('sí' if update.venv_is_floating('$CLONE') else 'no')")
chk "venv_is_floating lo detecta" "sí" "$flot"

echo
echo "── clock --update repara (el usuario no debe saber una contraseña) ──"
msg=$(PYTHONPATH="$CLONE/src" /usr/bin/python3 -c "
import sys; sys.path.insert(0,'$CLONE/src')
from clock_tui import update
print(update.do_update('$CLONE').message)" 2>&1)
echo "  mensaje: $msg"
chk "el update dice que recreó" "sí" "$(echo "$msg" | grep -q 'venv recreado' && echo sí || echo no)"
chk "ya no está flotante" "no" "$(readlink "$CLONE/.venv/bin/python3" | grep -q 'python3$' && echo sí || echo no)"
chk "el venv sigue importando" "sí" "$("$CLONE/.venv/bin/python" -c 'import clock_tui' 2>/dev/null && echo sí || echo no)"

echo
echo "── idempotencia: segundo update no debe tocar nada ──"
msg2=$(PYTHONPATH="$CLONE/src" /usr/bin/python3 -c "
import sys; sys.path.insert(0,'$CLONE/src')
from clock_tui import update
print(update.do_update('$CLONE').message)" 2>&1)
echo "  mensaje: $msg2"
chk "segundo update no recrea" "sí" "$(echo "$msg2" | grep -q 'venv recreado' && echo no || echo sí)"

echo
echo "── datos personales intactos ──"
chk "~/.config/clock no fue tocado por esto" "sin-data" "$([ -e "$HOME/.config/clock/data.json" ] && echo con-data || echo sin-data)"

# ── Auto-reparación del wrapper ──
# El caso que la venv muerta dejaba sin salida: tras un upgrade que borra la
# versión pineada, el comando está muerto y `clock --update` tampoco puede
# correr (es el mismo venv). El wrapper es bash, así que puede repararse solo.

echo
echo "── SIMULO upgrade de SO: la versión pineada desaparece ──"
ln -sf /usr/bin/python3.99 "$CLONE/.venv/bin/python3.12"  # danglante
ln -sf python3.99 "$CLONE/.venv/bin/python3"
ln -sf python3.99 "$CLONE/.venv/bin/python"
printf '/usr/bin/python3.99\n' >"$CLONE/.pinned-python"
echo "  pin: /usr/bin/python3.99 (no existe)   .venv/bin/python -> python3.99"

echo
echo "── clock se repara solo, sin que el usuario copie nada ──"
out=$("$BIN" --version 2>&1); rc=$?
echo "$out" | sed 's/^/  /'
chk "exit code" 0 "$rc"
chk "anuncia que repara" "sí" "$(echo "$out" | grep -q 'Reparando' && echo sí || echo no)"
chk "vuelve a funcionar" "sí" "$(echo "$out" | grep -q '^clock ' && echo sí || echo no)"
chk "ya no está danglante" "sí" "$([ -x "$CLONE/.venv/bin/python" ] && echo sí || echo no)"
chk "venv importable" "sí" "$("$CLONE/.venv/bin/python" -c 'import clock_tui' 2>/dev/null && echo sí || echo no)"
chk "no pide comando manual" "sí" "$(echo "$out" | grep -q 'Reparalo a mano' && echo no || echo sí)"
chk "pin realineado" "no" "$([ "$(cat "$CLONE/.pinned-python")" = "/usr/bin/python3.99" ] && echo sí || echo no)"
chk "wrapper sigue siendo wrapper" "no" "$([ -L "$BIN" ] && echo sí || echo no)"
chk "console script de pip intacto" "sí" "$(grep -q 'clock_tui' "$CLONE/.venv/bin/clock" 2>/dev/null && ! grep -q 'managed wrapper' "$CLONE/.venv/bin/clock" 2>/dev/null && echo sí || echo no)"

echo
echo "── no entra en loop si la reparación no sirve ──"
# install.sh roto: la reparación falla y tiene que salir, no reintentar para siempre
cp "$CLONE/install.sh" "$CLONE/install.sh.bak"
printf '#!/usr/bin/env bash\nexit 1\n' >"$CLONE/install.sh"
rm -f "$CLONE/.venv/bin/python"; ln -sf python3.99 "$CLONE/.venv/bin/python"
out2=$(timeout 60 "$BIN" --version 2>&1); rc2=$?
chk "termina (no cuelga)" "sí" "$([ $rc2 -ne 124 ] && echo sí || echo no)"
chk "no es éxito" "sí" "$([ $rc2 -ne 0 ] && echo sí || echo no)"
chk "ofrece el comando manual" "sí" "$(echo "$out2" | grep -q 'Reparalo a mano' && echo sí || echo no)"
chk "avisó que la reparación falló" "sí" "$(echo "$out2" | grep -q 'reparación automática falló' && echo sí || echo no)"
echo "$out2" | tail -3 | sed 's/^/  /'
mv "$CLONE/install.sh.bak" "$CLONE/install.sh"

echo
echo "── segundo clock tras reparar: sin ruido ──"
# El paso anterior dejó el venv roto a propósito (install.sh estaba stubbeado).
# Con install.sh devuelto pero sin correr, clock tiene que volver a reparar: es
# lo correcto, porque el venv sigue muerto. Primero se sana, y recién ahí se
# verifica que una invocación sana no vuelva a anunciar nada.
out3=$("$BIN" --version 2>&1)
chk "vuelve a reparar mientras siga roto" "sí" "$(echo "$out3" | grep -q 'Reparando' && echo sí || echo no)"
chk "y funciona" "sí" "$(echo "$out3" | grep -q '^clock ' && echo sí || echo no)"
out4=$("$BIN" --version 2>&1)
chk "ya sano: no anuncia reparación" "sí" "$(echo "$out4" | grep -q 'Reparando' && echo no || echo sí)"
chk "ya sano: solo la versión" "clock 1.2.0" "$out4"
chk "ya sano: no pide comando manual" "sí" "$(echo "$out4" | grep -q 'Reparalo a mano' && echo no || echo sí)"

echo
if [ "$fail" = 0 ]; then echo "E2E OK"; else echo "E2E FALLÓ"; fi
# No dejamos basura: el sandbox es de /tmp y no lo necesita nadie.
rm -rf "$T"
exit $fail

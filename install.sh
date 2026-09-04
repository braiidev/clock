#!/usr/bin/env bash
# install.sh — Instala/actualiza clock (dashboard TUI en curses)
# Uso: curl -fsSL https://raw.githubusercontent.com/braiidev/clock/main/install.sh | bash
# Instala SIN sudo en ~/.local: código en ~/.local/share/clock-tui, comando en ~/.local/bin/clock.
# Datos personales: NO se tocan (viven en ~/.config/clock).

set -euo pipefail

REPO_URL="https://github.com/braiidev/clock.git"
TARGET="${CLOCK_TUI_DIR:-$HOME/.local/share/clock-tui}"
BIN="$HOME/.local/bin/clock"

# ── Prerrequisitos ──
for cmd in git python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: $cmd no está instalado" >&2
        exit 1
    fi
done

# ── Obtener/actualizar el código ──
echo "▶ clock — instalando en $TARGET"
if [ -d "$TARGET/.git" ]; then
    echo "  ↳ ya existe, actualizando..."
    git -C "$TARGET" pull --ff-only
elif [ -d "$TARGET" ]; then
    echo "  ↳ existe pero no es un repo, respaldando como clock.bak..."
    mv "$TARGET" "$TARGET.bak"
    git clone "$REPO_URL" "$TARGET"
else
    mkdir -p "$(dirname "$TARGET")"
    git clone "$REPO_URL" "$TARGET"
fi

# ── Entorno virtual + dependencias (stdlib, sin deps externas) ──
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/pip" install --quiet --upgrade pip
"$TARGET/.venv/bin/pip" install --quiet -e "$TARGET"

# ── Ejecutable ──
mkdir -p "$HOME/.local/bin"
ln -sf "$TARGET/.venv/bin/clock" "$BIN"

echo ""
echo "✅ clock instalado. Ejecutá:  clock"
echo "   Código:   $TARGET"
echo "   Datos:    $HOME/.config/clock/"
echo "   Comandos: clock (TUI) · clock --update · clock --uninstall · clock --version"
if ! echo ":$PATH:" | grep -q ":${HOME}/.local/bin:"; then
    echo "   ⚠ Agregá ~/.local/bin a tu PATH (si no está ya):"
    echo "     echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
fi
#!/usr/bin/env bash
# Tool-agnostic dotfiles installer.
#
# Convention:
#   ~/dotfiles/<tool>/         is one tool module (e.g. cursor, claude, zsh, git).
#   Each top-level item inside is symlinked into the tool's target directory.
#   Default target:  $HOME/.<tool>   (e.g. cursor -> ~/.cursor, claude -> ~/.claude).
#   Override:        place a .dotfile.conf in the tool dir with:
#                        TARGET="$HOME"           # for top-level dotfiles (git, bash, …)
#                        TARGET="/custom/path"    # for tools with non-standard locations
#
# Usage:
#   install.sh                 # install all tool modules
#   install.sh cursor          # install only the cursor module
#   install.sh cursor claude   # install a subset
#
# Idempotent. On each run:
#   - symlink already pointing at the dotfiles source       -> leave alone
#   - symlink pointing elsewhere                            -> relink
#   - real file/dir                                         -> back up to <name>.bak.<timestamp> and replace

set -euo pipefail

DOTFILES_DIR="${DOTFILES_DIR:-$HOME/dotfiles}"
META_FILE=".dotfile.conf"

if [ ! -d "$DOTFILES_DIR" ]; then
  echo "ERROR: $DOTFILES_DIR does not exist." >&2
  exit 1
fi

# Determine tool list: explicit args, or every top-level directory.
TOOLS=("$@")
if [ ${#TOOLS[@]} -eq 0 ]; then
  while IFS= read -r -d '' dir; do
    name="$(basename "$dir")"
    [ "$name" = ".git" ] && continue
    TOOLS+=("$name")
  done < <(find "$DOTFILES_DIR" -mindepth 1 -maxdepth 1 -type d -print0)
fi

if [ ${#TOOLS[@]} -eq 0 ]; then
  echo "No tool modules found under $DOTFILES_DIR."
  exit 0
fi

ts="$(date +%Y%m%d-%H%M%S)"

for tool in "${TOOLS[@]}"; do
  src_dir="$DOTFILES_DIR/$tool"
  if [ ! -d "$src_dir" ]; then
    echo "skip tool: $tool (no directory at $src_dir)"
    continue
  fi

  # Default target; override from META_FILE if present.
  target_dir="$HOME/.$tool"
  if [ -f "$src_dir/$META_FILE" ]; then
    TARGET=""
    # shellcheck source=/dev/null
    . "$src_dir/$META_FILE"
    if [ -n "$TARGET" ]; then
      target_dir="${TARGET/#\~/$HOME}"
    fi
  fi

  echo "=== $tool -> $target_dir ==="
  mkdir -p "$target_dir"

  # Symlink each top-level item except the meta file.
  linked_any=0
  while IFS= read -r -d '' src; do
    name="$(basename "$src")"
    [ "$name" = "$META_FILE" ] && continue
    dest="$target_dir/$name"
    linked_any=1

    if [ -L "$dest" ]; then
      current="$(readlink "$dest")"
      if [ "$current" = "$src" ]; then
        echo "  ok:     $name"
        continue
      fi
      echo "  relink: $name (was -> $current)"
      rm "$dest"
    elif [ -e "$dest" ]; then
      backup="${dest}.bak.${ts}"
      echo "  backup: $name -> $(basename "$backup")"
      mv "$dest" "$backup"
    fi

    ln -s "$src" "$dest"
    echo "  link:   $name"
  done < <(find "$src_dir" -mindepth 1 -maxdepth 1 -print0)

  if [ "$linked_any" -eq 0 ]; then
    echo "  (empty tool module)"
  fi
done

echo "Done."

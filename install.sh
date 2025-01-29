#!/bin/bash

# these are the executables to install somewhere in the user PATH
toinstall=(
  "ollama-cli"
)

# Predefined list of 'standard' directories which may be in a user PATH
# If uv is installed, ~/.local/bin should be there anyway
directories=(
  "$HOME/.local/bin"
  "$HOME/bin"
  "$HOME/scripts"
  "$HOME/Public/bin"
)

# ---------------------------------------------------------------
# No user servicable part below this line
# ---------------------------------------------------------------

# Function to check if a directory is in the PATH
check_directory_in_path() {
  local dir=$1
  for path_dir in "${path_dirs[@]}"; do
    if [[ "$dir" == "$path_dir" ]]; then
      return 0
    fi
  done
  return 1
}

# Function to install via softlink an executable into a directory
install_to_dir() {
  local from=$1
  local to=$2
  local bname=$3

  echo -n "Installing $bname ... "
  if ln -sf "$from" "$to"; then
    echo "done."
  else
    echo "failed? Aborting!"
    exit 1
  fi
  return
}

# Check 'uv'
if command -v uv &> /dev/null; then
  echo "'uv' is installed, perfect."
  echo "Running 'uv' to prepare your environment"
else
  echo "'uv' is not installed, or not in your PATH."
  echo "Please consult https://docs.astral.sh/uv/getting-started/installation/"
  echo "Cannot install ollama-cli, exiting"
  exit
fi

uv sync --no-group dev

echo
echo

for binname in "${toinstall[@]}"; do
    if [ ! -e "$binname" ] || [ ! -x "$binname" ]; then
        echo "Oooops??? Somehow '$binname' either does not exist or is not executable."
        echo "Something went wrong with 'uv sync', exiting"
        exit 1
    fi
done

# Get the directories in PATH
IFS=':' read -r -a path_dirs <<< "$PATH"

# Check each directory if exist
for dir in "${directories[@]}"; do
  if check_directory_in_path "$dir"; then
    IPATH=$dir
    break
  fi
done

if [[ ! -n "$IPATH" ]]; then
  echo "No directory found to install to. Looked in:"
  for dir in "${directories[@]}"; do
    echo "$dir"
  done
  echo
  echo "I suggest you create ./local/bin and take it up permanently into your PATH,"
  echo "then rerun this script."
  exit 1
fi

# where are we?
SCRIPT=$(realpath "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

for binname in "${toinstall[@]}"; do
  install_to_dir "$SCRIPTPATH/.venv/bin/$toinstall" "$IPATH/$binname" "$binname"
done


echo
echo
echo "All done."
#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_PYTHON_CANDIDATES=(
    "${PROJECT_ROOT}/../tvt_313_env/bin/python"
    "${PROJECT_ROOT}/../tta_venv_313/bin/python"
    "${PROJECT_ROOT}/../tvt_311_env/bin/python"
)

prompt_with_default() {
    local label="$1"
    local default_value="$2"
    local current_value

    if [[ -n "${default_value}" ]]; then
        read -r -p "${label} [${default_value}]: " current_value
        printf '%s' "${current_value:-$default_value}"
    else
        read -r -p "${label}: " current_value
        printf '%s' "${current_value}"
    fi
}

require_value() {
    local name="$1"
    local value="$2"

    if [[ -z "${value}" ]]; then
        echo "Error: ${name} es obligatorio." >&2
        exit 1
    fi
}

DB_NAME="${DB_NAME:-}"
DB_USER="${DB_USER:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
PYTHON_BIN="${PYTHON_BIN:-}"
INTERACTIVE_PROMPTS=0

if [[ -z "${PYTHON_BIN}" ]]; then
    for candidate in "${DEFAULT_PYTHON_CANDIDATES[@]}"; do
        if [[ -x "${candidate}" ]]; then
            PYTHON_BIN="${candidate}"
            break
        fi
    done
fi

if [[ -z "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python3"
fi

if [[ -t 0 ]]; then
    INTERACTIVE_PROMPTS=1
fi

if [[ -z "${DB_NAME}" && "${INTERACTIVE_PROMPTS}" -eq 1 ]]; then
    DB_NAME="$(prompt_with_default "Nombre de la base de datos" "")"
fi

if [[ -z "${DB_USER}" && "${INTERACTIVE_PROMPTS}" -eq 1 ]]; then
    DB_USER="$(prompt_with_default "Usuario de la base de datos" "")"
fi

if [[ -z "${DB_PASSWORD}" && "${INTERACTIVE_PROMPTS}" -eq 1 ]]; then
    read -r -s -p "Contrasena de la base de datos: " DB_PASSWORD
    echo
fi

if [[ "${INTERACTIVE_PROMPTS}" -eq 1 ]]; then
    DB_HOST="$(prompt_with_default "Host de la base de datos" "${DB_HOST}")"
    DB_PORT="$(prompt_with_default "Puerto de la base de datos" "${DB_PORT}")"
fi

require_value "DB_NAME" "${DB_NAME}"
require_value "DB_USER" "${DB_USER}"
require_value "DB_PASSWORD" "${DB_PASSWORD}"
require_value "DB_HOST" "${DB_HOST}"
require_value "DB_PORT" "${DB_PORT}"

cd "${PROJECT_ROOT}"

echo "Ejecutando migraciones en MySQL/MariaDB:"
echo "  DB_NAME=${DB_NAME}"
echo "  DB_USER=${DB_USER}"
echo "  DB_HOST=${DB_HOST}"
echo "  DB_PORT=${DB_PORT}"
echo "  PYTHON_BIN=${PYTHON_BIN}"
echo

ENVIRONMENT=testing \
DB_ENGINE=django.db.backends.mysql \
DB_NAME="${DB_NAME}" \
DB_USER="${DB_USER}" \
DB_PASSWORD="${DB_PASSWORD}" \
DB_HOST="${DB_HOST}" \
DB_PORT="${DB_PORT}" \
"${PYTHON_BIN}" manage.py migrate "$@"

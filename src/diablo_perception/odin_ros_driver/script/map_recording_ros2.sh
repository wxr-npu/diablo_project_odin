#!/usr/bin/env bash

# Copyright (c) 2025 Manifold Tech Ltd.
#
# ROS2 固定地图录制流程：
# 1) 启动 pointcloud_saver_ros2_node 录制点云并保存为 PCD。
# 2) 启动 pcd2pgm_ros2_node 从 PCD 发布 /map。
# 3) 使用 nav2_map_server/map_saver_cli 保存 2D 栅格地图。
# 4) 触发 Odin 驱动保存 .bin 地图，用于重定位。

set -euo pipefail

FILENAME="${1:-mymap}"            # 输出地图基础名
VOXEL_SIZE="${2:-0.05}"           # PCD 保存体素大小
APPLY_FILTER="${3:-true}"         # PCD 保存是否统计滤波
WAIT_TIMEOUT_SEC="${4:-180}"      # 等待服务/文件/话题超时时间（秒）

normalize_bool() {
  local raw
  raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "${raw}" in
    true|1|yes|y|on)
      printf '%s' "true"
      ;;
    false|0|no|n|off)
      printf '%s' "false"
      ;;
    *)
      return 1
      ;;
  esac
}

if ! APPLY_FILTER_BOOL="$(normalize_bool "${APPLY_FILTER}")"; then
  echo "[map_recording_ros2][错误] APPLY_FILTER 参数无效: ${APPLY_FILTER}，请使用 true/false 或 1/0。" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WS_ROOT="$(cd "${PKG_DIR}/../../.." && pwd)"

CONFIG_FILE="${PKG_DIR}/config/control_command.yaml"
SET_PARAM_SH="${PKG_DIR}/set_param.sh"
ROS2_SETUP="${WS_ROOT}/install/setup.bash"
GRID_MAP_DIR="${WS_ROOT}/src/diablo_ros2/diablo_navigation2/maps/odin_maps"

pointcloud_saver_pid=""
pcd2pgm_pid=""
start_recording_service=""
stop_recording_service=""
save_map_service=""

log() {
  echo "[map_recording_ros2] $*"
}

die() {
  echo "[map_recording_ros2][错误] $*" >&2
  exit 1
}

cleanup() {
  for pid in "${pointcloud_saver_pid}" "${pcd2pgm_pid}"; do
    stop_process "${pid}" "3"
  done
  pointcloud_saver_pid=""
  pcd2pgm_pid=""
}

stop_process() {
  local pid="$1"
  local timeout_sec="${2:-3}"
  local elapsed=0

  if [[ -z "${pid}" ]]; then
    return 0
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  kill -INT "${pid}" 2>/dev/null || true
  while kill -0 "${pid}" 2>/dev/null && [[ ${elapsed} -lt ${timeout_sec} ]]; do
    sleep 1
    elapsed=$((elapsed + 1))
  done

  if kill -0 "${pid}" 2>/dev/null; then
    kill -TERM "${pid}" 2>/dev/null || true
    sleep 1
  fi

  if kill -0 "${pid}" 2>/dev/null; then
    kill -KILL "${pid}" 2>/dev/null || true
  fi

  wait "${pid}" 2>/dev/null || true
}

yaml_value() {
  local key="$1"
  local raw
  raw="$(sed -n "s/^[[:space:]]*${key}:[[:space:]]*\(.*\)$/\1/p" "${CONFIG_FILE}" | head -n 1)"
  raw="${raw%%#*}"
  raw="$(printf '%s' "${raw}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^['\"]//" -e "s/['\"]$//")"
  printf '%s' "${raw}"
}

wait_for_service() {
  local service_name="$1"
  local timeout_sec="$2"
  local elapsed=0

  while [[ ${elapsed} -lt ${timeout_sec} ]]; do
    if ros2 service list 2>/dev/null | grep -qx "${service_name}"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

resolve_service_name() {
  local timeout_sec="$1"
  local elapsed=0

  while [[ ${elapsed} -lt ${timeout_sec} ]]; do
    if ros2 service list 2>/dev/null | grep -qx '/pointcloud_saver/start_recording'; then
      start_recording_service='/pointcloud_saver/start_recording'
    elif ros2 service list 2>/dev/null | grep -qx '/start_recording'; then
      start_recording_service='/start_recording'
    fi

    if ros2 service list 2>/dev/null | grep -qx '/pointcloud_saver/stop_recording'; then
      stop_recording_service='/pointcloud_saver/stop_recording'
    elif ros2 service list 2>/dev/null | grep -qx '/stop_recording'; then
      stop_recording_service='/stop_recording'
    fi

    if ros2 service list 2>/dev/null | grep -qx '/pointcloud_saver/save_map'; then
      save_map_service='/pointcloud_saver/save_map'
    elif ros2 service list 2>/dev/null | grep -qx '/save_map'; then
      save_map_service='/save_map'
    fi

    if [[ -n "${start_recording_service}" && -n "${stop_recording_service}" && -n "${save_map_service}" ]]; then
      return 0
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

wait_for_topic() {
  local topic_name="$1"
  local timeout_sec="$2"
  local elapsed=0

  while [[ ${elapsed} -lt ${timeout_sec} ]]; do
    if ros2 topic list 2>/dev/null | grep -qx "${topic_name}"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

wait_for_file() {
  local target_path="$1"
  local timeout_sec="$2"
  local elapsed=0

  while [[ ${elapsed} -lt ${timeout_sec} ]]; do
    if [[ -f "${target_path}" ]]; then
      printf '%s' "${target_path}"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  return 1
}

wait_for_latest_bin() {
  local directory="$1"
  local timeout_sec="$2"
  local elapsed=0

  while [[ ${elapsed} -lt ${timeout_sec} ]]; do
    local latest
    latest="$(find "${directory}" -maxdepth 1 -type f -name '*.bin' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)"
    if [[ -n "${latest}" && -f "${latest}" ]]; then
      printf '%s' "${latest}"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  return 1
}

trap cleanup EXIT

command -v ros2 >/dev/null 2>&1 || die "未在 PATH 中找到 ros2，请先 source ROS2 环境。"
[[ -f "${CONFIG_FILE}" ]] || die "未找到配置文件: ${CONFIG_FILE}"
[[ -f "${SET_PARAM_SH}" ]] || die "未找到 set_param.sh: ${SET_PARAM_SH}"
[[ -f "${ROS2_SETUP}" ]] || die "未找到 ROS2 工作区 setup: ${ROS2_SETUP}，请先编译工作区。"

if [[ -n "${ROS_DISTRO:-}" && -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1091
  source "/opt/ros/${ROS_DISTRO}/setup.bash"
  set -u
fi

# shellcheck disable=SC1090
set +u
source "${ROS2_SETUP}"
set -u

mode="$(yaml_value custom_map_mode)"
if [[ -z "${mode}" ]]; then
  die "在 ${CONFIG_FILE} 中未找到 custom_map_mode 参数。"
fi
if [[ "${mode}" != "1" ]]; then
  die "Odin 当前不是建图模式，请将 ${CONFIG_FILE} 中 custom_map_mode 设为 1，并重启驱动。"
fi

mapping_dest_dir="$(yaml_value mapping_result_dest_dir)"
mapping_file_name="$(yaml_value mapping_result_file_name)"
relocalization_map_abs_path="$(yaml_value relocalization_map_abs_path)"

if [[ -z "${mapping_dest_dir}" ]]; then
  mapping_dest_dir="${PKG_DIR}/odin_map"
elif [[ "${mapping_dest_dir}" != /* ]]; then
  mapping_dest_dir="${WS_ROOT}/${mapping_dest_dir}"
fi

PCD_DIR="${mapping_dest_dir}/pcd"
PCD_FILE="${PCD_DIR}/${FILENAME}.pcd"
GRID_BASE="${GRID_MAP_DIR}/${FILENAME}"

mkdir -p "${mapping_dest_dir}" "${PCD_DIR}" "${GRID_MAP_DIR}"

log "ROS2 工作区: ${WS_ROOT}"
log "Odin 配置文件: ${CONFIG_FILE}"
log "PCD 输出文件: ${PCD_FILE}"
log "二维栅格输出前缀: ${GRID_BASE}"
log "统计滤波开关: ${APPLY_FILTER_BOOL}"

read -r -p "按 [Enter] 开始录制点云，输入 q 退出: " input
if [[ "${input}" == "q" ]]; then
  log "用户取消操作。"
  exit 0
fi

log "启动 pointcloud_saver_ros2_node ..."
ros2 run odin_ros_driver pointcloud_saver_ros2_node --ros-args \
  -p cloud_topic:=/odin1/cloud_slam \
  -p output_file:="${PCD_FILE}" \
  -p voxel_size:="${VOXEL_SIZE}" \
  -p apply_statistical_filter:=${APPLY_FILTER_BOOL} &
pointcloud_saver_pid=$!

resolve_service_name "${WAIT_TIMEOUT_SEC}" || die "等待 pointcloud_saver 服务超时（start_recording/stop_recording/save_map）。"
log "已识别服务: ${start_recording_service}, ${stop_recording_service}, ${save_map_service}"

ros2 service call "${start_recording_service}" std_srvs/srv/Trigger "{}" >/dev/null
log "已开始录制点云。"

read -r -p "按 [Enter] 停止录制并保存 PCD，输入 q 提前退出: " input
if [[ "${input}" == "q" ]]; then
  log "用户提前退出，停止录制。"
  ros2 service call "${stop_recording_service}" std_srvs/srv/Trigger "{}" >/dev/null || true
  exit 0
fi

ros2 service call "${stop_recording_service}" std_srvs/srv/Trigger "{}" >/dev/null
ros2 service call "${save_map_service}" std_srvs/srv/Trigger "{}" >/dev/null

if [[ -n "${pointcloud_saver_pid}" ]]; then
  stop_process "${pointcloud_saver_pid}" "3"
  pointcloud_saver_pid=""
fi

[[ -f "${PCD_FILE}" ]] || die "未生成 PCD 文件: ${PCD_FILE}"
log "PCD 保存成功: ${PCD_FILE}"

log "启动 pcd2pgm_ros2_node，发布 /map ..."
ros2 run odin_ros_driver pcd2pgm_ros2_node --ros-args \
  -p pcd_file:="${PCD_FILE}" \
  -p resolution:=0.05 \
  -p min_height:=-0.1 \
  -p max_height:=0.1 &
pcd2pgm_pid=$!

wait_for_topic "/map" "${WAIT_TIMEOUT_SEC}" || die "等待 /map 话题超时，无法保存二维地图。"
log "检测到 /map，开始保存二维栅格地图..."
ros2 run nav2_map_server map_saver_cli -t /map -f "${GRID_BASE}" --mode trinary
log "二维栅格地图保存成功: ${GRID_BASE}.yaml 和 ${GRID_BASE}.pgm"

if [[ -n "${pcd2pgm_pid}" ]]; then
  stop_process "${pcd2pgm_pid}" "3"
  pcd2pgm_pid=""
fi

log "触发 Odin 内部 .bin 地图保存..."
bash "${SET_PARAM_SH}" save_map 1

saved_bin=""
if [[ -n "${mapping_file_name}" ]]; then
  expected_bin="${mapping_dest_dir}/${mapping_file_name}.bin"
  log "等待指定 .bin 文件生成: ${expected_bin}"
  if ! saved_bin="$(wait_for_file "${expected_bin}" "${WAIT_TIMEOUT_SEC}")"; then
    die "等待超时，未生成文件: ${expected_bin}"
  fi
else
  log "等待 ${mapping_dest_dir} 中最新的 .bin 文件..."
  if ! saved_bin="$(wait_for_latest_bin "${mapping_dest_dir}" "${WAIT_TIMEOUT_SEC}")"; then
    die "等待超时，未在 ${mapping_dest_dir} 中检测到 .bin 文件。"
  fi
fi
log "Odin 三维地图已保存: ${saved_bin}"

read -r -p "按 [Enter] 将 custom_map_mode 切到 2 并写入重定位地图路径，输入其他任意内容跳过: " input
if [[ -z "${input}" ]]; then
  sed -i 's/^[[:space:]]*custom_map_mode:[[:space:]]*[0-9]\+/  custom_map_mode: 2/' "${CONFIG_FILE}"
  sed -i "s|^[[:space:]]*relocalization_map_abs_path:.*|  relocalization_map_abs_path: \"${saved_bin}\"|" "${CONFIG_FILE}"
  log "已更新 ${CONFIG_FILE}，切换为重定位模式。"
  log "custom_map_mode -> 2"
  log "relocalization_map_abs_path -> ${saved_bin}"
else
  log "用户选择跳过配置更新。"
  if [[ -n "${relocalization_map_abs_path}" ]]; then
    log "当前 relocalization_map_abs_path: ${relocalization_map_abs_path}"
  fi
fi

log "流程结束。"

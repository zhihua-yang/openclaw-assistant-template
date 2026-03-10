#!/usr/bin/env node
// post_reply_stats.js - 回复后延迟1秒查询并发送用量统计
// 使用 lane task done 字段获取完整任务耗时（含多个 run 的累计）

const fs = require('fs');
const path = require('path');

const LOG_DIR = '/tmp/openclaw';
const SESSION_LANE = 'session:agent:main:openclaw-wecom-bot:group:aiby2r-rxtkg9aj1bkpopbl69acynsnouvy';

function getTodayLog() {
  const today = new Date().toISOString().split('T')[0];
  return path.join(LOG_DIR, `openclaw-${today}.log`);
}

function parseLastTask(logFile) {
  if (!fs.existsSync(logFile)) return null;

  const content = fs.readFileSync(logFile, 'utf8');
  const lines = content.trim().split('\n');

  // 从末尾反向找最近一次 lane task done（session lane）
  let taskDurationMs = null;
  let taskEndTime = null;
  let todayTaskCount = 0;

  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (!line.includes('lane task done')) continue;
    if (!line.includes(SESSION_LANE)) continue;
    let data;
    try { data = JSON.parse(line); } catch { continue; }
    const msg = data['1'] || '';

    todayTaskCount++;
    if (taskDurationMs === null) {
      const durMatch = msg.match(/durationMs=(\d+)/);
      if (durMatch) {
        taskDurationMs = parseInt(durMatch[1]);
        taskEndTime = data._meta?.date || '';
      }
    }
  }

  if (taskDurationMs === null) return null;

  // 统计该任务内的 tool 调用数：找任务结束时间前最近的 embedded run 们
  // 用 taskEndTime 往前找，统计在该 lane task 时间窗口内的 tool start 数
  // 简化方案：找最近的 lane task done 和上一个 lane task done 之间的 tool start 数
  let prevTaskEndTime = null;
  let foundCurrent = false;
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (!line.includes('lane task done')) continue;
    if (!line.includes(SESSION_LANE)) continue;
    let data;
    try { data = JSON.parse(line); } catch { continue; }
    const t = data._meta?.date || '';
    if (!foundCurrent) {
      foundCurrent = true; // 跳过最近一次（当前任务）
      continue;
    }
    prevTaskEndTime = t;
    break;
  }

  let toolCount = 0;
  for (const line of lines) {
    if (!line.includes('embedded run tool start')) continue;
    let data;
    try { data = JSON.parse(line); } catch { continue; }
    const msg = data['1'] || '';
    if (!msg.includes('embedded run tool start')) continue;
    const t = data._meta?.date || '';
    if (prevTaskEndTime && t <= prevTaskEndTime) continue;
    if (taskEndTime && t > taskEndTime) continue;
    toolCount++;
  }

  return { durationMs: taskDurationMs, toolCount, todayTaskCount };
}

async function main() {
  // 延迟1秒等待日志写入
  await new Promise(r => setTimeout(r, 1000));

  const logFile = getTodayLog();
  const result = parseLastTask(logFile);

  if (!result) {
    console.log('未找到对话记录');
    return;
  }

  const { durationMs, toolCount, todayTaskCount } = result;
  const durS = (durationMs / 1000).toFixed(1);

  console.log(JSON.stringify({ durationMs, durS, toolCount, todayTaskCount }));
}

main().catch(console.error);

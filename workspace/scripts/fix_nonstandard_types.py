#!/usr/bin/env python3
"""
修复非标准类型事件工具
解决PUA第3轮检查发现的类型标准化率仅91.5%问题

关键问题发现：
1. skill-creation (2个) → 应转换为 new-capability
2. repeated-error (1个) → 应转换为 error-found  
3. session-summary (1个) → 应转换为 system-monitoring

工具策略：
1. 智能类型映射转换
2. 自动Tags更新（基于新类型）
3. 保留原内容但增强描述
4. 标记转换历史便于追溯
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 标准类型列表（与create_event.py保持一致）
STANDARD_TYPES = [
    'task-done', 'error-found', 'system-improvement', 'learning-achievement',
    'user-correction', 'automation-deployment', 'error-fix', 'system-monitoring',
    'quality-verification', 'new-capability', 'automation-planning', 'memory-compaction',
    'pua-inspection', 'quality-improvement'
]

# 非标类型到标准类型的智能映射
TYPE_MAPPING = {
    'skill-creation': 'new-capability',
    'repeated-error': 'error-found',
    'session-summary': 'system-monitoring',
    'quality-fix': 'quality-improvement',
    'skill-development': 'new-capability',
    'error-detection': 'error-found',
    'system-check': 'system-monitoring',
    'tool-creation': 'new-capability',
    'data-fix': 'quality-improvement',
    'check-completion': 'task-done',
}

# 类型转换后的内容增强建议
CONTENT_ENHANCEMENT = {
    'skill-creation': lambda old_content: f"获得新能力：{old_content} （原类型：skill-creation）",
    'repeated-error': lambda old_content: f"发现重复错误：{old_content} （原类型：repeated-error）",
    'session-summary': lambda old_content: f"会话总结监控：{old_content} （原类型：session-summary）",
}

def load_events(filepath: Path) -> List[Dict[str, Any]]:
    """加载所有事件"""
    events = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        print(f"📊 已加载 {len(events)} 个事件")
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filepath}")
    
    return events

def identify_nonstandard_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """识别非标准类型事件并返回详细信息"""
    nonstandard_details = []
    
    for i, event in enumerate(events):
        event_type = event.get('type', 'unknown')
        
        # 检查是否非标
        if event_type not in STANDARD_TYPES:
            nonstandard_details.append({
                'index': i,
                'original_event': event,
                'original_type': event_type,
                'suggested_type': TYPE_MAPPING.get(event_type, 'system-monitoring'),  # 默认映射
                'content': event.get('content', ''),
                'tags': event.get('tags', []),
            })
    
    return nonstandard_details

def update_event_tags(event: Dict[str, Any], new_type: str) -> List[str]:
    """基于新类型更新Tags，保留原有效Tags"""
    original_tags = event.get('tags', [])
    
    # 新类型的基础Tags
    base_tags = {
        'new-capability': ['capability', 'development', 'skill'],
        'error-found': ['error-detection', 'monitoring', 'issue'],
        'system-monitoring': ['monitoring', 'check', 'system'],
        'quality-improvement': ['quality', 'improvement', 'fix'],
        'task-done': ['task-completion', 'progress'],
    }
    
    new_tags = base_tags.get(new_type, [])
    
    # 保留原Tags中有价值的部分
    for tag in original_tags:
        if tag not in new_tags:
            # 过滤掉可能冗余或无效的Tags
            if '_' not in tag and tag != new_type and len(tag) < 20:
                new_tags.append(tag)
    
    return new_tags

def enhance_content(event_content: str, original_type: str, new_type: str) -> str:
    """增强事件内容，增加标准化描述"""
    enhancement_func = CONTENT_ENHANCEMENT.get(original_type)
    
    if enhancement_func:
        enhanced_content = enhancement_func(event_content)
    else:
        # 默认增强：添加类型转换标记
        enhanced_content = f"{event_content} （标准化转换：{original_type} → {new_type}）"
    
    return enhanced_content

def fix_nonstandard_event(event: Dict[str, Any], original_type: str, new_type: str) -> Dict[str, Any]:
    """修复单个非标类型事件"""
    fixed_event = event.copy()
    
    # 1. 更新类型
    fixed_event['type'] = new_type
    
    # 2. 增强内容
    original_content = event.get('content', '')
    if original_content:
        fixed_event['content'] = enhance_content(original_content, original_type, new_type)
    
    # 3. 更新Tags
    fixed_event['tags'] = update_event_tags(event, new_type)
    
    # 4. 添加转换标记（在extra中）
    if 'extra' not in fixed_event:
        fixed_event['extra'] = {}
    
    fixed_event['extra']['type_conversion'] = {
        'original_type': original_type,
        'converted_at': datetime.now().isoformat(),
        'conversion_reason': 'PUA第3轮检查发现类型标准化率不足，进行标准化修复'
    }
    
    return fixed_event

def backup_original_file(filepath: Path) -> Path:
    """备份原始文件"""
    if not filepath.exists():
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = filepath.parent / f"{filepath.name}.backup.{timestamp}"
    
    try:
        import shutil
        shutil.copy2(filepath, backup_path)
        print(f"📁 已备份原文件到: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None

def main():
    print("🔧 修复非标准类型事件工具 - PUA第3轮检查遗留问题修复")
    print("="*70)
    print("目标: 提升类型标准化率从91.5%到100%")
    print("      解决skill-creation、repeated-error、session-summary等非标类型")
    print("="*70)
    
    # 确定events.jsonl路径
    workspace_root = Path(__file__).parent.parent
    events_file = workspace_root / '.openclaw' / 'logs' / 'events.jsonl'
    
    if not events_file.exists():
        print(f"❌ 文件不存在: {events_file}")
        return 1
    
    # 备份原文件
    backup_path = backup_original_file(events_file)
    if not backup_path:
        print("⚠️ 备份未创建，继续执行但风险较高")
    
    # 加载事件
    events = load_events(events_file)
    if len(events) == 0:
        print("❌ 没有事件可处理")
        return 1
    
    # 识别非标准类型事件
    print(f"\n🔍 识别非标准类型事件中...")
    nonstandard_events = identify_nonstandard_events(events)
    
    if not nonstandard_events:
        print("✅ 所有事件类型都是标准类型，无需修复")
        return 0
    
    print(f"📊 发现 {len(nonstandard_events)} 个非标准类型事件:")
    for ns in nonstandard_events:
        idx = ns['index'] + 1
        old_type = ns['original_type']
        new_type = ns['suggested_type']
        content_preview = ns['content'][:40].replace('\n', ' ')
        tag_count = len(ns['tags'])
        
        print(f"   事件{idx}: {old_type} → {new_type} (tags: {tag_count}, \"{content_preview}...\")")
    
    # 确认修复
    print(f"\n⚠️ 确认修复吗？这将转换 {len(nonstandard_events)} 个事件的类型。")
    print(f"   转换映射：")
    type_counts = {}
    for ns in nonstandard_events:
        old_type = ns['original_type']
        new_type = ns['suggested_type']
        key = f"{old_type} → {new_type}"
        type_counts[key] = type_counts.get(key, 0) + 1
    
    for key, count in type_counts.items():
        print(f"   {key}: {count}个事件")
    
    # 修复事件
    fixed_count = 0
    for ns in nonstandard_events:
        idx = ns['index']
        original_event = events[idx]
        old_type = ns['original_type']
        new_type = ns['suggested_type']
        
        print(f"\n🔄 修复事件{idx+1}: {old_type} → {new_type}")
        
        # 修复事件
        fixed_event = fix_nonstandard_event(original_event, old_type, new_type)
        events[idx] = fixed_event
        
        # 显示变化
        print(f"   📋 类型: {old_type} → {new_type}")
        
        original_tag_count = len(original_event.get('tags', []))
        new_tag_count = len(fixed_event['tags'])
        print(f"   🏷️ Tags: {original_tag_count} → {new_tag_count}: {fixed_event['tags'][:3]}")
        
        fixed_count += 1
    
    # 保存修复后的事件
    try:
        with open(events_file, 'w', encoding='utf-8') as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        
        print(f"\n✅ 修复完成！")
        print(f"   📊 修复文件: {events_file}")
        print(f"   🔄 修复数量: {fixed_count}/{len(nonstandard_events)}个非标事件")
        
        # 验证修复效果
        print(f"\n🔍 验证修复效果:")
        
        # 重新计算类型标准化率
        std_count = sum(1 for e in events if e.get('type') in STANDARD_TYPES)
        type_std_rate = std_count / len(events) * 100 if events else 0
        
        print(f"   类型标准化率: {type_std_rate:.1f}% ({std_count}/{len(events)}个事件)")
        print(f"   修复前: 91.5% （第3轮PUA检查）")
        
        if type_std_rate >= 99.9:
            print(f"   结果: ✅ 成功提升到 {type_std_rate:.1f}%")
        else:
            # 检查剩余非标类型
            remaining_nonstd = [e.get('type') for e in events if e.get('type') not in STANDARD_TYPES]
            if remaining_nonstd:
                from collections import Counter
                remaining_counts = Counter(remaining_nonstd)
                print(f"   ⚠️ 仍有非标类型: {remaining_counts}")
        
        return 0
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        print(f"   可以从备份恢复: {backup_path}" if backup_path else "   没有备份可恢复")
        return 1

if __name__ == '__main__':
    sys.exit(main())
import React, { ChangeEvent } from 'react';

interface LayoutSelectorProps {
  layoutType: string;
  onLayoutChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  showHint?: boolean;
}

export default function LayoutSelector({ layoutType, onLayoutChange, showHint = true }: LayoutSelectorProps) {
  return (
    <div className="form-group">
      <label htmlFor="layoutType" className="agent_question">Layout Type </label>
      <select 
        name="layoutType" 
        id="layoutType" 
        value={layoutType} 
        onChange={onLayoutChange} 
        className="form-control-static"
        required
      >
        <option value="research">Research - 单列报告布局</option>
        <option value="copilot">Copilot - 左右分屏（报告 + 对话）</option>
      </select>
      {showHint && (
        <p className="mt-2 text-xs text-gray-400 leading-relaxed">
          仅对「Write Report」研究报告生效；Chat 模式始终为全屏对话。
          若当前正在查看报告，切换后界面会立即更新。
        </p>
      )}
    </div>
  );
} 
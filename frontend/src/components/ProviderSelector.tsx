/** 服务商/模型选择器 */
import React from "react";

interface ProviderSelectorProps {
  selectedProvider: string;
  onProviderChange: (name: string) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  providersList: any[];
  sniffedModels: any[];
}

export function ProviderSelector({
  selectedProvider, onProviderChange,
  selectedModel, onModelChange,
  providersList, sniffedModels,
}: ProviderSelectorProps) {
  const current = providersList.find((x: any) => x.name === selectedProvider);
  const models = sniffedModels.length > 0 ? sniffedModels : (current ? [{ id: current.default_model || 'default' }] : []);

  return (
    <div className="flex gap-2 items-center">
      <div className="flex-1">
        <select
          value={selectedProvider}
          onChange={e => onProviderChange(e.target.value)}
          className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">-- 默认供应商 --</option>
          {providersList.map((p: any) => (
            <option key={p.name} value={p.name}>{p.display_name}</option>
          ))}
        </select>
      </div>
      {selectedProvider && (
        <div className="flex-1">
          <select
            value={selectedModel}
            onChange={e => onModelChange(e.target.value)}
            className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {models.map((m: any) => (
              <option key={m.id} value={m.id}>{m.id}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}

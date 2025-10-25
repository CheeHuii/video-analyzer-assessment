// src/components/ModalChoice.tsx
import React from "react";

export default function ModalChoice({ open, choices, onChoose, onClose }: any) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/40">
      <div className="bg-white p-4 rounded shadow-lg w-96">
        <h3 className="font-bold mb-2">Clarification needed</h3>
        {choices.map((c: string, i: number) => (
          <button key={i} className="block w-full my-1 p-2 border rounded" onClick={()=>onChoose(c)}>{c}</button>
        ))}
        <div className="text-right mt-2"><button className="text-sm text-gray-500" onClick={onClose}>Cancel</button></div>
      </div>
    </div>
  );
}

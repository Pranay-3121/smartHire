import React, { useRef, useState } from "react";

export default function FileDropzone({ files, onChange, accept, multiple = true, label }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = Array.from(e.dataTransfer.files);
    onChange(multiple ? dropped : [dropped[0]]);
  };

  const handleChange = (e) => {
    const selected = Array.from(e.target.files);
    onChange(multiple ? selected : [selected[0]]);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        className="hidden"
      />
      <div className="text-4xl mb-2">📁</div>
      <p className="text-sm font-medium text-gray-700">{label}</p>
      <p className="text-xs text-gray-400 mt-1">Drag & drop or click to browse</p>

      {files?.length > 0 && (
        <div className="mt-4 space-y-1">
          {files.map((f, i) => (
            <div key={i} className="text-xs bg-blue-50 text-blue-700 px-3 py-1 rounded-full inline-block mx-1">
              {f.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

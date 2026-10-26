import { useEffect, useRef, useState } from "react";

const MAX_MB = 5;

/** Drag-and-drop / click image picker with preview and client-side checks (type + size). */
export default function ImageUpload({ file, onChange, label = "Photo", required = false }) {
  const [preview, setPreview] = useState(null);
  const [problem, setProblem] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef(null);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function accept(f) {
    setProblem("");
    if (!f) return;
    if (!f.type.startsWith("image/")) return setProblem("Please choose an image file (JPG, PNG, WEBP or GIF).");
    if (f.size > MAX_MB * 1024 * 1024) return setProblem(`That image is larger than ${MAX_MB} MB.`);
    if (f.size === 0) return setProblem("That file is empty.");
    onChange(f);
  }

  return (
    <div className="field">
      <span className="field-label">
        {label} {required ? <em>(required)</em> : <em>(optional)</em>}
      </span>
      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          accept(e.dataTransfer.files?.[0]);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      >
        {preview ? (
          <img src={preview} alt="Selected upload preview" />
        ) : (
          <p>
            <strong>Click to upload</strong> or drag a photo here
            <br />
            <small>JPG, PNG, WEBP or GIF · up to {MAX_MB} MB</small>
          </p>
        )}
        <input ref={input} type="file" accept="image/*" hidden data-testid="file-input" onChange={(e) => accept(e.target.files?.[0])} />
      </div>
      {file && (
        <button
          type="button"
          className="link-btn"
          onClick={() => {
            onChange(null);
            setProblem("");
            if (input.current) input.current.value = "";
          }}
        >
          Remove photo ({file.name})
        </button>
      )}
      {problem && <span className="field-error">{problem}</span>}
    </div>
  );
}

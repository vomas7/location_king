import styles from "~/components/ui/ui.module.css";

export interface SegmentedOption<T> {
  value: T;
  label: string;
}

interface SegmentedProps<T extends string | number | null> {
  label: string;
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  hint?: string;
}

/** Переключатель на несколько взаимоисключающих значений. */
export function Segmented<T extends string | number | null>({
  label,
  options,
  value,
  onChange,
  hint,
}: SegmentedProps<T>) {
  return (
    <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
      <legend className={styles.fieldLabel} style={{ marginBottom: 9 }}>
        {label}
      </legend>

      <div className={styles.segmented} role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={option.value === value}
            className={[
              styles.segmentedItem,
              option.value === value ? styles.segmentedItemActive : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              onChange(option.value);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>

      {hint !== undefined && (
        <p style={{ marginTop: 8, color: "var(--text-faint)", fontSize: 12 }}>{hint}</p>
      )}
    </fieldset>
  );
}

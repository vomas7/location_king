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

/**
 * Со скольких значений список перестаёт быть рядом и становится сеткой.
 *
 * В ряду значения делят ширину поровну, и последняя строка при переносе
 * растягивает свои два-три пункта по всей ширине — между «Юж. Америкой» и
 * «Океанией» получалась дыра в полполя, а «30 сек» в одиночку занимало строку
 * целиком. Сетка ставит их в те же колонки, что и строкой выше, и список
 * читается как список.
 *
 * Четыре — та граница, с которой список начинает переноситься в узкой
 * колонке. Три значения помещаются в строку всегда и переноса не знают.
 */
const GRID_FROM = 4;

/** Переключатель на несколько взаимоисключающих значений. */
export function Segmented<T extends string | number | null>({
  label,
  options,
  value,
  onChange,
  hint,
}: SegmentedProps<T>) {
  return (
    <fieldset className={styles.group}>
      <legend className={styles.groupLabel}>{label}</legend>

      <div
        className={[styles.segmented, options.length >= GRID_FROM ? styles.segmentedGrid : ""]
          .filter(Boolean)
          .join(" ")}
        role="radiogroup"
        aria-label={label}
      >
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

      {hint !== undefined && <p className={styles.groupHint}>{hint}</p>}
    </fieldset>
  );
}

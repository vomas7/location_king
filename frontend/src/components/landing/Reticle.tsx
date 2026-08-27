/**
 * Знак игры на первом экране: сетка тайлов с перекрестием в центре.
 *
 * То же перекрестие стоит в центре снимка во время раунда, на вкладке
 * браузера и в шапке — это единственная запоминающаяся деталь, и она
 * повторяется везде. Луч медленно проходит по сетке, как строка сканирования
 * съёмки; при выключенной анимации в системе он просто стоит на месте.
 */

interface ReticleProps {
  className: string | undefined;
}

const GRID = [80, 160, 240];

export function Reticle({ className }: ReticleProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 320 320"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="reticle-scan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
          <stop offset="50%" stopColor="currentColor" stopOpacity="0.45" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>

        {/* Без растушёвки к краям рисунок виден на фоне отдельной
            прямоугольной заплаткой */}
        <radialGradient id="reticle-edges">
          <stop offset="55%" stopColor="white" />
          <stop offset="100%" stopColor="black" />
        </radialGradient>

        <mask id="reticle-mask">
          <rect x="0" y="0" width="320" height="320" fill="url(#reticle-edges)" />
        </mask>
      </defs>

      <g mask="url(#reticle-mask)">
        {/* Сетка тайлов: четыре на четыре, как первый уровень приближения */}
        <g stroke="currentColor" strokeOpacity="0.18">
          {GRID.map((offset) => (
            <line key={`v${String(offset)}`} x1={offset} y1="0" x2={offset} y2="320" />
          ))}
          {GRID.map((offset) => (
            <line key={`h${String(offset)}`} x1="0" y1={offset} x2="320" y2={offset} />
          ))}
        </g>

        <rect
          className="reticle-scan"
          x="0"
          y="0"
          width="320"
          height="70"
          fill="url(#reticle-scan)"
        />
      </g>

      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="160" cy="160" r="34" strokeOpacity="0.9" />
        <path d="M160 96v34M160 190v34M96 160h34M190 160h34" />
      </g>

      <circle cx="160" cy="160" r="4" fill="currentColor" />
    </svg>
  );
}

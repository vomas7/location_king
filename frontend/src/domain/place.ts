/**
 * Где брать зоны для партии.
 *
 * На сервере это два независимых фильтра: часть света и группа стран. В меню
 * игрок выбирает что-то одно — пересечение вроде «Европа и Россия» не дало бы
 * ни одной зоны, а объяснять это в интерфейсе нечем. Поэтому выбор хранится
 * одним ключом, а здесь он разбирается обратно в два параметра запроса.
 */

/** Ключ выбранного места: `continent:<код>`, `country:<код>` или null. */
export type PlaceKey = string | null;

export interface PlaceFilter {
  continent: string | null;
  country_group: string | null;
}

const CONTINENT = "continent:";
const COUNTRY = "country:";

/** Разобрать выбор игрока в параметры запроса. */
export function placeFilter(place: PlaceKey): PlaceFilter {
  if (place === null) return { continent: null, country_group: null };

  if (place.startsWith(CONTINENT)) {
    return { continent: place.slice(CONTINENT.length), country_group: null };
  }
  if (place.startsWith(COUNTRY)) {
    return { continent: null, country_group: place.slice(COUNTRY.length) };
  }

  // Ключ приходит из списка в меню, поэтому третьего варианта быть не может:
  // если он появился, это опечатка в списке, а не выбор игрока
  throw new Error(`Неизвестное место: ${place}`);
}

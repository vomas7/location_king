/**
 * Словари интерфейса и их тип.
 *
 * Тип выведен из русского словаря: он исходный, и всё, что в нём появилось,
 * обязано появиться в остальных. Английский словарь объявлен этим типом,
 * поэтому пропущенный ключ или лишний — ошибка сборки, а не пустое место на
 * экране у того, кто до него доберётся.
 */

import type { Language } from "~/domain/language";
import { en } from "~/i18n/en";
import { ru } from "~/i18n/ru";

export type Dictionary = typeof ru;

export const DICTIONARIES: Record<Language, Dictionary> = { ru, en };
